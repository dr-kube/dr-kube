"""Alertmanager 페이로드 → 이슈 JSON 변환기"""
import hashlib
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

# alertname → issue type 매핑 (values/prometheus.yaml의 15개 alert rule 전부)
ALERT_TYPE_MAP = {
    # 컨테이너 리소스
    "ContainerOOMKilled": "oom",
    "HighMemoryUsage": "oom",
    "CPUThrottling": "cpu_throttle",
    # 파드 상태
    "PodCrashLooping": "pod_crash",
    "PodNotReady": "pod_unhealthy",
    "ContainerWaiting": "container_waiting",
    # 디플로이먼트
    "DeploymentReplicasMismatch": "replicas_mismatch",
    # 노드
    "NodeHighCPU": "node_resource",
    # 서비스 레벨 (span metrics 기반)
    "ServiceHighLatencyP99": "service_latency",
    "ServiceHighErrorRate": "service_error",
    "ServiceDown": "service_down",
    "UpstreamConnectionError": "upstream_error",
    # Nginx Ingress
    "NginxHighLatency": "nginx_latency",
    "NginxHigh4xxRate": "nginx_error",
    "NginxHigh5xxRate": "nginx_error",
}

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Online Boutique 서비스명 목록
ONLINE_BOUTIQUE_SERVICES = {
    "frontend", "cartservice", "productcatalogservice", "currencyservice",
    "paymentservice", "shippingservice", "emailservice", "checkoutservice",
    "recommendationservice", "adservice", "redis-cart", "loadgenerator",
}

DR_KUBE_SERVICES = {
    "inventory-service", "recommendation-proxy", "order-validator",
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
    # 3. DR-Kube 커스텀 서비스 매칭
    if resource in DR_KUBE_SERVICES or namespace == "dr-kube-services":
        return "values/dr-kube-services.yaml"
    # 4. 네임스페이스 기반 fallback
    if namespace == "online-boutique":
        return "values/online-boutique.yaml"
    return ""


def convert_alert_to_issue(alert: dict) -> dict:
    """단일 Alertmanager alert → 이슈 JSON"""
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    alertname = labels.get("alertname", "Unknown")
    namespace = labels.get("namespace", "default")

    # 리소스명 추출: pod → deployment → service 순 fallback
    pod = labels.get("pod", "")
    if pod:
        resource = extract_resource_name(pod)
    elif labels.get("deployment"):
        resource = labels["deployment"]
    elif labels.get("service"):
        resource = labels["service"]
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


def _kubectl_raw(path: str, timeout: int = 10) -> dict:
    """kubectl get --raw 로 k8s API 프록시 경유 JSON 조회."""
    try:
        r = subprocess.run(
            ["kubectl", "get", "--raw", path],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode == 0:
            return json.loads(r.stdout)
    except Exception:
        pass
    return {}


def _query_prometheus(namespace: str, resource: str) -> list[str]:
    """Prometheus에서 리소스 핵심 메트릭 조회."""
    base = "/api/v1/namespaces/monitoring/services/http:prometheus-server:80/proxy/api/v1/query?query="

    queries = [
        (
            "메모리 사용률 (%)",
            f'round(container_memory_usage_bytes{{namespace="{namespace}",container=~"{resource}.*"}}'
            f' / container_spec_memory_limit_bytes{{namespace="{namespace}",container=~"{resource}.*"}} * 100, 1)',
        ),
        (
            "컨테이너 재시작 횟수",
            f'kube_pod_container_status_restarts_total{{namespace="{namespace}",container=~"{resource}.*"}}',
        ),
        (
            "OOMKill 여부",
            f'kube_pod_container_status_last_terminated_reason{{namespace="{namespace}",'
            f'container=~"{resource}.*",reason="OOMKilled"}}',
        ),
        (
            "P99 응답 지연 (ms)",
            f'histogram_quantile(0.99, rate(duration_milliseconds_bucket{{namespace="{namespace}",'
            f'service=~".*{resource}.*"}}[5m])) * 1000',
        ),
        (
            "5xx 에러율 (/s)",
            f'rate(calls_total{{namespace="{namespace}",service=~".*{resource}.*",status_code=~"5.."}}[5m])',
        ),
    ]

    results = []
    for label, query in queries:
        data = _kubectl_raw(base + urllib.parse.quote(query), timeout=8)
        items = data.get("data", {}).get("result", [])
        if not items:
            continue
        lines = []
        for item in items[:3]:
            pod = item.get("metric", {}).get("pod", item.get("metric", {}).get("container", "?"))
            val = item.get("value", ["", "N/A"])[1]
            lines.append(f"  {pod}: {val}")
        results.append(f"[Prometheus - {label}]\n" + "\n".join(lines))

    return results


def _query_loki(namespace: str, resource: str) -> list[str]:
    """Loki에서 최근 5분 에러 로그 조회."""
    base = "/api/v1/namespaces/monitoring/services/http:loki-gateway:80/proxy/loki/api/v1/query_range"

    now_ns = int(time.time() * 1_000_000_000)
    start_ns = now_ns - 5 * 60 * 1_000_000_000

    logql = f'{{namespace="{namespace}", app=~".*{resource}.*"}} |~ "(?i)(error|panic|fatal|oom|killed|timeout|refused)"'
    params = urllib.parse.urlencode({
        "query": logql,
        "start": start_ns,
        "end": now_ns,
        "limit": 20,
        "direction": "backward",
    })

    data = _kubectl_raw(f"{base}?{params}", timeout=12)
    lines = []
    for stream in data.get("data", {}).get("result", []):
        for _, line in stream.get("values", []):
            lines.append(line[:200])  # 너무 긴 로그 자르기

    if lines:
        return [f"[Loki 에러 로그 (최근 5분, {len(lines)}건)]\n" + "\n".join(lines[:15])]
    return []


def enrich_with_kubectl(issue: dict) -> dict:
    """kubectl로 실제 pod 데이터를 issue logs에 추가.

    추가 컨텍스트:
    - pod 상태 (kubectl get pods)
    - 현재 리소스 설정 (kubectl describe deployment)
    - 실시간 CPU/메모리 사용량 (kubectl top pods)
    - Warning 이벤트 (kubectl get events)
    - Pod 로그 (이전 컨테이너 or 최근)
    """
    import subprocess

    namespace = issue.get("namespace", "default")
    resource = issue.get("resource", "unknown")

    if resource in ("unknown", "") or not namespace:
        return issue

    logs = list(issue.get("logs", []))

    def run_kubectl(*args, timeout: int = 10) -> str:
        try:
            r = subprocess.run(
                ["kubectl", *args], capture_output=True, text=True, timeout=timeout
            )
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""

    # 1. Pod 상태
    pod_status = run_kubectl(
        "get", "pods", "-n", namespace, "-l", f"app={resource}",
        "--no-headers", "-o", "wide"
    )
    if pod_status:
        logs.append(f"[pod 상태]\n{pod_status}")

    # 2. 현재 리소스 설정 (limits/requests)
    describe_out = run_kubectl("describe", "deployment", resource, "-n", namespace)
    if describe_out:
        lines = describe_out.splitlines()
        resource_lines: list[str] = []
        for i, line in enumerate(lines):
            if "Limits:" in line or "Requests:" in line:
                resource_lines.extend(lines[i : i + 6])
        if resource_lines:
            logs.append("[현재 리소스 설정]\n" + "\n".join(resource_lines[:12]))

    # 3. 실시간 CPU/메모리 사용량
    top_out = run_kubectl("top", "pods", "-n", namespace, "--no-headers")
    if top_out:
        relevant = [l for l in top_out.splitlines() if resource in l]
        if relevant:
            logs.append("[실시간 리소스 사용량]\n" + "\n".join(relevant))

    # 4. Warning 이벤트
    events_out = run_kubectl(
        "get", "events", "-n", namespace,
        "--field-selector=type=Warning",
        "--sort-by=.lastTimestamp", "--no-headers"
    )
    if events_out:
        relevant_events = [l for l in events_out.splitlines() if resource in l]
        if relevant_events:
            logs.append("[Warning 이벤트]\n" + "\n".join(relevant_events[-10:]))

    # 5. Pod 로그 (이전 컨테이너 crash 직전 or 최근)
    pod_name = run_kubectl(
        "get", "pods", "-n", namespace,
        "-l", f"app={resource}",
        "-o", "jsonpath={.items[0].metadata.name}"
    )
    if pod_name:
        prev_logs = run_kubectl(
            "logs", pod_name, "-n", namespace, "--tail=30", "--previous", timeout=15
        )
        if prev_logs:
            logs.append(f"[이전 컨테이너 로그 (crash 직전)]\n{prev_logs}")
        else:
            curr_logs = run_kubectl(
                "logs", pod_name, "-n", namespace, "--tail=20", timeout=15
            )
            if curr_logs:
                logs.append(f"[pod 로그 (최근 20줄)]\n{curr_logs}")

    # 6. Prometheus 메트릭 (메모리 사용률, 재시작 횟수, 에러율, P99 지연)
    logs.extend(_query_prometheus(namespace, resource))

    # 7. Loki 에러 로그 (최근 5분)
    logs.extend(_query_loki(namespace, resource))

    return {**issue, "logs": logs}


def convert_alertmanager_payload(payload: dict) -> list[dict]:
    """Alertmanager 웹훅 페이로드 → 이슈 JSON 리스트 (firing만 처리).

    kubectl enrichment는 process_issue() 백그라운드 태스크에서 수행 (응답 지연 방지).
    """
    issues = []
    for alert in payload.get("alerts", []):
        if alert.get("status") == "firing":
            issue = convert_alert_to_issue(alert)
            issues.append(issue)
    return issues
