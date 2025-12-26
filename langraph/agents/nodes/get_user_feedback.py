"""사용자 피드백 노드 (Phase 1에서는 기본 구현만)"""
import sys
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.models.state import IncidentState
from langraph.utils.logger import get_logger

logger = get_logger(__name__)


def get_user_feedback_node(state: IncidentState) -> Dict[str, Any]:
    """
    사용자로부터 피드백을 받는 노드
    
    Phase 1: CLI 기반 간단한 입력
    Phase 2: 대화형 인터페이스로 개선 예정
    """
    logger.info("사용자 피드백 수집 시작")
    
    root_cause = state.get("root_cause", "")
    suggested_actions = state.get("suggested_actions", [])
    
    # Phase 1: 자동 승인 (개발 중)
    # Phase 2: 실제 사용자 입력 받기
    
    logger.info("=== 인시던트 분석 결과 ===")
    logger.info(f"근본 원인: {root_cause}")
    logger.info("제안된 액션:")
    for i, action in enumerate(suggested_actions, 1):
        logger.info(f"  {i}. {action}")
    
    # Phase 1에서는 첫 번째 제안된 액션을 자동으로 승인
    approved_action = suggested_actions[0] if suggested_actions else "수동 확인 필요"
    user_recognition = f"자동 승인됨 (Phase 1): {root_cause}"
    
    logger.info(f"승인된 액션: {approved_action}")
    
    return {
        "user_recognition": user_recognition,
        "user_approved_action": approved_action,
        "workflow_status": "user_feedback_received",
        "user_feedback_history": state.get("user_feedback_history", []) + [{
            "type": "recognition",
            "content": user_recognition,
            "approved_action": approved_action,
        }],
    }

