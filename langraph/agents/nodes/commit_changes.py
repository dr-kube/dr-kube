"""Git 커밋 노드"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.models.state import IncidentState
from langraph.utils.logger import get_logger
from langraph.services.git_client import GitClient

logger = get_logger(__name__)


def commit_changes_node(state: IncidentState) -> Dict[str, Any]:
    """
    Git 변경사항을 커밋하는 노드
    
    실제 Git 커밋 수행 (dry-run 모드 지원)
    """
    logger.info("Git 커밋 시작")
    
    modified_files = state.get("modified_files", [])
    commit_message = state.get("commit_message", "")
    dry_run = state.get("dry_run", False)
    repo_root = state.get("repo_root", ".")
    
    if not modified_files:
        logger.warning("커밋할 변경사항이 없습니다")
        return {
            "commit_hash": None,
            "workflow_status": "commit_skipped",
        }
    
    git_client = GitClient(repo_path=repo_root)
    
    # 변경사항 확인
    status = git_client.status()
    logger.info(f"변경된 파일: {status['modified']}")
    
    # 파일 추가
    if not git_client.add(modified_files, dry_run=dry_run):
        logger.error("파일 추가 실패")
        return {
            "commit_hash": None,
            "workflow_status": "commit_failed",
        }
    
    # 커밋
    commit_hash = git_client.commit(commit_message, dry_run=dry_run)
    
    if commit_hash:
        logger.info(f"커밋 완료: {commit_hash}")
        return {
            "commit_hash": commit_hash,
            "workflow_status": "changes_committed",
        }
    else:
        logger.error("커밋 실패")
        return {
            "commit_hash": None,
            "workflow_status": "commit_failed",
        }

