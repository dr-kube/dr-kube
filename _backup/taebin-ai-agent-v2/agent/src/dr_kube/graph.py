"""LangGraph 워크플로우 정의"""
from langgraph.graph import StateGraph, END
from typing import Literal

from src.dr_kube.state import AgentState
from src.dr_kube.nodes.collect_logs import collect_logs
from src.dr_kube.nodes.classify_error import classify_error
from src.dr_kube.nodes.analyze_root_cause import analyze_root_cause
from src.dr_kube.nodes.generate_action import generate_action
from src.dr_kube.nodes.verify_recovery import verify_recovery


def should_continue(state: AgentState) -> Literal["generate_action", "end"]:
    """
    사용자 피드백이 필요한지 확인
    
    Args:
        state: 현재 상태
        
    Returns:
        다음 노드 이름
    """
    if state.get("user_approved", False):
        return "generate_action"
    return "end"


def create_graph() -> StateGraph:
    """
    LangGraph 워크플로우 생성
    
    Returns:
        컴파일된 StateGraph 인스턴스
    """
    workflow = StateGraph(AgentState)
    
    # 노드 추가
    workflow.add_node("collect_logs", collect_logs)
    workflow.add_node("classify_error", classify_error)
    workflow.add_node("analyze_root_cause", analyze_root_cause)
    workflow.add_node("get_user_feedback", lambda state: state)  # Phase 1: 자동 승인
    workflow.add_node("generate_action", generate_action)
    workflow.add_node("commit_changes", lambda state: state)  # Phase 1: 시뮬레이션
    workflow.add_node("verify_recovery", verify_recovery)
    workflow.add_node("final_feedback", lambda state: state)
    
    # 엣지 정의
    workflow.set_entry_point("collect_logs")
    workflow.add_edge("collect_logs", "classify_error")
    workflow.add_edge("classify_error", "analyze_root_cause")
    workflow.add_edge("analyze_root_cause", "get_user_feedback")
    workflow.add_conditional_edges(
        "get_user_feedback",
        should_continue,
        {
            "generate_action": "generate_action",
            "end": END
        }
    )
    workflow.add_edge("generate_action", "commit_changes")
    workflow.add_edge("commit_changes", "verify_recovery")
    workflow.add_edge("verify_recovery", "final_feedback")
    workflow.add_edge("final_feedback", END)
    
    return workflow.compile()
