"""K8s / Prometheus 읽기 전용 도구 (GitOps 원칙: kubectl 쓰기 금지)"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Any

from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from delivery_agent.policy import DEPENDENCY_GRAPH

logger = logging.getLogger("delivery-tools")

PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus-operated.monitoring.svc.cluster.local:9090",
)

LOG_LINES = 100       # 수집할 로그 라인 수
EVENTS_MINUTES = 30   # 이벤트 조회 시간 범위 (분)
COLLECT_TIMEOUT = 10  # 병렬 수집 타임아웃 (초)


def _load_k8s_config():
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()


# ── Pod 로그 ──────────────────────────────────────────

def fetch_pod_logs(service: str, namespace: str, lines: int = LOG_LINES) -> list[str]:
    """서비스의 최근 로그 반환 (Pod 내 컨테이너 첫 번째)"""
    try:
        _load_k8s_config()
        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"app={service}",
        )
        if not pods.items:
            return [f"[경고] {service} Pod 없음"]

        pod_name = pods.items[0].metadata.name
        log_text = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=lines,
            timestamps=True,
        )
        return log_text.splitlines()[-lines:]
    except ApiException as e:
        logger.warning("로그 수집 실패 (%s): %s", service, e)
        return [f"[오류] 로그 수집 실패: {e.reason}"]
    except Exception as e:
        logger.warning("로그 수집 예외 (%s): %s", service, e)
        return [f"[오류] {e}"]


# ── K8s 이벤트 ────────────────────────────────────────

def fetch_k8s_events(service: str, namespace: str) -> list[str]:
    """서비스 관련 K8s 이벤트 반환"""
    try:
        _load_k8s_config()
        v1 = client.CoreV1Api()
        events = v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={service}",
        )
        result = []
        for e in sorted(events.items, key=lambda x: x.last_timestamp or x.event_time or ""):
            ts = e.last_timestamp or e.event_time or ""
            result.append(f"[{e.type}] {ts} {e.reason}: {e.message}")
        return result[-30:] if result else ["이벤트 없음"]
    except Exception as e:
        logger.warning("이벤트 수집 실패 (%s): %s", service, e)
        return [f"[오류] {e}"]


# ── Pod 상태 ──────────────────────────────────────────

def fetch_pod_status(service: str, namespace: str) -> dict[str, Any]:
    """Pod 상태, 재시작 횟수, 컨테이너 상태 반환"""
    try:
        _load_k8s_config()
        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"app={service}",
        )
        if not pods.items:
            return {"phase": "Unknown", "restart_count": 0, "reason": "Pod 없음"}

        pod = pods.items[0]
        restart_count = 0
        reason = ""
        container_states = []

        if pod.status.container_statuses:
            for cs in pod.status.container_statuses:
                restart_count += cs.restart_count
                if cs.state.waiting:
                    reason = cs.state.waiting.reason or ""
                elif cs.state.terminated:
                    reason = cs.state.terminated.reason or ""
                container_states.append({
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    "reason": reason,
                })

        return {
            "phase": pod.status.phase or "Unknown",
            "restart_count": restart_count,
            "reason": reason,
            "container_states": container_states,
        }
    except Exception as e:
        logger.warning("Pod 상태 수집 실패 (%s): %s", service, e)
        return {"phase": "Unknown", "restart_count": 0, "reason": str(e)}


# ── Prometheus 메트릭 ─────────────────────────────────

def fetch_prometheus_metrics(service: str, namespace: str) -> dict[str, Any]:
    """Prometheus에서 메모리/CPU 사용률, RPS, 에러율 조회"""
    try:
        import httpx
        metrics: dict[str, Any] = {}

        def query(promql: str) -> float | None:
            resp = httpx.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": promql},
                timeout=5.0,
            )
            data = resp.json()
            result = data.get("data", {}).get("result", [])
            if result:
                return float(result[0]["value"][1])
            return None

        # 메모리 사용률 (%)
        mem = query(
            f'100 * container_memory_working_set_bytes{{namespace="{namespace}",pod=~"{service}.*",container="{service}"}}'
            f' / on(pod) kube_pod_container_resource_limits{{namespace="{namespace}",resource="memory",container="{service}"}}'
        )
        if mem is not None:
            metrics["memory_pct"] = round(mem, 1)

        # CPU 사용률 (%)
        cpu = query(
            f'100 * rate(container_cpu_usage_seconds_total{{namespace="{namespace}",pod=~"{service}.*",container="{service}"}}[2m])'
            f' / on(pod) kube_pod_container_resource_limits{{namespace="{namespace}",resource="cpu",container="{service}"}}'
        )
        if cpu is not None:
            metrics["cpu_pct"] = round(cpu, 1)

        # HTTP 에러율 (5xx / 전체)
        error_rate = query(
            f'rate(http_requests_total{{job="{service}",status=~"5.."}}[2m])'
            f' / rate(http_requests_total{{job="{service}"}}[2m])'
        )
        if error_rate is not None:
            metrics["error_rate_pct"] = round(error_rate * 100, 2)

        return metrics
    except Exception as e:
        logger.warning("Prometheus 수집 실패 (%s): %s", service, e)
        return {}


# ── 병렬 컨텍스트 수집 ─────────────────────────────────

def collect_context_parallel(service: str, namespace: str) -> dict:
    """4가지 데이터 소스를 ThreadPoolExecutor로 병렬 수집"""
    # 영향 서비스 + upstream 1단계
    upstream_services = DEPENDENCY_GRAPH.get(service, [])
    all_services = list({service, *upstream_services})

    pod_logs: dict[str, list[str]] = {}
    pod_events: dict[str, list[str]] = {}
    pod_status: dict[str, dict] = {}
    metrics: dict[str, dict] = {}

    tasks = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        for svc in all_services:
            tasks[executor.submit(fetch_pod_logs, svc, namespace)] = ("logs", svc)
            tasks[executor.submit(fetch_pod_status, svc, namespace)] = ("status", svc)
            if svc == service:
                # 직접 영향 서비스만 이벤트 + 메트릭 전체 수집
                tasks[executor.submit(fetch_k8s_events, svc, namespace)] = ("events", svc)
                tasks[executor.submit(fetch_prometheus_metrics, svc, namespace)] = ("metrics", svc)

        for future in as_completed(tasks, timeout=COLLECT_TIMEOUT):
            kind, svc = tasks[future]
            try:
                result = future.result()
                if kind == "logs":
                    pod_logs[svc] = result
                elif kind == "status":
                    pod_status[svc] = result
                elif kind == "events":
                    pod_events[svc] = result
                elif kind == "metrics":
                    metrics[svc] = result
            except TimeoutError:
                logger.warning("컨텍스트 수집 타임아웃: %s/%s", kind, svc)
            except Exception as e:
                logger.warning("컨텍스트 수집 실패 (%s/%s): %s", kind, svc, e)

    return {
        "pod_logs": pod_logs,
        "pod_events": pod_events,
        "pod_status": pod_status,
        "metrics": metrics,
    }


# ── 매니페스트 파일 읽기 ───────────────────────────────

def read_manifest(file_path: str, repo_root: str) -> str:
    """로컬 또는 Git 저장소에서 manifest 파일 읽기"""
    from pathlib import Path
    full_path = Path(repo_root) / file_path
    if not full_path.exists():
        raise FileNotFoundError(f"매니페스트 파일 없음: {full_path}")
    return full_path.read_text(encoding="utf-8")
