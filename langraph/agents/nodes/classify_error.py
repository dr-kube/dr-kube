"""에러 분류 노드 (Phase 1에서는 기본 구현만)"""
import sys
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.models.state import IncidentState
from langraph.config.error_categories import categorize_error
from langraph.utils.logger import get_logger

logger = get_logger(__name__)


def classify_error_node(state: IncidentState) -> Dict[str, Any]:
    """
    에러를 분류하는 노드
    
    Phase 1: 키워드 기반 분류만 구현
    Phase 2: LLM 기반 고급 분류 추가 예정
    """
    logger.info("에러 분류 시작")
    
    raw_log = state.get("raw_log", "")
    if not raw_log:
        logger.warning("분류할 로그가 없습니다")
        return {
            "error_category": None,
            "error_severity": None,
            "affected_apps": [],
            "workflow_status": "classification_failed",
        }
    
    # 키워드 기반 분류
    error_category, error_severity = categorize_error(raw_log)
    
    # 영향받는 애플리케이션 추출 (간단한 휴리스틱)
    affected_apps = _extract_affected_apps(raw_log)
    
    logger.info(f"에러 분류 완료: category={error_category}, severity={error_severity}")
    
    return {
        "error_category": error_category,
        "error_severity": error_severity,
        "affected_apps": affected_apps,
        "workflow_status": "error_classified",
    }


def _extract_affected_apps(log_text: str) -> list[str]:
    """
    로그에서 영향받는 애플리케이션 이름 추출
    
    Phase 1: 간단한 휴리스틱 사용
    Phase 2: LLM 기반 추출로 개선 예정
    """
    # 일반적인 Kubernetes 리소스 이름 패턴 찾기
    import re
    
    # Pod 이름 패턴 (예: app-name-xxx-xxx)
    pod_pattern = r'pod[\/\s]+([a-z0-9-]+(?:-[a-z0-9]+)*)'
    matches = re.findall(pod_pattern, log_text.lower())
    
    # 네임스페이스나 애플리케이션 이름 패턴
    app_patterns = [
        r'application[\/\s]+([a-z0-9-]+)',
        r'app[\/\s]+([a-z0-9-]+)',
        r'deployment[\/\s]+([a-z0-9-]+)',
    ]
    
    apps = set()
    for pattern in app_patterns:
        apps.update(re.findall(pattern, log_text.lower()))
    
    # Pod 이름에서 애플리케이션 이름 추출 (예: grafana-xxx -> grafana)
    for match in matches:
        parts = match.split('-')
        if len(parts) > 0:
            apps.add(parts[0])
    
    return list(apps)[:5]  # 최대 5개만 반환

