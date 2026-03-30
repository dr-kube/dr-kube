"""Alertmanager 웹훅 수신 서버"""
import os
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from dotenv import load_dotenv

from dr_kube.converter import convert_alertmanager_payload
from dr_kube.converter import derive_values_file
from dr_kube.graph import create_graph
import dr_kube.slack as slack_client

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
_processed_alerts: set = set()

# AGENT-2: PR 번호 → LangGraph 스레드 ID 매핑 (Human-in-the-Loop)
_pr_to_thread: dict[int, str] = {}

# 코파일럿 모드: action_id → {result, channel, ts}
_pending_approvals: dict[str, dict] = {}

# delivery-agent Human-in-the-Loop: action_id → thread_id (파일 기반, pod 재시작 생존)
_PENDING_FILE = os.getenv("PENDING_FILE", "/checkpoints/delivery_pending.json")


def _load_delivery_pending() -> dict[str, str]:
    try:
        import json
        with open(_PENDING_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, Exception):
        return {}


def _save_delivery_pending(d: dict[str, str]) -> None:
    try:
        import json
        os.makedirs(os.path.dirname(_PENDING_FILE), exist_ok=True)
        with open(_PENDING_FILE, "w") as f:
            json.dump(d, f)
    except Exception as e:
        logger.warning("_delivery_pending 저장 실패: %s", e)


_delivery_pending: dict[str, str] = _load_delivery_pending()

# 머지 대기: pr_number → {channel, ts, issue_data, fix_description, pr_url, merged}
_pending_merges: dict[int, dict] = {}

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app_: FastAPI):
    """서버 시작 시 K8s 리소스 워처 시작."""
    try:
        from dr_kube.watcher import start as start_watcher
        start_watcher()
    except Exception as e:
        logger.warning(f"워처 시작 실패 (계속 진행): {e}")
    yield


app = FastAPI(title="DR-Kube Webhook Server", lifespan=lifespan)


def _copilot_mode() -> bool:
    """코파일럿 모드 여부. SLACK_BOT_TOKEN이 설정돼 있으면 활성화."""
    return slack_client.is_configured() and os.getenv("COPILOT_MODE", "true").lower() == "true"


def _is_delivery_app_issue(issue_data: dict) -> bool:
    """delivery-app 네임스페이스 이슈인지 확인"""
    return issue_data.get("namespace", "") == "delivery-app"


def process_delivery_issue(issue_data: dict) -> None:
    """delivery-app 전용 LangGraph 에이전트로 처리"""
    try:
        from delivery_agent.graph import run as delivery_run
        alert_payload = issue_data.get("_raw_alert", issue_data)
        thread_id = issue_data.get("id", "")
        result = delivery_run(alert_payload=alert_payload, thread_id=thread_id)

        # Slack 승인 대기 중이면 action_id → thread_id 등록 (파일에도 저장)
        if result.get("status") == "awaiting_approval":
            action_id = result.get("slack_action_id", "")
            if action_id and thread_id:
                _delivery_pending[action_id] = thread_id
                _save_delivery_pending(_delivery_pending)
                logger.info(
                    "delivery-agent 승인 대기 등록: action_id=%s thread_id=%s",
                    action_id, thread_id,
                )

        logger.info(
            "delivery-agent 완료: id=%s status=%s pr=%s",
            issue_data.get("id"), result.get("status"), result.get("pr_url"),
        )
    except Exception as e:
        logger.error("delivery-agent 실패: %s", e, exc_info=True)


def resume_delivery(thread_id: str, decision: str) -> None:
    """Slack 버튼 클릭 후 delivery-agent LangGraph 재개"""
    try:
        from delivery_agent.graph import get_graph
        from langgraph.types import Command

        graph = get_graph()
        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke(Command(resume=decision), config=config)
        logger.info(
            "delivery-agent 재개 완료: thread=%s status=%s pr=%s",
            thread_id, result.get("status"), result.get("pr_url"),
        )
    except Exception as e:
        logger.error("delivery-agent 재개 실패: thread=%s error=%s", thread_id, e, exc_info=True)


def resume_delivery_with_comment(thread_id: str, comment: str) -> None:
    """수정 요청 코멘트와 함께 delivery-agent 재개 (plan_fix 경로)"""
    try:
        from delivery_agent.graph import get_graph
        from langgraph.types import Command

        graph = get_graph()
        config = {"configurable": {"thread_id": thread_id}}
        # human_comment를 state에 주입한 뒤 "modify"로 재개
        # graph.update_state로 comment 추가 후 resume
        graph.update_state(config, {"human_comment": comment})
        result = graph.invoke(Command(resume="modify"), config=config)
        logger.info(
            "delivery-agent 수정 재개 완료: thread=%s status=%s",
            thread_id, result.get("status"),
        )
    except Exception as e:
        logger.error("delivery-agent 수정 재개 실패: thread=%s error=%s", thread_id, e, exc_info=True)


def process_issue(issue_data: dict, with_pr: bool = False, thread_ts: str = ""):
    """이슈를 LangGraph 파이프라인으로 처리.

    네임스페이스별 에이전트 라우팅:
      - delivery-app → delivery_agent (전용 에이전트)
      - 그 외         → dr_kube 기존 에이전트

    코파일럿 모드(SLACK_BOT_TOKEN 설정 시):
      - 분석만 수행(with_pr=False) → Slack에 제안 메시지 전송
      - 사람이 ✅ 버튼 클릭 → approve_issue()에서 PR 생성

    일반 모드:
      - with_pr 값에 따라 분석 or 분석+PR 자동 생성
    """
    issue_id = issue_data["id"]
    logger.info(f"처리 시작: {issue_id} (type={issue_data['type']}, with_pr={with_pr})")

    # delivery-app은 전용 에이전트로 처리
    if _is_delivery_app_issue(issue_data):
        logger.info("delivery-app 이슈 → delivery_agent로 라우팅")
        process_delivery_issue(issue_data)
        return

    # 코파일럿 모드: 항상 분석만 먼저
    copilot = _copilot_mode()
    run_with_pr = False if copilot else with_pr

    try:
        graph = create_graph(with_pr=run_with_pr)
        result = graph.invoke({"issue_data": issue_data})

        if result.get("error"):
            logger.error(f"처리 실패: {issue_id} - {result['error']}")
            return

        logger.info(
            f"처리 완료: {issue_id} - "
            f"status={result.get('status')} route={result.get('route')} "
            f"fix_method={result.get('fix_method')}"
        )
        if result.get("root_cause"):
            logger.info(f"[분석] 근본 원인: {result['root_cause']}")
        if result.get("suggestions"):
            for i, s in enumerate(result["suggestions"][:3], 1):
                logger.info(f"[분석] 해결책 {i}: {s}")

        # 코파일럿 모드: Slack에 제안 메시지 전송
        if copilot and result.get("fix_content"):
            import uuid
            action_id = str(uuid.uuid4())[:8]
            ok, channel, ts = slack_client.send_proposal(result, action_id, thread_ts=thread_ts)
            if ok:
                _pending_approvals[action_id] = {
                    "result": result,
                    "issue_data": issue_data,
                    "channel": channel,
                    "ts": ts,
                }
                logger.info(f"코파일럿 대기 중: action_id={action_id} channel={channel} obj_id={id(_pending_approvals)}")
            return

        # 일반 모드 PR 처리
        if result.get("pr_url"):
            logger.info(f"PR 생성됨: {result['pr_url']}")
            pr_number = result.get("pr_number", 0)
            if pr_number:
                _pr_to_thread[pr_number] = issue_id

    except (ConnectionRefusedError, OSError) as e:
        if getattr(e, "errno", None) == 111 or isinstance(e, ConnectionRefusedError):
            logger.error(
                f"처리 실패: {issue_id} - Connection refused. "
                "LLM 연결 실패: GITHUB_TOKEN 또는 COPILOT_TOKEN 설정 확인."
            )
        else:
            logger.error(f"처리 실패: {issue_id} - {e}")
    except Exception as e:
        logger.error(f"처리 중 예외: {issue_id} - {e}")


def approve_issue(action_id: str) -> None:
    """Slack ✅ 버튼 클릭 시 호출 - 저장된 분석 결과로 PR 생성."""
    logger.info(f"approve_issue 호출: action_id={action_id} pending_keys={list(_pending_approvals.keys())} obj_id={id(_pending_approvals)}")
    entry = _pending_approvals.get(action_id)
    if not entry:
        logger.error(f"approve_issue: action_id={action_id} 없음")
        return

    result = entry["result"]
    issue_data = entry["issue_data"]
    channel = entry["channel"]
    ts = entry["ts"]

    slack_client.update_proposal(channel, ts, "approved", "PR 생성 중...")
    logger.info(f"PR 생성 시작: action_id={action_id} issue={issue_data['id']}")

    try:
        from dr_kube.graph import create_pr
        pr_result = create_pr({
            "issue_data": issue_data,
            "target_file": result.get("target_file", ""),
            "original_yaml": result.get("original_yaml", ""),
            "root_cause": result.get("root_cause", ""),
            "severity": result.get("severity", "medium"),
            "suggestions": result.get("suggestions", []),
            "fix_content": result.get("fix_content", ""),
            "fix_description": result.get("fix_description", ""),
            "fix_method": result.get("fix_method", "llm"),
            "status": "validated",
        })

        if pr_result.get("pr_url"):
            pr_url = pr_result["pr_url"]
            pr_number = pr_result.get("pr_number", 0)
            logger.info(f"PR 생성 완료: {pr_url}")

            pr_ts = slack_client.send_pr_ready(result, pr_url, pr_number, channel, ts)

            if pr_number:
                _pr_to_thread[pr_number] = issue_data["id"]
                _pending_merges[pr_number] = {
                    "channel": channel,
                    "ts": ts,
                    "pr_ts": pr_ts,
                    "issue_data": issue_data,
                    "fix_description": result.get("fix_description", ""),
                    "fix_content": result.get("fix_content", ""),
                    "pr_url": pr_url,
                    "merged": False,
                }
        else:
            error = pr_result.get("error", "알 수 없는 오류")
            slack_client.update_proposal(channel, ts, "error", error)
            logger.error(f"PR 생성 실패: {error}")
    except Exception as e:
        slack_client.update_proposal(channel, ts, "error", str(e))
        logger.error(f"approve_issue 예외: {e}")
    finally:
        _pending_approvals.pop(action_id, None)


def merge_and_notify(pr_number: int) -> None:
    """Slack ⚡ 머지 버튼 클릭 시 호출 - PR squash merge 후 Slack 업데이트."""
    entry = _pending_merges.get(pr_number)
    if not entry:
        logger.error(f"merge_and_notify: pr_number={pr_number} 없음")
        return

    channel = entry["channel"]
    ts = entry["ts"]
    pr_ts = entry.get("pr_ts") or ts

    logger.info(f"PR 머지 시작: pr_number={pr_number}")
    try:
        from dr_kube.github import GitHubClient
        gh = GitHubClient(str(PROJECT_ROOT))
        success, msg = gh.merge_pr(pr_number)

        if success:
            entry["merged"] = True
            slack_client.update_proposal(channel, pr_ts, "merged", f"#{pr_number}")
            logger.info(f"PR 머지 완료: pr_number={pr_number}")
        else:
            slack_client.update_proposal(channel, pr_ts, "error", f"머지 실패: {msg}")
            logger.error(f"PR 머지 실패: pr_number={pr_number} - {msg}")
            _pending_merges.pop(pr_number, None)
    except Exception as e:
        slack_client.update_proposal(channel, pr_ts, "error", str(e))
        logger.error(f"merge_and_notify 예외: {e}")
        _pending_merges.pop(pr_number, None)


def modify_pr_issue(pr_number: int, comment: str) -> None:
    """PR 생성 후 수정 요청 - 기존 PR 닫고 재분석 → 새 PR 생성."""
    entry = _pending_merges.pop(pr_number, None)
    if not entry:
        logger.error(f"modify_pr_issue: pr_number={pr_number} 없음")
        return

    channel = entry["channel"]
    ts = entry["ts"]
    issue_data = dict(entry["issue_data"])
    previous_fix = entry.get("fix_content", "")

    logger.info(f"PR 수정 요청: pr_number={pr_number} comment={comment[:50]}")
    slack_client.update_proposal(channel, ts, "modified", f"PR #{pr_number} 닫고 재분석 중...")

    # 기존 PR 닫기
    try:
        from dr_kube.github import GitHubClient
        gh = GitHubClient(str(PROJECT_ROOT))
        gh.close_pr(pr_number)
        logger.info(f"기존 PR 닫힘: pr_number={pr_number}")
    except Exception as e:
        logger.warning(f"PR 닫기 실패 (계속 진행): {e}")

    # 피드백 주입 후 재분석
    issue_data["_review_comment"] = comment
    issue_data["_previous_fix"] = previous_fix
    process_issue(issue_data, with_pr=False, thread_ts=ts)


def modify_issue(action_id: str, comment: str) -> None:
    """Slack ✏️ 수정 요청 처리 - 댓글 주입 후 LLM 재분석 → 새 제안 전송."""
    entry = _pending_approvals.pop(action_id, None)
    if not entry:
        logger.error(f"modify_issue: action_id={action_id} 없음")
        return

    issue_data = dict(entry["issue_data"])
    channel = entry["channel"]
    ts = entry["ts"]

    slack_client.update_proposal(channel, ts, "modified", comment)
    logger.info(f"수정 요청 처리: action_id={action_id} comment={comment[:50]}")

    issue_data["_review_comment"] = comment
    issue_data["_previous_fix"] = entry["result"].get("fix_content", "")
    process_issue(issue_data, with_pr=False, thread_ts=ts)


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
    """환경변수 기반 런타임 비용 정책 계산."""
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
    if len(issues) == 1:
        return issues[0]

    sorted_ids = sorted(i.get("id", "") for i in issues)
    sorted_fps = sorted(i.get("fingerprint", "") for i in issues)
    seed = "|".join(sorted_ids + sorted_fps)
    cid = hashlib.md5(seed.encode()).hexdigest()[:10]

    counter: dict[str, int] = {}
    for issue in issues:
        res = issue.get("resource", "unknown")
        counter[res] = counter.get(res, 0) + 1
    primary_resource = max(counter, key=counter.get) if counter else issues[0].get("resource", "unknown")
    namespace = issues[0].get("namespace", "default")
    values_file = derive_values_file(primary_resource, namespace)
    if not values_file:
        for issue in issues:
            candidate = issue.get("values_file", "")
            if candidate:
                values_file = candidate
                break

    merged_logs: list[str] = []
    for issue in issues:
        merged_logs.append(
            f"[{issue.get('type','unknown')}] "
            f"ns={issue.get('namespace','default')} "
            f"resource={issue.get('resource','unknown')} "
            f"msg={issue.get('error_message','')}"
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


@app.post("/webhook/slack/action")
async def slack_action(request: Request, background_tasks: BackgroundTasks):
    """Slack Interactive Components 수신 (버튼 클릭 + 모달 제출).

    Slack App 설정:
      Interactivity & Shortcuts → Request URL: https://{your-domain}/webhook/slack/action
    """
    from urllib.parse import unquote_plus
    import json as _json

    raw = await request.body()
    body_str = unquote_plus(raw.decode())
    if body_str.startswith("payload="):
        body_str = body_str[len("payload="):]

    try:
        payload = _json.loads(body_str)
    except Exception:
        raise HTTPException(status_code=400, detail="payload 파싱 실패")

    payload_type = payload.get("type", "")

    if payload_type == "block_actions":
        actions = payload.get("actions", [])
        if not actions:
            return {"ok": True}

        action = actions[0]
        action_id_btn = action.get("action_id", "")
        value = action.get("value", "")

        if action_id_btn == "approve":
            # 파일에서 직접 읽어 소스로 사용 (thread import 객체 불일치 방지)
            _pending_file = _load_delivery_pending()
            if value in _pending_file:
                thread_id = _pending_file.pop(value)
                _delivery_pending.pop(value, None)
                _save_delivery_pending(_pending_file)
                background_tasks.add_task(resume_delivery, thread_id, "approve")
            elif value in _delivery_pending:
                thread_id = _delivery_pending.pop(value)
                _save_delivery_pending(_delivery_pending)
                background_tasks.add_task(resume_delivery, thread_id, "approve")
            else:
                background_tasks.add_task(approve_issue, value)
            return {"ok": True}

        elif action_id_btn == "reject":
            _pending_file = _load_delivery_pending()
            if value in _pending_file:
                thread_id = _pending_file.pop(value)
                _delivery_pending.pop(value, None)
                _save_delivery_pending(_pending_file)
                background_tasks.add_task(resume_delivery, thread_id, "reject")
            elif value in _delivery_pending:
                thread_id = _delivery_pending.pop(value)
                _save_delivery_pending(_delivery_pending)
                background_tasks.add_task(resume_delivery, thread_id, "reject")
            else:
                entry = _pending_approvals.pop(value, None)
                if entry:
                    slack_client.update_proposal(entry["channel"], entry["ts"], "rejected")
            return {"ok": True}

        elif action_id_btn == "merge_pr":
            try:
                pr_number = int(value)
            except ValueError:
                raise HTTPException(status_code=400, detail="invalid pr_number")
            background_tasks.add_task(merge_and_notify, pr_number)
            return {"ok": True}

        elif action_id_btn == "view_pr":
            return {"ok": True}

        elif action_id_btn == "request_modify_pr":
            # PR 생성 후 수정 요청: 모달 열기
            try:
                pr_number = int(value)
            except ValueError:
                raise HTTPException(status_code=400, detail="invalid pr_number")
            trigger_id = payload.get("trigger_id", "")
            # _pending_merges의 action_id 역할을 pr_number로 대체
            slack_client.open_modify_modal(trigger_id, f"pr_{pr_number}")
            return {"ok": True}

        elif action_id_btn == "request_modify":
            trigger_id = payload.get("trigger_id", "")
            # delivery-agent와 일반 모드 모두 동일 모달 → callback_id로 구분
            slack_client.open_modify_modal(trigger_id, value)
            return {"ok": True}

        elif action_id_btn == "restore_resource":
            background_tasks.add_task(_do_restore, value, payload)
            return {"ok": True}

        elif action_id_btn == "ignore_resource":
            from dr_kube.watcher import _restore_pending
            entry = _restore_pending.pop(value, None)
            if entry:
                try:
                    from slack_sdk import WebClient
                    WebClient(token=os.getenv("SLACK_BOT_TOKEN", "")).chat_update(
                        channel=entry.get("channel", ""),
                        ts=entry.get("ts", ""),
                        blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "❌ *무시됨*"}}],
                        text="DR-Kube: 무시됨",
                    )
                except Exception:
                    pass
            return {"ok": True}

    elif payload_type == "view_submission":
        callback_id = payload.get("view", {}).get("callback_id", "")
        if callback_id.startswith("modify_modal_"):
            action_id_modal = callback_id[len("modify_modal_"):]
            comment = (
                payload.get("view", {})
                .get("state", {})
                .get("values", {})
                .get("modify_comment", {})
                .get("comment", {})
                .get("value", "")
            )
            # PR 생성 후 수정 요청: pr_{pr_number} 형식
            if action_id_modal.startswith("pr_"):
                try:
                    pr_number = int(action_id_modal[3:])
                    background_tasks.add_task(modify_pr_issue, pr_number, comment)
                except ValueError:
                    pass
            elif action_id_modal in _delivery_pending:
                # delivery-agent 수정 요청: LangGraph resume with "modify"
                thread_id = _delivery_pending.pop(action_id_modal)
                # human_comment를 상태에 반영하기 위해 별도 처리
                background_tasks.add_task(resume_delivery_with_comment, thread_id, comment)
            else:
                background_tasks.add_task(modify_issue, action_id_modal, comment)
            return {"response_action": "clear"}

    return {"ok": True}


@app.post("/webhook/alertmanager")
async def alertmanager_webhook(request: Request, background_tasks: BackgroundTasks):
    """Alertmanager 웹훅 수신"""
    payload = await request.json()
    raw_alerts = payload.get("alerts", [])
    total = len(raw_alerts)

    for idx, raw in enumerate(raw_alerts, 1):
        labels = raw.get("labels", {})
        annotations = raw.get("annotations", {})
        alertname = labels.get("alertname", "Unknown")
        severity = labels.get("severity", "unknown")
        namespace = labels.get("namespace", "unknown")
        status = raw.get("status", "unknown")
        source = "loki" if alertname.startswith("Log") else "prometheus"
        logger.info(
            "[webhook] alert %d/%d source=%s alertname=%s severity=%s "
            "ns=%s status=%s summary=%s",
            idx, total, source, alertname, severity,
            namespace, status, annotations.get("summary", ""),
        )

    issues = convert_alertmanager_payload(payload)
    logger.info("[webhook] received=%d, firing(to process)=%d", total, len(issues))

    with_pr = os.getenv("AUTO_PR", "false").lower() == "true"
    composite_mode = os.getenv("COMPOSITE_INCIDENT_MODE", "true").lower() == "true"
    limits = _resolve_runtime_limits()
    max_issues_with_pr = _parse_int_env("MAX_ISSUES_PER_WEBHOOK_WITH_PR", 1)
    pr_group_cooldown_minutes = _parse_int_env("PR_GROUP_COOLDOWN_MINUTES", 180)

    if composite_mode and len(issues) > 1:
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

        if _is_duplicate_within_cooldown(fingerprint, limits["dedup_cooldown_minutes"]):
            logger.info(f"중복 스킵(쿨다운): {alert_id} fp={fingerprint}")
            skipped_duplicate.append(alert_id)
            continue

        if _is_over_daily_limit(limits["max_calls_per_day"]):
            logger.warning(
                "일일 예산 초과 스킵: %s (count=%s, limit=%s)",
                alert_id, _daily_usage["count"], limits["max_calls_per_day"],
            )
            skipped_budget.append(alert_id)
            continue

        if with_pr:
            group_key = _issue_group_key(issue)
            if _is_recent_pr_group(group_key, pr_group_cooldown_minutes):
                logger.info(
                    "그룹 쿨다운 스킵: %s group=%s cooldown=%sm",
                    alert_id, group_key, pr_group_cooldown_minutes,
                )
                skipped_group_cooldown.append(alert_id)
                continue

            if max_issues_with_pr > 0 and queued_count >= max_issues_with_pr:
                logger.info(
                    "배치 상한 스킵: %s queued=%s limit=%s",
                    alert_id, queued_count, max_issues_with_pr,
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


def _do_restore(action_id: str, payload: dict) -> None:
    """Slack [복구] 버튼 클릭 시 kubectl apply로 리소스 복구."""
    from dr_kube.watcher import restore_resource, _restore_pending
    entry = _restore_pending.get(action_id)
    channel = (entry or {}).get("channel", "")
    ts = (entry or {}).get("ts", "")

    success, msg = restore_resource(action_id)

    try:
        from slack_sdk import WebClient
        client = WebClient(token=os.getenv("SLACK_BOT_TOKEN", ""))
        if channel and ts:
            text = f"✅ *복구 완료*\n{msg}" if success else f"⚠️ *복구 실패*\n{msg}"
            client.chat_update(
                channel=channel,
                ts=ts,
                blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": text}}],
                text=text,
            )
    except Exception as e:
        logger.error(f"복구 알림 업데이트 실패: {e}")


def _verify_and_notify(pr_number: int, entry: dict) -> None:
    """ArgoCD sync 후 복구 여부를 검증하고 Slack에 결과를 전송."""
    from dr_kube.verifier import verify_fix
    issue_data = entry.get("issue_data", {})
    namespace = issue_data.get("namespace", "")
    resource = issue_data.get("resource", "")
    fingerprint = issue_data.get("fingerprint", "")
    channel = entry["channel"]
    ts = entry["ts"]

    logger.info(f"복구 검증 시작: pr={pr_number} namespace={namespace} resource={resource}")

    success, detail = verify_fix(
        namespace=namespace,
        resource=resource,
        fingerprint=fingerprint,
        poll_interval=30,
        timeout=600,
    )

    if success:
        logger.info(f"복구 확인됨: pr={pr_number} {detail}")
        slack_client.send_recovery_complete(
            channel=channel,
            ts=ts,
            issue_data=issue_data,
            fix_description=entry.get("fix_description", ""),
            pr_url=entry.get("pr_url", ""),
            pr_number=pr_number,
        )
    else:
        logger.warning(f"복구 미확인: pr={pr_number} {detail}")
        slack_client.update_proposal(
            channel=channel,
            ts=ts,
            status="error",
            detail=f"⚠️ 복구 미확인 (10분 경과)\n{detail}\nPR: {entry.get('pr_url', '')}",
        )

    _pending_merges.pop(pr_number, None)


@app.post("/webhook/argocd")
async def argocd_webhook(request: Request, background_tasks: BackgroundTasks):
    """ArgoCD Notifications webhook (sync-failed, health-degraded, synced)."""
    body = await request.json()
    issue_id = body.get("id") or "argocd-unknown"
    issue_type = body.get("type", "")
    logger.info(f"ArgoCD 이벤트 수신: {issue_id} (type={issue_type})")

    # argocd_synced: 복구 검증 후 완료 알림
    if issue_type == "argocd_synced":
        merged_entry = None
        merged_pr_number = None
        for pr_num, entry in list(_pending_merges.items()):
            if entry.get("merged"):
                merged_entry = entry
                merged_pr_number = pr_num
                break

        if merged_entry and slack_client.is_configured():
            background_tasks.add_task(_verify_and_notify, merged_pr_number, merged_entry)
            logger.info(f"복구 검증 시작 (백그라운드): pr_number={merged_pr_number}")
        else:
            logger.info("argocd_synced 수신 - 대기 중인 머지 없음, 스킵")
        return {"status": "accepted", "queued": 0, "type": "argocd_synced"}

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
