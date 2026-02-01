"""Alertmanager 페이로드 → 이슈 JSON 변환기"""
import hashlib
import re
from pathlib import Path

# alertname → issue type 매핑
ALERT_TYPE_MAP = {
    "ContainerOOMKilled": "oom",
    "CPUThrottling": "cpu_throttle",
    "PodCrashLooping": "pod_crash",
    "HighMemoryUsage": "oom",
}

PROJECT_ROOT = Path(__file__).parent.parent.parent


def extract_resource_name(pod_name: str) -> str:
    """파드명에서 Deployment/StatefulSet 이름 추출

    예: oom-test-7f8b9c6d5-x2k4j → oom-test
        my-app-0 → my-app (StatefulSet)
    """
    # ReplicaSet + Pod suffix 제거 (Deployment)
    result = re.sub(r"-[a-f0-9]{6,10}-[a-z0-9]{5}$", "", pod_name)
    if result != pod_name:
        return result
    # StatefulSet suffix 제거
    result = re.sub(r"-\d+$", "", pod_name)
    return result


def derive_values_file(resource: str) -> str:
    """리소스명으로 values 파일 경로 추론"""
    candidate = f"values/{resource}.yaml"
    if (PROJECT_ROOT / candidate).exists():
        return candidate
    return ""


def convert_alert_to_issue(alert: dict) -> dict:
    """단일 Alertmanager alert → 이슈 JSON"""
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    alertname = labels.get("alertname", "Unknown")
    pod = labels.get("pod", "unknown")
    resource = extract_resource_name(pod)
    namespace = labels.get("namespace", "default")

    alert_id = hashlib.md5(
        f"{alertname}-{pod}-{alert.get('startsAt', '')}".encode()
    ).hexdigest()[:8]

    return {
        "id": f"alert-{alert_id}",
        "type": ALERT_TYPE_MAP.get(alertname, "unknown"),
        "namespace": namespace,
        "resource": resource,
        "error_message": annotations.get("summary", alertname),
        "logs": [annotations.get("description", "")],
        "timestamp": alert.get("startsAt", ""),
        "values_file": derive_values_file(resource),
    }


def convert_alertmanager_payload(payload: dict) -> list[dict]:
    """Alertmanager 웹훅 페이로드 → 이슈 JSON 리스트 (firing만 처리)"""
    issues = []
    for alert in payload.get("alerts", []):
        if alert.get("status") == "firing":
            issues.append(convert_alert_to_issue(alert))
    return issues
