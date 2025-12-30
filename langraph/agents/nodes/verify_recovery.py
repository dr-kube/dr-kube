"""복구 결과 검증 노드 (Phase 1에서는 기본 구현만)"""
import sys
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.models.state import IncidentState
from langraph.utils.logger import get_logger

logger = get_logger(__name__)


def verify_recovery_node(state: IncidentState) -> Dict[str, Any]:
    """
    복구 결과를 검증하는 노드
    
    Phase 1: 기본 구조만 구현
    Phase 2: Kubernetes/ArgoCD API를 통한 실제 검증 추가
    """
    logger.info("복구 결과 검증 시작")
    
    commit_hash = state.get("commit_hash")
    affected_apps = state.get("affected_apps", [])
    
    if not commit_hash:
        logger.warning("커밋 해시가 없어 검증을 건너뜁니다")
        return {
            "recovery_result": "검증 불가: 커밋이 없습니다",
            "verification_status": "failed",
            "workflow_status": "verification_skipped",
        }
    
    # Phase 1: 시뮬레이션만 수행
    logger.info(f"커밋 {commit_hash}의 복구 결과 확인 중...")
    
    # Phase 2: 실제 검증 로직
    # - ArgoCD Application 상태 확인
    # - Pod 상태 확인
    # - 로그 재조회
    
    recovery_result = f"복구 액션이 실행되었습니다 (Phase 1 시뮬레이션)"
    verification_status = "pending"  # Phase 1에서는 항상 pending
    
    logger.info(f"검증 완료: {verification_status}")
    
    return {
        "recovery_result": recovery_result,
        "verification_status": verification_status,
        "workflow_status": "recovery_verified",
    }

