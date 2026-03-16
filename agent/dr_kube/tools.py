"""Investigate tools - Loki / Prometheus / K8s API query tools for LLM agent"""
import json
import logging
import os
import ssl
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta
from langchain_core.tools import tool

logger = logging.getLogger("dr-kube-investigate")

LOKI_URL = os.getenv("LOKI_URL", "http://loki.monitoring:3100")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus-server.monitoring:9090")
K8S_API_URL = "https://kubernetes.default.svc"
TOOL_TIMEOUT_SECONDS = int(os.getenv("TOOL_TIMEOUT_SECONDS", "10"))

_SA_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
_SA_CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"


def _http_get(url: str, timeout: int = TOOL_TIMEOUT_SECONDS, headers: dict | None = None,
              ssl_context: ssl.SSLContext | None = None) -> dict | str:
    req = urllib.request.Request(url, method="GET")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
            body = resp.read().decode("utf-8")
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return f"HTTP {e.code}: {error_body}"
    except urllib.error.URLError as e:
        return f"Connection error: {e.reason}"
    except TimeoutError:
        return f"Timeout ({timeout}s)"
    except Exception as e:
        return f"Unexpected error: {type(e).__name__}: {e}"


def _k8s_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if os.path.exists(_SA_CA_PATH):
        ctx.load_verify_locations(_SA_CA_PATH)
    else:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _k8s_token() -> str:
    try:
        with open(_SA_TOKEN_PATH, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


@tool
def query_loki_logs(app: str, namespace: str, pattern: str,
                    duration: str = "5m", limit: int = 20) -> str:
    """Query Loki for recent application logs matching a pattern.

    Args:
        app: Application name (label selector, e.g. "productcatalogservice")
        namespace: Kubernetes namespace (e.g. "online-boutique")
        pattern: Log line regex filter (e.g. "error|timeout|no such host")
        duration: Lookback duration (e.g. "5m", "10m", "1h")
        limit: Maximum number of log lines to return
    """
    logql = f'{{namespace="{namespace}", app="{app}"}} |~ "(?i){pattern}"'
    now = datetime.now(timezone.utc)
    duration_seconds = _parse_duration(duration)
    start_time = now - timedelta(seconds=duration_seconds)

    params = urllib.parse.urlencode({
        "query": logql,
        "start": str(int(start_time.timestamp())),
        "end": str(int(now.timestamp())),
        "limit": str(limit),
        "direction": "backward",
    })
    url = f"{LOKI_URL}/loki/api/v1/query_range?{params}"

    logger.info("[investigate] tool_call: query_loki_logs(app=%s, namespace=%s, pattern=%s, duration=%s)",
                app, namespace, pattern, duration)

    result = _http_get(url)

    if isinstance(result, str):
        logger.warning("[investigate] tool_call: query_loki_logs -> failed (%s)", result)
        return json.dumps({"error": f"Loki query failed: {result}", "query": logql})

    try:
        streams = result.get("data", {}).get("result", [])
        lines = []
        for stream in streams:
            labels = stream.get("stream", {})
            for ts, line in stream.get("values", []):
                lines.append(line)
            if len(lines) >= limit:
                break

        if not lines:
            logger.info("[investigate] tool_call: query_loki_logs -> success (0 logs)")
            return json.dumps({
                "result": [],
                "count": 0,
                "note": f"No logs matching pattern '{pattern}' for app={app} in {namespace} over last {duration}",
                "query": logql,
            })

        logger.info("[investigate] tool_call: query_loki_logs -> success (%d logs)", len(lines))
        return json.dumps({
            "result": lines[:limit],
            "count": len(lines),
            "query": logql,
        })
    except Exception as e:
        logger.warning("[investigate] tool_call: query_loki_logs -> parse error (%s)", e)
        return json.dumps({"error": f"Failed to parse Loki response: {e}", "query": logql})


@tool
def query_prometheus(query: str) -> str:
    """Execute a PromQL instant query against Prometheus.

    Args:
        query: PromQL expression (e.g. 'rate(http_requests_total{status=~"5.."}[5m])')
    """
    params = urllib.parse.urlencode({"query": query})
    url = f"{PROMETHEUS_URL}/api/v1/query?{params}"

    logger.info("[investigate] tool_call: query_prometheus(query=%s)", query)

    result = _http_get(url)

    if isinstance(result, str):
        logger.warning("[investigate] tool_call: query_prometheus -> failed (%s)", result)
        return json.dumps({"error": f"Prometheus query failed: {result}", "query": query})

    try:
        status = result.get("status", "")
        if status == "error":
            error_type = result.get("errorType", "")
            error_msg = result.get("error", "")
            logger.warning("[investigate] tool_call: query_prometheus -> API error (%s: %s)", error_type, error_msg)
            return json.dumps({"error": f"PromQL error ({error_type}): {error_msg}", "query": query})

        data = result.get("data", {})
        result_type = data.get("resultType", "")
        results = data.get("result", [])

        formatted = []
        for item in results:
            metric = item.get("metric", {})
            value = item.get("value", [])
            formatted.append({
                "metric": metric,
                "value": value[1] if len(value) > 1 else None,
                "timestamp": value[0] if value else None,
            })

        logger.info("[investigate] tool_call: query_prometheus -> success (%d series)", len(formatted))
        return json.dumps({
            "result": formatted,
            "count": len(formatted),
            "resultType": result_type,
            "query": query,
        })
    except Exception as e:
        logger.warning("[investigate] tool_call: query_prometheus -> parse error (%s)", e)
        return json.dumps({"error": f"Failed to parse Prometheus response: {e}", "query": query})


@tool
def get_pod_status(namespace: str, app: str) -> str:
    """Get Kubernetes pod status for a specific application.

    Args:
        namespace: Kubernetes namespace (e.g. "online-boutique")
        app: Application name label (e.g. "productcatalogservice")
    """
    token = _k8s_token()
    if not token:
        logger.warning("[investigate] tool_call: get_pod_status -> no service account token")
        return json.dumps({"error": "K8s service account token not found (not running in cluster?)"})

    selector = urllib.parse.quote(f"app={app}")
    url = f"{K8S_API_URL}/api/v1/namespaces/{namespace}/pods?labelSelector={selector}"

    logger.info("[investigate] tool_call: get_pod_status(namespace=%s, app=%s)", namespace, app)

    result = _http_get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        ssl_context=_k8s_ssl_context(),
    )

    if isinstance(result, str):
        logger.warning("[investigate] tool_call: get_pod_status -> failed (%s)", result)
        return json.dumps({"error": f"K8s API query failed: {result}"})

    try:
        items = result.get("items", [])
        pods = []
        for pod in items:
            metadata = pod.get("metadata", {})
            status = pod.get("status", {})

            container_statuses = []
            for cs in status.get("containerStatuses", []):
                container_statuses.append({
                    "name": cs.get("name", ""),
                    "ready": cs.get("ready", False),
                    "restartCount": cs.get("restartCount", 0),
                    "state": _summarize_container_state(cs.get("state", {})),
                    "lastTermination": _summarize_container_state(cs.get("lastState", {})),
                })

            conditions = []
            for cond in status.get("conditions", []):
                if cond.get("status") != "True":
                    conditions.append({
                        "type": cond.get("type", ""),
                        "status": cond.get("status", ""),
                        "reason": cond.get("reason", ""),
                        "message": cond.get("message", ""),
                    })

            pods.append({
                "name": metadata.get("name", ""),
                "phase": status.get("phase", ""),
                "containers": container_statuses,
                "failedConditions": conditions,
            })

        if not pods:
            logger.info("[investigate] tool_call: get_pod_status -> success (0 pods found)")
            return json.dumps({
                "result": [],
                "count": 0,
                "note": f"No pods found with label app={app} in namespace {namespace}",
            })

        total_restarts = sum(
            cs["restartCount"] for p in pods for cs in p["containers"]
        )
        logger.info("[investigate] tool_call: get_pod_status -> success (%d pods, %d total restarts)",
                     len(pods), total_restarts)
        return json.dumps({
            "result": pods,
            "count": len(pods),
            "totalRestarts": total_restarts,
        })
    except Exception as e:
        logger.warning("[investigate] tool_call: get_pod_status -> parse error (%s)", e)
        return json.dumps({"error": f"Failed to parse K8s API response: {e}"})


def _summarize_container_state(state: dict) -> str:
    if not state:
        return ""
    for key in ("running", "waiting", "terminated"):
        if key in state:
            info = state[key]
            reason = info.get("reason", "")
            message = info.get("message", "")
            if reason:
                return f"{key}: {reason}" + (f" ({message})" if message else "")
            return key
    return ""


def _parse_duration(duration: str) -> int:
    """Parse duration string like '5m', '1h', '30s' to seconds."""
    duration = duration.strip().lower()
    if duration.endswith("h"):
        return int(duration[:-1]) * 3600
    elif duration.endswith("m"):
        return int(duration[:-1]) * 60
    elif duration.endswith("s"):
        return int(duration[:-1])
    try:
        return int(duration)
    except ValueError:
        return 300


ALL_TOOLS = [query_loki_logs, query_prometheus, get_pod_status]
