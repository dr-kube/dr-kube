"""K8s 리소스 변경 감지 워처

ArgoCD가 관리하지 않는 리소스의 삭제/수상한 변경을 감지하여
Slack에 알림 + [복구] [무시] 버튼을 제공한다.

환경변수:
  WATCH_NAMESPACES  : 감시할 네임스페이스 (콤마 구분, 기본: online-boutique)
  WATCH_ENABLED     : 워처 활성화 여부 (기본: true)
"""
import os
import copy
import json
import logging
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone

import yaml

logger = logging.getLogger("dr-kube-watcher")

# 리소스 스냅샷: {ns/kind/name → resource_dict}
_snapshots: dict[str, dict] = {}
_snapshots_lock = threading.Lock()

# 복구 대기: action_id → {kind, name, namespace, resource_yaml, channel, ts}
_restore_pending: dict[str, dict] = {}

# 감시할 리소스 종류: (group, version, plural, kind_label)
_WATCH_TYPES = [
    ("apps", "v1", "deployments", "Deployment"),
    ("apps", "v1", "statefulsets", "StatefulSet"),
    ("", "v1", "services", "Service"),
    ("", "v1", "configmaps", "ConfigMap"),
]

# 복구 불필요한 ConfigMap (시스템/자동 생성)
_SKIP_CONFIGMAP_PREFIXES = (
    "kube-", "argocd-", "sh.helm.", "leader-election",
)


def _snapshot_key(namespace: str, kind: str, name: str) -> str:
    return f"{namespace}/{kind}/{name}"


def _clean_for_apply(resource: dict) -> dict:
    """kubectl apply를 위해 서버 관리 필드 제거."""
    r = copy.deepcopy(resource)
    meta = r.get("metadata", {})
    for field in ("resourceVersion", "uid", "creationTimestamp",
                  "generation", "managedFields", "selfLink",
                  "annotations"):
        meta.pop(field, None)
    # status 제거
    r.pop("status", None)
    return r


def _is_suspicious_modification(old: dict, new: dict, kind: str) -> str | None:
    """변경이 수상한지 판단. 수상하면 설명 문자열 반환, 정상이면 None."""
    if kind == "Deployment":
        old_replicas = old.get("spec", {}).get("replicas", 1)
        new_replicas = new.get("spec", {}).get("replicas", 1)
        if old_replicas > 0 and new_replicas == 0:
            return f"replicas {old_replicas} → 0 (강제 다운)"

    if kind in ("Deployment", "StatefulSet"):
        old_img = _get_images(old)
        new_img = _get_images(new)
        if old_img and new_img and old_img != new_img:
            return f"이미지 변경: {old_img} → {new_img}"

    if kind == "Service":
        old_ports = _get_ports(old)
        new_ports = _get_ports(new)
        if old_ports and new_ports and old_ports != new_ports:
            return f"포트 변경: {old_ports} → {new_ports}"

    return None


def _get_images(resource: dict) -> list[str]:
    containers = (
        resource.get("spec", {})
        .get("template", {})
        .get("spec", {})
        .get("containers", [])
    )
    return [c.get("image", "") for c in containers if c.get("image")]


def _get_ports(resource: dict) -> list:
    return [
        {"port": p.get("port"), "protocol": p.get("protocol")}
        for p in resource.get("spec", {}).get("ports", [])
    ]


def restore_resource(action_id: str) -> tuple[bool, str]:
    """저장된 스냅샷으로 kubectl apply 복구."""
    entry = _restore_pending.pop(action_id, None)
    if not entry:
        return False, f"action_id={action_id} 없음 (만료되었을 수 있음)"

    resource_yaml = entry["resource_yaml"]
    kind = entry["kind"]
    name = entry["name"]
    namespace = entry["namespace"]

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(resource_yaml, f, allow_unicode=True)
            tmp_path = f.name

        result = subprocess.run(
            ["kubectl", "apply", "-f", tmp_path],
            capture_output=True, text=True,
        )
        os.unlink(tmp_path)

        if result.returncode == 0:
            msg = f"{kind}/{name} (ns={namespace}) 복구 완료"
            logger.info(msg)
            return True, msg
        else:
            msg = result.stderr.strip() or result.stdout.strip()
            logger.error(f"복구 실패: {msg}")
            return False, msg
    except Exception as e:
        logger.error(f"restore_resource 예외: {e}")
        return False, str(e)


def _send_alert(kind: str, name: str, namespace: str,
                event_type: str, detail: str, resource_yaml: dict) -> None:
    """Slack에 변경 감지 알림 + [복구] [무시] 버튼 전송."""
    try:
        import dr_kube.slack as slack_client
        if not slack_client.is_configured():
            logger.warning("Slack 미설정 — 알림 스킵")
            return

        action_id = str(uuid.uuid4())[:8]
        _restore_pending[action_id] = {
            "kind": kind,
            "name": name,
            "namespace": namespace,
            "resource_yaml": resource_yaml,
        }

        icon = "🗑️" if event_type == "DELETED" else "⚠️"
        event_label = "삭제됨" if event_type == "DELETED" else "변경됨"

        channel = os.getenv("SLACK_CHANNEL", "dr-kube").lstrip("#")
        from slack_sdk import WebClient
        client = WebClient(token=os.getenv("SLACK_BOT_TOKEN", ""))

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{icon} DR-Kube 리소스 {event_label} — 복구 요청"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*종류:*\n`{kind}`"},
                    {"type": "mrkdwn", "text": f"*이름:*\n`{name}`"},
                    {"type": "mrkdwn", "text": f"*네임스페이스:*\n`{namespace}`"},
                    {"type": "mrkdwn", "text": f"*감지 시각:*\n{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*🔍 변경 내용*\n{detail}"},
            },
            {"type": "divider"},
            {
                "type": "actions",
                "block_id": f"restore_{action_id}",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "♻️ 복구"},
                        "style": "primary",
                        "action_id": "restore_resource",
                        "value": action_id,
                        "confirm": {
                            "title": {"type": "plain_text", "text": "복구 확인"},
                            "text": {"type": "mrkdwn", "text": f"`{kind}/{name}`을 복구하시겠습니까?"},
                            "confirm": {"type": "plain_text", "text": "복구"},
                            "deny": {"type": "plain_text", "text": "취소"},
                        },
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❌ 무시"},
                        "style": "danger",
                        "action_id": "ignore_resource",
                        "value": action_id,
                    },
                ],
            },
        ]

        resp = client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text=f"DR-Kube: {kind}/{name} {event_label} (ns={namespace})",
        )
        _restore_pending[action_id]["channel"] = resp["channel"]
        _restore_pending[action_id]["ts"] = resp["ts"]
        logger.info(f"워처 알림 전송: {kind}/{name} action_id={action_id}")

    except Exception as e:
        logger.error(f"워처 알림 전송 실패: {e}")


def _should_skip(kind: str, name: str) -> bool:
    """시스템 리소스 스킵 여부."""
    if kind == "ConfigMap":
        return any(name.startswith(p) for p in _SKIP_CONFIGMAP_PREFIXES)
    if kind == "Service" and name == "kubernetes":
        return True
    return False


def _watch_loop(namespace: str, group: str, version: str,
                plural: str, kind_label: str) -> None:
    """단일 리소스 타입을 무한 Watch하는 루프."""
    from kubernetes import client as k8s_client, watch

    if group:
        api = k8s_client.CustomObjectsApi()
    else:
        api = k8s_client.CoreV1Api()

    while True:
        try:
            w = watch.Watch()

            if group == "apps":
                apps_api = k8s_client.AppsV1Api()
                if plural == "deployments":
                    stream = w.stream(
                        apps_api.list_namespaced_deployment,
                        namespace=namespace,
                        timeout_seconds=300,
                    )
                else:
                    stream = w.stream(
                        apps_api.list_namespaced_stateful_set,
                        namespace=namespace,
                        timeout_seconds=300,
                    )
            elif group == "":
                if plural == "services":
                    stream = w.stream(
                        api.list_namespaced_service,
                        namespace=namespace,
                        timeout_seconds=300,
                    )
                else:
                    stream = w.stream(
                        api.list_namespaced_config_map,
                        namespace=namespace,
                        timeout_seconds=300,
                    )
            else:
                time.sleep(30)
                continue

            for event in stream:
                event_type = event["type"]  # ADDED, MODIFIED, DELETED
                obj = event["object"]

                # kubernetes 클라이언트 객체 → dict
                if hasattr(obj, "to_dict"):
                    resource = obj.to_dict()
                elif isinstance(obj, dict):
                    resource = obj
                else:
                    continue

                name = (resource.get("metadata") or {}).get("name", "")
                if not name or _should_skip(kind_label, name):
                    continue

                key = _snapshot_key(namespace, kind_label, name)

                with _snapshots_lock:
                    old_snapshot = _snapshots.get(key)

                    if event_type == "ADDED":
                        _snapshots[key] = resource
                        continue

                    elif event_type == "DELETED":
                        stored = old_snapshot or resource
                        _snapshots.pop(key, None)
                        cleaned = _clean_for_apply(stored)
                        detail = f"`{kind_label}/{name}` 이 삭제되었습니다."
                        logger.warning(f"[워처] DELETED: {kind_label}/{name} ns={namespace}")
                        threading.Thread(
                            target=_send_alert,
                            args=(kind_label, name, namespace, "DELETED", detail, cleaned),
                            daemon=True,
                        ).start()

                    elif event_type == "MODIFIED":
                        if old_snapshot:
                            reason = _is_suspicious_modification(old_snapshot, resource, kind_label)
                            if reason:
                                cleaned = _clean_for_apply(old_snapshot)
                                logger.warning(f"[워처] 수상한 변경: {kind_label}/{name} ns={namespace} — {reason}")
                                threading.Thread(
                                    target=_send_alert,
                                    args=(kind_label, name, namespace, "MODIFIED", reason, cleaned),
                                    daemon=True,
                                ).start()
                        _snapshots[key] = resource

        except Exception as e:
            logger.error(f"[워처] Watch 오류 ({kind_label} ns={namespace}): {e} — 5초 후 재시도")
            time.sleep(5)


def start(namespaces: list[str] | None = None) -> None:
    """워처 백그라운드 스레드 시작."""
    if os.getenv("WATCH_ENABLED", "true").lower() != "true":
        logger.info("워처 비활성화 (WATCH_ENABLED=false)")
        return

    try:
        from kubernetes import config as k8s_config
        try:
            k8s_config.load_incluster_config()
            logger.info("[워처] in-cluster config 로드")
        except Exception:
            k8s_config.load_kube_config()
            logger.info("[워처] kubeconfig 로드")
    except Exception as e:
        logger.error(f"[워처] K8s 설정 로드 실패: {e} — 워처 비활성화")
        return

    if namespaces is None:
        env_ns = os.getenv("WATCH_NAMESPACES", "online-boutique")
        namespaces = [ns.strip() for ns in env_ns.split(",") if ns.strip()]

    logger.info(f"[워처] 시작: namespaces={namespaces}")

    for ns in namespaces:
        for (group, version, plural, kind_label) in _WATCH_TYPES:
            t = threading.Thread(
                target=_watch_loop,
                args=(ns, group, version, plural, kind_label),
                daemon=True,
                name=f"watcher-{kind_label}-{ns}",
            )
            t.start()
            logger.info(f"[워처] 스레드 시작: {kind_label} ns={ns}")
