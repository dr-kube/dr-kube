"""LangGraph 워크플로우

흐름:
  load_alert
    ↓
  gather_context          ← 병렬 logs/events/status/metrics 수집
    ↓
  classify_issue          ← 규칙 기반 분류 (LLM 없음)
    ↓
  [unknown] → notify_skip → END
  [known]   → analyze     ← LLM 근본 원인 분석
    ↓
  plan_fix                ← LLM manifest 수정안 생성
    ↓
  validate_fix
    ↓ 통과
  human_gate              ← 고위험만 Slack interrupt
    ↓ approve / auto
  create_pr
    ↓
  verify_recovery
    ↓ 성공           ↓ 실패
  notify_complete    rollback → END

재시도 경로:
  validate_fix 실패 + retry < 3 → plan_fix (다른 전략)
  validate_fix 실패 + retry >= 3 → escalate → END
  human_gate reject → notify_skip → END
  human_gate modify → plan_fix (human_comment 포함)
"""
import logging
import os

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from delivery_agent.nodes import (
    analyze,
    classify_issue,
    create_pr,
    escalate,
    gather_context,
    human_gate,
    human_gate_wait,
    load_alert,
    notify_complete,
    notify_skip,
    plan_fix,
    validate_fix,
    verify_recovery,
)
from delivery_agent.state import DeliveryState

logger = logging.getLogger("delivery-graph")

MAX_RETRIES = 3


# ── 라우팅 함수 ────────────────────────────────────────

def route_after_classify(state: DeliveryState) -> str:
    if state.get("issue_type") == "unknown":
        logger.info("라우팅: classify → notify_skip (unknown)")
        return "notify_skip"
    return "analyze"


def route_after_analyze(state: DeliveryState) -> str:
    if state.get("status") == "error":
        logger.warning("라우팅: analyze → escalate (error)")
        return "escalate"
    return "plan_fix"


def route_after_validate(state: DeliveryState) -> str:
    errors = state.get("validation_errors", [])
    retry = state.get("retry_count", 0)

    if not errors:
        return "human_gate"

    if retry >= MAX_RETRIES:
        logger.warning("라우팅: validate → escalate (max retries %d)", retry)
        return "escalate"

    logger.info("라우팅: validate → plan_fix (retry=%d)", retry)
    return "plan_fix"


def route_after_human_gate(state: DeliveryState) -> str:
    status = state.get("status")
    if status == "approved":
        return "create_pr"
    if status == "awaiting_approval":
        return "human_gate_wait"
    return "create_pr"


def route_after_human_gate_wait(state: DeliveryState) -> str:
    decision = state.get("human_decision", "")
    if decision == "approve":
        return "create_pr"
    elif decision == "modify":
        return "plan_fix"
    else:  # reject / unknown
        return "notify_skip"


def route_after_verify(state: DeliveryState) -> str:
    if state.get("status") == "recovered":
        return "notify_complete"
    logger.warning("복구 실패 — escalate")
    return "escalate"


# ── 그래프 빌드 ────────────────────────────────────────

def build_graph() -> StateGraph:
    workflow = StateGraph(DeliveryState)

    # 노드 등록
    workflow.add_node("load_alert", load_alert)
    workflow.add_node("gather_context", gather_context)
    workflow.add_node("classify_issue", classify_issue)
    workflow.add_node("analyze", analyze)
    workflow.add_node("plan_fix", plan_fix)
    workflow.add_node("validate_fix", validate_fix)
    workflow.add_node("human_gate", human_gate)
    workflow.add_node("human_gate_wait", human_gate_wait)
    workflow.add_node("create_pr", create_pr)
    workflow.add_node("verify_recovery", verify_recovery)
    workflow.add_node("notify_complete", notify_complete)
    workflow.add_node("notify_skip", notify_skip)
    workflow.add_node("escalate", escalate)

    # 엣지 연결
    workflow.add_edge(START, "load_alert")
    workflow.add_edge("load_alert", "gather_context")
    workflow.add_edge("gather_context", "classify_issue")

    workflow.add_conditional_edges(
        "classify_issue",
        route_after_classify,
        {"analyze": "analyze", "notify_skip": "notify_skip"},
    )

    workflow.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {"plan_fix": "plan_fix", "escalate": "escalate"},
    )

    workflow.add_edge("plan_fix", "validate_fix")

    workflow.add_conditional_edges(
        "validate_fix",
        route_after_validate,
        {"human_gate": "human_gate", "plan_fix": "plan_fix", "escalate": "escalate"},
    )

    workflow.add_conditional_edges(
        "human_gate",
        route_after_human_gate,
        {"create_pr": "create_pr", "human_gate_wait": "human_gate_wait"},
    )

    workflow.add_conditional_edges(
        "human_gate_wait",
        route_after_human_gate_wait,
        {"create_pr": "create_pr", "plan_fix": "plan_fix", "notify_skip": "notify_skip"},
    )

    workflow.add_edge("create_pr", "verify_recovery")

    workflow.add_conditional_edges(
        "verify_recovery",
        route_after_verify,
        {"notify_complete": "notify_complete", "escalate": "escalate"},
    )

    workflow.add_edge("notify_complete", END)
    workflow.add_edge("notify_skip", END)
    workflow.add_edge("escalate", END)

    return workflow


# ── 싱글톤 그래프 (SqliteSaver — pod 재시작 생존) ────────────────────

CHECKPOINT_DB = os.getenv("CHECKPOINT_DB", "/checkpoints/delivery.db")

_singleton_graph = None
_singleton_checkpointer = None


def get_graph():
    """싱글톤 컴파일 그래프 반환. SqliteSaver로 pod 재시작 후에도 체크포인트 유지."""
    global _singleton_graph, _singleton_checkpointer
    if _singleton_graph is None:
        os.makedirs(os.path.dirname(CHECKPOINT_DB), exist_ok=True)
        import sqlite3
        from langgraph.checkpoint.sqlite import SqliteSaver
        conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
        _singleton_checkpointer = SqliteSaver(conn)
        _singleton_graph = build_graph().compile(checkpointer=_singleton_checkpointer)
        logger.info("delivery-agent 그래프 초기화 완료 (checkpoint_db=%s)", CHECKPOINT_DB)
    return _singleton_graph


def create_graph():
    """하위 호환용 — get_graph() 사용 권장"""
    return get_graph()


# ── CLI 실행 (테스트용) ────────────────────────────────

def run(alert_payload: dict, thread_id: str | None = None) -> DeliveryState:
    """Alert payload를 받아 워크플로우 실행. interrupt 발생 시 현재 상태 반환."""
    import uuid as _uuid

    graph = get_graph()
    thread_id = thread_id or str(_uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: DeliveryState = {
        "alert_payload": alert_payload,
        "retry_count": 0,
    }

    result = graph.invoke(initial_state, config=config)
    logger.info("워크플로우 완료/중단: status=%s thread_id=%s", result.get("status"), thread_id)
    return result
