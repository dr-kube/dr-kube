"""액션 생성 노드 (Phase 1에서는 기본 구현만)"""
import sys
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.models.state import IncidentState
from langraph.utils.logger import get_logger

logger = get_logger(__name__)


def generate_action_node(state: IncidentState) -> Dict[str, Any]:
    """
    승인된 액션에 따라 Git 변경사항을 생성하는 노드
    
    Phase 1: 기본 구조만 구현
    Phase 2: 실제 Application.yaml, values.yaml 수정 로직 추가
    """
    logger.info("액션 생성 시작")
    
    approved_action = state.get("user_approved_action", "")
    affected_apps = state.get("affected_apps", [])
    error_category = state.get("error_category", "")
    
    # Phase 1: 기본 커밋 메시지만 생성
    commit_message = f"fix: {error_category} 에러 복구 - {approved_action}"
    
    # Phase 2: 실제 파일 변경사항 생성
    git_changes = {}
    
    logger.info(f"커밋 메시지 생성: {commit_message}")
    
    return {
        "git_changes": git_changes,
        "commit_message": commit_message,
        "workflow_status": "action_generated",
    }

