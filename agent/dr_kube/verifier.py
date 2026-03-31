"""PR 머지 후 복구 검증 모듈

ArgoCD sync 완료 이후 실제로 이슈가 해결됐는지 확인:
  1. kubernetes Python client - 영향 받은 Pod Running 상태 + 재시작 안정
  2. Alertmanager API - 원본 alert 해소 여부
"""
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("dr-kube-verifier")

ALERTMANAGER_URL = "http://prometheus-alertmanager.monitoring.svc.cluster.local:9093"
K8S_TIMEOUT = 10  # 초

_k8s_v1 = None


def _get_k8s_client():
    """kubernetes CoreV1Api 클라이언트 (in-cluster 또는 kubeconfig)."""
    global _k8s_v1
    if _k8s_v1 is not None:
        return _k8s_v1
    try:
        from kubernetes import client as k8s_client, config as k8s_config
        try:
            k8s_config.load_incluster_config()
        except Exception:
            k8s_config.load_kube_config()
        _k8s_v1 = k8s_client.CoreV1Api()
    except Exception as e:
        logger.warning("kubernetes client 초기화 실패: %s", e)
    return _k8s_v1


def check_pods_healthy(namespace: str, resource: str, max_restarts: int = 5) -> tuple[bool, str]:
    """namespace/resource의 Pod들이 모두 Running이고 재시작이 안정적인지 확인.

    Returns:
        (healthy: bool, reason: str)
    """
    v1 = _get_k8s_client()
    if v1 is None:
        return False, f"kubernetes client 초기화 실패 (namespace={namespace}, resource={resource})"

    # app 레이블로 조회, 없으면 app.kubernetes.io/name 재시도
    pods = None
    for selector in [f"app={resource}", f"app.kubernetes.io/name={resource}"]:
        try:
            result = v1.list_namespaced_pod(namespace, label_selector=selector, _request_timeout=K8S_TIMEOUT)
            if result.items:
                pods = result.items
                break
        except Exception as e:
            logger.warning("Pod 조회 실패 (selector=%s): %s", selector, e)

    if pods is None:
        return False, f"Pod 없음 (namespace={namespace}, resource={resource})"

    for pod in pods:
        name = pod.metadata.name
        phase = pod.status.phase or ""
        conditions = pod.status.conditions or []
        ready = any(c.type == "Ready" and c.status == "True" for c in conditions)

        if phase != "Running" or not ready:
            return False, f"Pod {name}: phase={phase}, ready={ready}"

        for cs in (pod.status.container_statuses or []):
            restarts = cs.restart_count or 0
            if restarts > max_restarts:
                return False, f"Pod {name} 컨테이너 재시작 횟수 과다: {restarts}회"

    return True, f"{len(pods)}개 Pod 모두 Running + Ready"


def check_alert_resolved(fingerprint: str) -> tuple[bool, str]:
    """Alertmanager에서 해당 fingerprint의 alert가 해소됐는지 확인.

    Returns:
        (resolved: bool, reason: str)
    """
    if not fingerprint:
        return True, "fingerprint 없음 (확인 생략)"

    url = f"{ALERTMANAGER_URL}/api/v2/alerts?active=true"
    try:
        with urllib.request.urlopen(url, timeout=KUBECTL_TIMEOUT) as resp:
            alerts = json.loads(resp.read())
    except Exception as e:
        logger.warning("Alertmanager 조회 실패: %s", e)
        return True, f"Alertmanager 접근 실패 (확인 생략): {e}"

    still_firing = [
        a for a in alerts
        if a.get("fingerprint") == fingerprint and a.get("status", {}).get("state") == "active"
    ]
    if still_firing:
        alert = still_firing[0]
        alertname = alert.get("labels", {}).get("alertname", "?")
        return False, f"Alert 여전히 firing: {alertname} (fingerprint={fingerprint})"

    return True, "Alert 해소됨"


def verify_fix(
    namespace: str,
    resource: str,
    fingerprint: str,
    poll_interval: int = 30,
    timeout: int = 600,
) -> tuple[bool, str]:
    """PR 머지 후 복구 여부를 폴링으로 확인.

    Args:
        namespace: 영향 받은 네임스페이스
        resource: Deployment/StatefulSet 이름
        fingerprint: 원본 Alertmanager alert fingerprint
        poll_interval: 체크 간격 (초)
        timeout: 최대 대기 시간 (초)

    Returns:
        (success: bool, detail: str)
    """
    import time
    deadline = datetime.now(timezone.utc) + timedelta(seconds=timeout)
    attempt = 0

    logger.info("복구 검증 시작: namespace=%s resource=%s fingerprint=%s timeout=%ds",
                namespace, resource, fingerprint, timeout)

    while datetime.now(timezone.utc) < deadline:
        attempt += 1
        pod_ok, pod_reason = check_pods_healthy(namespace, resource)
        alert_ok, alert_reason = check_alert_resolved(fingerprint)

        logger.info("[verify #%d] pod=%s alert=%s | %s | %s",
                    attempt, pod_ok, alert_ok, pod_reason, alert_reason)

        if pod_ok and alert_ok:
            detail = f"Pod 정상: {pod_reason} / Alert: {alert_reason}"
            logger.info("복구 검증 성공: %s", detail)
            return True, detail

        remaining = (deadline - datetime.now(timezone.utc)).seconds
        if remaining <= poll_interval:
            break
        time.sleep(poll_interval)

    # 타임아웃
    pod_ok, pod_reason = check_pods_healthy(namespace, resource)
    alert_ok, alert_reason = check_alert_resolved(fingerprint)
    detail = f"Pod: {pod_reason} / Alert: {alert_reason}"
    logger.warning("복구 검증 타임아웃 (%ds): %s", timeout, detail)
    return False, detail
