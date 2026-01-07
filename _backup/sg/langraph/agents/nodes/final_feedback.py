"""최종 피드백 노드"""
import sys
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.models.state import IncidentState
from langraph.utils.logger import get_logger

logger = get_logger(__name__)


def final_feedback_node(state: IncidentState) -> Dict[str, Any]:
    """
    사용자에게 최종 결과를 보고하는 노드
    """
    logger.info("최종 피드백 생성")
    
    incident_id = state.get("incident_id", "unknown")
    error_category = state.get("error_category", "unknown")
    recovery_result = state.get("recovery_result", "")
    verification_status = state.get("verification_status", "unknown")
    commit_hash = state.get("commit_hash", "")
    
    logger.info("=" * 60)
    logger.info("=== 인시던트 처리 완료 ===")
    logger.info(f"인시던트 ID: {incident_id}")
    logger.info(f"에러 카테고리: {error_category}")
    logger.info(f"복구 결과: {recovery_result}")
    logger.info(f"검증 상태: {verification_status}")
    if commit_hash:
        logger.info(f"커밋 해시: {commit_hash}")
    logger.info("=" * 60)
    
    return {
        "workflow_status": "completed",
    }

