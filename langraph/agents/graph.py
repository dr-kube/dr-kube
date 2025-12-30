"""LangGraph 메인 그래프 정의"""
from langgraph.graph import StateGraph, END

import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.models.state import IncidentState
from langraph.agents.nodes import (
    collect_logs_node,
    classify_error_node,
    analyze_root_cause_node,
    get_user_feedback_node,
    generate_action_node,
    commit_changes_node,
    verify_recovery_node,
    final_feedback_node,
)
from langraph.utils.logger import get_logger

logger = get_logger(__name__)


def create_incident_response_graph() -> StateGraph:
    """
    장애 대응 워크플로우 그래프 생성
    
    워크플로우:
    1. 로그 수집
    2. 에러 분류
    3. 근본 원인 분석
    4. 사용자 피드백
    5. 액션 생성
    6. Git 커밋
    7. 복구 검증
    8. 최종 피드백
    """
    workflow = StateGraph(IncidentState)
    
    # 노드 추가
    workflow.add_node("collect_logs", collect_logs_node)
    workflow.add_node("classify_error", classify_error_node)
    workflow.add_node("analyze_root_cause", analyze_root_cause_node)
    workflow.add_node("get_user_feedback", get_user_feedback_node)
    workflow.add_node("generate_action", generate_action_node)
    workflow.add_node("commit_changes", commit_changes_node)
    workflow.add_node("verify_recovery", verify_recovery_node)
    workflow.add_node("final_feedback", final_feedback_node)
    
    # 엣지 정의 (순차 실행)
    workflow.set_entry_point("collect_logs")
    workflow.add_edge("collect_logs", "classify_error")
    workflow.add_edge("classify_error", "analyze_root_cause")
    workflow.add_edge("analyze_root_cause", "get_user_feedback")
    workflow.add_edge("get_user_feedback", "generate_action")
    workflow.add_edge("generate_action", "commit_changes")
    workflow.add_edge("commit_changes", "verify_recovery")
    workflow.add_edge("verify_recovery", "final_feedback")
    workflow.add_edge("final_feedback", END)
    
    return workflow.compile()

