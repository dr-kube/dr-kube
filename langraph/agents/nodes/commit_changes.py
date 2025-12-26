"""Git 커밋 노드 (Phase 1에서는 기본 구현만)"""
import sys
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.models.state import IncidentState
from langraph.utils.logger import get_logger

logger = get_logger(__name__)


def commit_changes_node(state: IncidentState) -> Dict[str, Any]:
    """
    Git 변경사항을 커밋하는 노드
    
    Phase 1: 기본 구조만 구현 (실제 커밋은 하지 않음)
    Phase 2: GitPython을 사용한 실제 커밋 로직 추가
    """
    logger.info("Git 커밋 시작")
    
    git_changes = state.get("git_changes", {})
    commit_message = state.get("commit_message", "")
    
    if not git_changes:
        logger.warning("커밋할 변경사항이 없습니다")
        return {
            "commit_hash": None,
            "workflow_status": "commit_skipped",
        }
    
    # Phase 1: 시뮬레이션만 수행
    logger.info(f"커밋 메시지: {commit_message}")
    logger.info(f"변경된 파일 수: {len(git_changes)}")
    
    # Phase 2: 실제 Git 커밋 수행
    # commit_hash = _perform_git_commit(git_changes, commit_message)
    
    commit_hash = "simulated-commit-hash-phase1"
    
    logger.info(f"커밋 완료 (시뮬레이션): {commit_hash}")
    
    return {
        "commit_hash": commit_hash,
        "workflow_status": "changes_committed",
    }

