"""Alertmanager 페이로드 → 이슈 JSON 변환기"""
import hashlib
import json
import re
from pathlib import Path

# alertname → issue type 매핑 (Prometheus metric alerts + Loki log alerts)
ALERT_TYPE_MAP = {
    # 컨테이너 리소스 (Prometheus)
    "ContainerOOMKilled": "oom",
    "HighMemoryUsage": "oom",
    "CPUThrottling": "cpu_throttle",
    # 파드 상태 (Prometheus)
    "PodCrashLooping": "pod_crash",
    "PodNotReady": "pod_unhealthy",
    "ContainerWaiting": "container_waiting",
    # 디플로이먼트 (Prometheus)
    "DeploymentReplicasMismatch": "replicas_mismatch",
    # 노드 (Prometheus)
    "NodeHighCPU": "node_resource",
    # 서비스 레벨 (Prometheus, span metrics 기반)
    "ServiceHighLatencyP99": "service_latency",
    "ServiceHighErrorRate": "service_error",
    "ServiceDown": "service_down",
    "UpstreamConnectionError": "upstream_error",
    # Nginx Ingress (Prometheus)
    "NginxHighLatency": "nginx_latency",
    "NginxHigh4xxRate": "nginx_error",
    "NginxHigh5xxRate": "nginx_error",
    # Loki log-based alerts
    "LogDNSResolutionFailure": "log_dns_failure",
    "LogConnectionRefused": "log_connection_error",
    "LogGRPCUnavailable": "log_grpc_error",
    "LogTimeoutDetected": "log_timeout",
    "LogRedisConnectionError": "log_redis_error",
    "LogOOMSignal": "log_oom_signal",
    "LogFatalOrPanic": "log_fatal",
    "LogErrorSpike": "log_error_spike",
    "LogHTTP5xxErrors": "log_http_5xx",
}

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Online Boutique 서비스명 목록
ONLINE_BOUTIQUE_SERVICES = {
    "frontend", "cartservice", "productcatalogservice", "currencyservice",
    "paymentservice", "shippingservice", "emailservice", "checkoutservice",
    "recommendationservice", "adservice", "redis-cart", "loadgenerator",
}


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


def derive_values_file(resource: str, namespace: str = "") -> str:
    """리소스명과 네임스페이스로 values 파일 경로 추론

    우선순위:
    1. values/{resource}.yaml 파일이 직접 존재하는 경우
    2. 리소스가 Online Boutique 서비스인 경우
    3. 네임스페이스가 online-boutique인 경우
    """
    # 1. 직접 매칭
    candidate = f"values/{resource}.yaml"
    if (PROJECT_ROOT / candidate).exists():
        return candidate
    # 2. Online Boutique 서비스 매칭
    if resource in ONLINE_BOUTIQUE_SERVICES:
        return "values/online-boutique.yaml"
    # 3. 네임스페이스 기반 fallback
    if namespace == "online-boutique":
        return "values/online-boutique.yaml"
    return ""


def convert_alert_to_issue(alert: dict) -> dict:
    """단일 Alertmanager alert → 이슈 JSON"""
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    alertname = labels.get("alertname", "Unknown")
    namespace = labels.get("namespace", "default")

    # 리소스명 추출: pod → deployment → service → app 순 fallback
    pod = labels.get("pod", "")
    if pod:
        resource = extract_resource_name(pod)
    elif labels.get("deployment"):
        resource = labels["deployment"]
    elif labels.get("service"):
        resource = labels["service"]
    elif labels.get("app"):
        resource = labels["app"]
    else:
        resource = "unknown"

    alert_id = hashlib.md5(
        f"{alertname}-{resource}-{namespace}-{alert.get('startsAt', '')}".encode()
    ).hexdigest()[:8]

    return {
        "id": f"alert-{alert_id}",
        "fingerprint": alert.get("fingerprint", ""),
        "type": ALERT_TYPE_MAP.get(alertname, alertname),
        "namespace": namespace,
        "resource": resource,
        "error_message": annotations.get("summary", alertname),
        "logs": [annotations.get("description", "")],
        "timestamp": alert.get("startsAt", ""),
        "values_file": derive_values_file(resource, namespace),
    }


def convert_alertmanager_payload(payload: dict) -> list[dict]:
    """Alertmanager 웹훅 페이로드 → 이슈 JSON 리스트 (firing만 처리)"""
    issues = []
    for alert in payload.get("alerts", []):
        if alert.get("status") == "firing":
            issues.append(convert_alert_to_issue(alert))
    return issues


def convert_argocd_event(payload: dict) -> dict:
    """ArgoCD Notifications webhook body (single event) -> issue schema."""
    resource = payload.get("resource", "unknown")
    namespace = payload.get("namespace", "default")
    raw_id = payload.get("id")
    fingerprint = raw_id or hashlib.md5(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    logs = payload.get("logs", [])
    if not isinstance(logs, list):
        logs = [str(logs)] if logs else []
    values_file = payload.get("values_file", "").strip()
    if not values_file:
        values_file = derive_values_file(resource, namespace)
    return {
        "id": raw_id or f"argocd-{fingerprint}",
        "fingerprint": fingerprint,
        "type": payload.get("type", "argocd_unknown"),
        "namespace": namespace,
        "resource": resource,
        "error_message": payload.get("error_message", ""),
        "logs": logs,
        "timestamp": payload.get("timestamp", ""),
        "values_file": values_file,
    }
