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
    repo_root = state.get("repo_root", ".")
    
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
    
    # 영향받는 애플리케이션 추출 (App of Apps 구조 활용)
    affected_apps = _extract_affected_apps(raw_log, repo_root)
    
    logger.info(f"에러 분류 완료: category={error_category}, severity={error_severity}, apps={affected_apps}")
    
    return {
        "error_category": error_category,
        "error_severity": error_severity,
        "affected_apps": affected_apps,
        "workflow_status": "error_classified",
    }


def _extract_affected_apps(log_text: str, repo_root: str = ".") -> list[str]:
    """
    로그에서 영향받는 애플리케이션 이름 추출
    
    App of Apps 구조를 활용하여 정확한 앱 이름 찾기
    """
    import re
    
    # App of Apps 구조 분석
    try:
        from langraph.services.app_of_apps_analyzer import AppOfAppsAnalyzer
        analyzer = AppOfAppsAnalyzer(repo_root=repo_root)
        analyzer.analyze()
    except Exception as e:
        logger.warning(f"App of Apps 분석 실패, 기본 휴리스틱 사용: {e}")
        analyzer = None
    
    # Pod 이름 패턴 찾기 (예: pod/grafana-7d8f9c4b5-xk2m3)
    pod_pattern = r'pod[\/\s]+([a-z0-9-]+(?:-[a-z0-9]+)*)'
    pod_matches = re.findall(pod_pattern, log_text.lower())
    
    apps = set()
    
    # Pod 이름에서 앱 이름 추출
    for pod_name in pod_matches:
        if analyzer:
            # App of Apps 구조를 활용하여 정확한 앱 이름 찾기
            app_name = analyzer.find_app_by_pod_name(pod_name)
            if app_name:
                apps.add(app_name)
            else:
                # 실패 시 기본 휴리스틱 사용
                parts = pod_name.split('-')
                if len(parts) > 0:
                    apps.add(parts[0])
        else:
            # 기본 휴리스틱
            parts = pod_name.split('-')
            if len(parts) > 0:
                apps.add(parts[0])
    
    # 다른 패턴들도 시도
    app_patterns = [
        r'application[\/\s]+([a-z0-9-]+)',
        r'app[\/\s]+([a-z0-9-]+)',
        r'deployment[\/\s]+([a-z0-9-]+)',
    ]
    
    for pattern in app_patterns:
        matches = re.findall(pattern, log_text.lower())
        for match in matches:
            if analyzer and match in analyzer.apps_map:
                apps.add(match)
            else:
                apps.add(match)
    
    return list(apps)[:5]  # 최대 5개만 반환

