"""PR 머지 후 복구 검증 모듈

ArgoCD sync 완료 이후 실제로 이슈가 해결됐는지 확인:
  1. kubectl - 영향 받은 Pod Running 상태 + 재시작 안정
  2. Alertmanager API - 원본 alert 해소 여부
"""
import json
import logging
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("dr-kube-verifier")

ALERTMANAGER_URL = "http://prometheus-alertmanager.monitoring.svc.cluster.local:9093"
KUBECTL_TIMEOUT = 10  # 초


def _kubectl(args: list[str]) -> dict | list | None:
    """kubectl 명령 실행 후 JSON 파싱. 실패 시 None 반환."""
    try:
        result = subprocess.run(
            ["kubectl"] + args + ["-o", "json"],
            capture_output=True, text=True, timeout=KUBECTL_TIMEOUT,
        )
        if result.returncode != 0:
            logger.warning("kubectl 실패: %s", result.stderr.strip())
            return None
        return json.loads(result.stdout)
    except Exception as e:
        logger.warning("kubectl 예외: %s", e)
        return None


def check_pods_healthy(namespace: str, resource: str, max_restarts: int = 5) -> tuple[bool, str]:
    """namespace/resource의 Pod들이 모두 Running이고 재시작이 안정적인지 확인.

    Returns:
        (healthy: bool, reason: str)
    """
    data = _kubectl(["get", "pods", "-n", namespace, "-l", f"app={resource}"])
    if data is None:
        # app 레이블이 없는 경우 deployment 레이블로 재시도
        data = _kubectl(["get", "pods", "-n", namespace, "-l", f"app.kubernetes.io/name={resource}"])
    if data is None:
        return False, f"kubectl 실패 (namespace={namespace}, resource={resource})"

    items = data.get("items", [])
    if not items:
        return False, f"Pod 없음 (namespace={namespace}, resource={resource})"

    for pod in items:
        name = pod["metadata"]["name"]
        phase = pod.get("status", {}).get("phase", "")
        conditions = pod.get("status", {}).get("conditions", [])
        ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in conditions)

        if phase != "Running" or not ready:
            return False, f"Pod {name}: phase={phase}, ready={ready}"

        for cs in pod.get("status", {}).get("containerStatuses", []):
            restarts = cs.get("restartCount", 0)
            if restarts > max_restarts:
                return False, f"Pod {name} 컨테이너 재시작 횟수 과다: {restarts}회"

    return True, f"{len(items)}개 Pod 모두 Running + Ready"


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
