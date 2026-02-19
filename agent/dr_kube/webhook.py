"""Alertmanager 웹훅 수신 서버"""
import os
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, BackgroundTasks, Request
from dotenv import load_dotenv

from dr_kube.converter import convert_alertmanager_payload
from dr_kube.converter import derive_values_file
from dr_kube.graph import create_graph

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("dr-kube-webhook")

# LLM 비용 보호 설정
DEFAULT_MAX_LLM_CALLS_PER_DAY = int(os.getenv("MAX_LLM_CALLS_PER_DAY", "20"))
DEFAULT_DEDUP_COOLDOWN_MINUTES = int(os.getenv("DEDUP_COOLDOWN_MINUTES", "60"))

# 간단한 프로세스 메모리 캐시
_daily_usage = {"date": datetime.now(timezone.utc).date().isoformat(), "count": 0}
_processed_fingerprints: dict[str, datetime] = {}
_recent_pr_groups: dict[str, datetime] = {}

app = FastAPI(title="DR-Kube Webhook Server")


def process_issue(issue_data: dict, with_pr: bool = False):
    """이슈를 LangGraph 파이프라인으로 처리"""
    logger.info(f"처리 시작: {issue_data['id']} (type={issue_data['type']}, with_pr={with_pr})")
    try:
        graph = create_graph(with_pr=with_pr)
        result = graph.invoke({"issue_data": issue_data})

        if result.get("error"):
            logger.error(f"처리 실패: {issue_data['id']} - {result['error']}")
        else:
            logger.info(f"처리 완료: {issue_data['id']} - status={result.get('status')}")
            if result.get("pr_url"):
                logger.info(f"PR 생성됨: {result['pr_url']}")
            # 분석 결과 요약 (LLM이 한 일을 로그로 남김)
            if result.get("root_cause"):
                logger.info(f"[분석] 근본 원인: {result['root_cause']}")
            if result.get("suggestions"):
                for i, s in enumerate(result["suggestions"][:5], 1):
                    logger.info(f"[분석] 해결책 {i}: {s}")
    except (ConnectionRefusedError, OSError) as e:
        if getattr(e, "errno", None) == 111 or isinstance(e, ConnectionRefusedError):
            logger.error(
                f"처리 실패: {issue_data['id']} - Connection refused. "
                "LLM 연결 실패 가능성: Ollama 미실행 시 GEMINI_API_KEY 설정, 또는 Ollama 실행 확인."
            )
        else:
            logger.error(f"처리 실패: {issue_data['id']} - {e}")
    except Exception as e:
        logger.error(f"처리 중 예외: {issue_data['id']} - {e}")


def _reset_daily_usage_if_needed() -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    if _daily_usage["date"] != today:
        _daily_usage["date"] = today
        _daily_usage["count"] = 0


def _parse_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _parse_utc_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _resolve_runtime_limits() -> dict:
    """환경변수 기반 런타임 비용 정책 계산.

    - COST_MODE: normal | high | unlimited
    - OVERRIDE_UNTIL_UTC: 이 시각까지 OVERRIDE_COST_MODE 강제 적용
    - MAX_LLM_CALLS_PER_DAY=0: 무제한
    """
    now = datetime.now(timezone.utc)
    mode = os.getenv("COST_MODE", "normal").strip().lower()
    if mode not in {"normal", "high", "unlimited"}:
        mode = "normal"

    override_until = _parse_utc_datetime(os.getenv("OVERRIDE_UNTIL_UTC", ""))
    override_active = bool(override_until and now < override_until)
    if override_active:
        override_mode = os.getenv("OVERRIDE_COST_MODE", "high").strip().lower()
        if override_mode in {"normal", "high", "unlimited"}:
            mode = override_mode

    normal_max = _parse_int_env("MAX_LLM_CALLS_PER_DAY", DEFAULT_MAX_LLM_CALLS_PER_DAY)
    normal_dedup = _parse_int_env("DEDUP_COOLDOWN_MINUTES", DEFAULT_DEDUP_COOLDOWN_MINUTES)
    high_max = _parse_int_env("HIGH_MAX_LLM_CALLS_PER_DAY", 200)
    high_dedup = _parse_int_env("HIGH_DEDUP_COOLDOWN_MINUTES", 10)

    if mode == "unlimited":
        max_calls = 0
        dedup_minutes = 1
    elif mode == "high":
        max_calls = high_max
        dedup_minutes = high_dedup
    else:
        max_calls = normal_max
        dedup_minutes = normal_dedup

    return {
        "mode": mode,
        "max_calls_per_day": max_calls,
        "dedup_cooldown_minutes": dedup_minutes,
        "override_active": override_active,
        "override_until_utc": override_until.isoformat() if override_until else "",
    }


def _is_over_daily_limit(max_calls_per_day: int) -> bool:
    _reset_daily_usage_if_needed()
    if max_calls_per_day == 0:
        return False
    return _daily_usage["count"] >= max_calls_per_day


def _consume_daily_budget() -> None:
    _reset_daily_usage_if_needed()
    _daily_usage["count"] += 1


def _is_duplicate_within_cooldown(fingerprint: str, cooldown_minutes: int) -> bool:
    if not fingerprint:
        return False
    if cooldown_minutes <= 0:
        return False
    now = datetime.now(timezone.utc)
    last_seen = _processed_fingerprints.get(fingerprint)
    if last_seen and (now - last_seen) < timedelta(minutes=cooldown_minutes):
        return True
    _processed_fingerprints[fingerprint] = now
    return False


def _issue_group_key(issue: dict) -> str:
    """PR 중복 제어용 그룹 키."""
    target_file = issue.get("values_file", "")
    if target_file:
        return f"file:{target_file}"
    return (
        f"resource:{issue.get('namespace', 'default')}:"
        f"{issue.get('resource', 'unknown')}:{issue.get('type', 'unknown')}"
    )


def _is_recent_pr_group(group_key: str, cooldown_minutes: int) -> bool:
    if cooldown_minutes <= 0:
        return False
    now = datetime.now(timezone.utc)
    last_seen = _recent_pr_groups.get(group_key)
    if last_seen and (now - last_seen) < timedelta(minutes=cooldown_minutes):
        return True
    _recent_pr_groups[group_key] = now
    return False


def _build_composite_issue(issues: list[dict]) -> dict:
    """여러 알림을 하나의 복합 인시던트 이슈로 합성."""
    if len(issues) == 1:
        return issues[0]

    sorted_ids = sorted(i.get("id", "") for i in issues)
    sorted_fps = sorted(i.get("fingerprint", "") for i in issues)
    seed = "|".join(sorted_ids + sorted_fps)
    cid = hashlib.md5(seed.encode()).hexdigest()[:10]

    # resource 빈도 기반 대표값 선택
    counter: dict[str, int] = {}
    for issue in issues:
        res = issue.get("resource", "unknown")
        counter[res] = counter.get(res, 0) + 1
    primary_resource = max(counter, key=counter.get) if counter else issues[0].get("resource", "unknown")
    namespace = issues[0].get("namespace", "default")
    values_file = derive_values_file(primary_resource, namespace)
    if not values_file:
        # 입력 alert 중 유효한 values_file이 있다면 우선 사용
        for issue in issues:
            candidate = issue.get("values_file", "")
            if candidate:
                values_file = candidate
                break

    # 전체 컨텍스트를 logs에 합쳐서 LLM이 복합 장애를 보게 함
    merged_logs: list[str] = []
    for issue in issues:
        merged_logs.append(
            (
                f"[{issue.get('type','unknown')}] "
                f"ns={issue.get('namespace','default')} "
                f"resource={issue.get('resource','unknown')} "
                f"msg={issue.get('error_message','')}"
            )
        )
        merged_logs.extend(issue.get("logs", []))

    return {
        "id": f"incident-{cid}",
        "fingerprint": f"composite-{cid}",
        "type": "composite_incident",
        "namespace": namespace,
        "resource": primary_resource,
        "error_message": f"복합 장애 감지: {len(issues)} alerts",
        "logs": merged_logs,
        "timestamp": issues[0].get("timestamp", ""),
        "values_file": values_file,
    }


def _group_issues_for_composite(issues: list[dict]) -> list[dict]:
    """namespace + values_file 단위로 issue를 그룹핑해 composite 생성."""
    if len(issues) <= 1:
        return issues

    groups: dict[tuple[str, str], list[dict]] = {}
    for issue in issues:
        key = (
            issue.get("namespace", "default"),
            issue.get("values_file", ""),
        )
        groups.setdefault(key, []).append(issue)

    merged: list[dict] = []
    for grouped in groups.values():
        if len(grouped) > 1:
            merged.append(_build_composite_issue(grouped))
        else:
            merged.append(grouped[0])
    return merged


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/alertmanager")
async def alertmanager_webhook(request: Request, background_tasks: BackgroundTasks):
    """Alertmanager 웹훅 수신"""
    payload = await request.json()

    issues = convert_alertmanager_payload(payload)
    total = len(payload.get("alerts", []))
    logger.info(f"알림 수신: {total}건, 처리 대상(firing): {len(issues)}건")

    with_pr = os.getenv("AUTO_PR", "false").lower() == "true"
    composite_mode = os.getenv("COMPOSITE_INCIDENT_MODE", "true").lower() == "true"
    limits = _resolve_runtime_limits()
    max_issues_with_pr = _parse_int_env("MAX_ISSUES_PER_WEBHOOK_WITH_PR", 1)
    pr_group_cooldown_minutes = _parse_int_env("PR_GROUP_COOLDOWN_MINUTES", 180)

    if with_pr and composite_mode and len(issues) > 1:
        issues = _group_issues_for_composite(issues)

    queued = []
    skipped_duplicate = []
    skipped_budget = []
    skipped_group_cooldown = []
    skipped_batch_limit = []
    queued_count = 0
    for issue in issues:
        alert_id = issue["id"]
        fingerprint = issue.get("fingerprint", "")

        if _is_duplicate_within_cooldown(
            fingerprint, limits["dedup_cooldown_minutes"]
        ):
            logger.info(f"중복 스킵(쿨다운): {alert_id} fp={fingerprint}")
            skipped_duplicate.append(alert_id)
            continue

        if _is_over_daily_limit(limits["max_calls_per_day"]):
            logger.warning(
                "일일 예산 초과 스킵: %s (count=%s, limit=%s)",
                alert_id,
                _daily_usage["count"],
                limits["max_calls_per_day"],
            )
            skipped_budget.append(alert_id)
            continue

        if with_pr:
            group_key = _issue_group_key(issue)
            if _is_recent_pr_group(group_key, pr_group_cooldown_minutes):
                logger.info(
                    "그룹 쿨다운 스킵: %s group=%s cooldown=%sm",
                    alert_id,
                    group_key,
                    pr_group_cooldown_minutes,
                )
                skipped_group_cooldown.append(alert_id)
                continue

            # PR 모드에서는 한 번의 Alertmanager 요청당 최대 N건만 처리
            if max_issues_with_pr > 0 and queued_count >= max_issues_with_pr:
                logger.info(
                    "배치 상한 스킵: %s queued=%s limit=%s",
                    alert_id,
                    queued_count,
                    max_issues_with_pr,
                )
                skipped_batch_limit.append(alert_id)
                continue

        _consume_daily_budget()
        background_tasks.add_task(process_issue, issue, with_pr)
        queued.append(alert_id)
        queued_count += 1

    return {
        "status": "accepted",
        "daily_usage": {
            "date_utc": _daily_usage["date"],
            "count": _daily_usage["count"],
            "limit": limits["max_calls_per_day"],
        },
        "cost_mode": limits["mode"],
        "override_active": limits["override_active"],
        "override_until_utc": limits["override_until_utc"],
        "queued": len(queued),
        "alert_ids": queued,
        "skipped_duplicate": skipped_duplicate,
        "skipped_budget": skipped_budget,
        "skipped_group_cooldown": skipped_group_cooldown,
        "skipped_batch_limit": skipped_batch_limit,
    }


@app.post("/webhook/argocd")
async def argocd_webhook(request: Request, background_tasks: BackgroundTasks):
    """ArgoCD Notifications webhook (sync-failed, health-degraded). Body = single issue_data JSON."""
    body = await request.json()
    issue_id = body.get("id") or "argocd-unknown"
    logger.info(f"ArgoCD 이벤트 수신: {issue_id} (type={body.get('type', '')})")

    if issue_id in _processed_alerts:
        logger.info(f"중복 스킵: {issue_id}")
        return {"status": "accepted", "queued": 0, "reason": "duplicate"}

    _processed_alerts.add(issue_id)
    with_pr = os.getenv("AUTO_PR", "false").lower() == "true"
    background_tasks.add_task(process_issue, body, with_pr)
    return {"status": "accepted", "queued": 1, "id": issue_id}


def main():
    import uvicorn

    host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("WEBHOOK_PORT", "8080"))
    limits = _resolve_runtime_limits()

    logger.info(f"DR-Kube 웹훅 서버 시작: http://{host}:{port}")
    logger.info(f"AUTO_PR={os.getenv('AUTO_PR', 'false')}")
    logger.info(
        "COST_MODE=%s max_calls_per_day=%s dedup_cooldown_minutes=%s override_active=%s",
        limits["mode"],
        limits["max_calls_per_day"],
        limits["dedup_cooldown_minutes"],
        limits["override_active"],
    )
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
