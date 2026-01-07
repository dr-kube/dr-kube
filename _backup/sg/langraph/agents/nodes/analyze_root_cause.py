"""근본 원인 분석 노드 (Phase 1에서는 기본 구현만)"""
import sys
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.models.state import IncidentState
from langraph.utils.logger import get_logger

logger = get_logger(__name__)


def analyze_root_cause_node(state: IncidentState) -> Dict[str, Any]:
    """
    근본 원인을 분석하는 노드
    
    Phase 1: 기본 템플릿 기반 분석
    Phase 2: LLM 기반 고급 분석 추가 예정
    """
    logger.info("근본 원인 분석 시작")
    
    error_category = state.get("error_category")
    affected_apps = state.get("affected_apps", [])
    raw_log = state.get("raw_log", "")
    
    if not error_category:
        logger.warning("에러 카테고리가 없어 분석을 건너뜁니다")
        return {
            "root_cause": "에러 카테고리를 확인할 수 없습니다",
            "suggested_actions": ["로그를 더 자세히 확인하세요"],
            "workflow_status": "analysis_skipped",
        }
    
    # 기본 원인 분석 (카테고리 기반)
    root_cause, suggested_actions = _get_basic_analysis(error_category, affected_apps)
    
    logger.info(f"근본 원인 분석 완료: category={error_category}")
    
    return {
        "root_cause": root_cause,
        "suggested_actions": suggested_actions,
        "workflow_status": "root_cause_analyzed",
    }


def _get_basic_analysis(error_category: str, affected_apps: list[str]) -> tuple[str, list[str]]:
    """카테고리 기반 기본 분석"""
    apps_str = ", ".join(affected_apps) if affected_apps else "애플리케이션"
    
    analysis_map = {
        "oom": (
            f"{apps_str}에서 메모리 부족이 발생했습니다.",
            [
                f"{apps_str}의 메모리 리소스 제한을 증가시키세요 (values.yaml 수정)",
                "Pod의 메모리 요청량을 조정하세요",
            ]
        ),
        "crashloop": (
            f"{apps_str}가 반복적으로 재시작되고 있습니다.",
            [
                "애플리케이션 로그를 확인하여 크래시 원인을 파악하세요",
                "환경 변수나 설정 파일을 점검하세요",
                "이미지 버전을 확인하세요",
            ]
        ),
        "config_error": (
            f"{apps_str}의 설정에 오류가 있습니다.",
            [
                "Application.yaml 또는 values.yaml의 설정을 확인하세요",
                "YAML 문법 오류를 확인하세요",
            ]
        ),
        "resource_exhausted": (
            f"{apps_str}에 할당할 리소스가 부족합니다.",
            [
                "클러스터의 리소스 사용량을 확인하세요",
                "리소스 쿼터를 증가시키거나 불필요한 리소스를 정리하세요",
            ]
        ),
        "network_error": (
            f"{apps_str}에서 네트워크 연결 문제가 발생했습니다.",
            [
                "서비스 엔드포인트를 확인하세요",
                "네트워크 정책을 확인하세요",
                "DNS 설정을 확인하세요",
            ]
        ),
        "image_pull_error": (
            f"{apps_str}의 컨테이너 이미지를 가져올 수 없습니다.",
            [
                "이미지 레지스트리 접근 권한을 확인하세요",
                "이미지 태그가 올바른지 확인하세요",
                "네트워크 연결을 확인하세요",
            ]
        ),
        "pod_scheduling_error": (
            f"{apps_str}의 Pod를 스케줄링할 수 없습니다.",
            [
                "노드 리소스 가용성을 확인하세요",
                "Taint와 Toleration 설정을 확인하세요",
                "Affinity 규칙을 확인하세요",
            ]
        ),
    }
    
    return analysis_map.get(
        error_category,
        (
            f"{apps_str}에서 알 수 없는 에러가 발생했습니다.",
            ["로그를 자세히 확인하여 원인을 파악하세요"]
        )
    )

