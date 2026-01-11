"""로그 수집 노드"""
from typing import Optional
from src.dr_kube.state import AgentState
from src.dr_kube.services.loki_client import LokiClient
from src.tools.logger import get_logger

logger = get_logger(__name__)


def collect_logs(state: AgentState) -> AgentState:
    """
    로그를 수집하는 노드
    
    로그 출처:
    - Loki API
    - Alloy Webhook
    - 로컬 파일
    
    Args:
        state: 현재 상태
        
    Returns:
        로그가 추가된 상태
    """
    try:
        logger.info("로그 수집 시작")
        
        # Phase 1: 기본 구현 - 로컬 파일 또는 Loki에서 로그 수집
        logs = state.get("logs", [])
        log_source = state.get("log_source", "file")
        
        if not logs and log_source == "loki":
            # Loki에서 로그 수집
            loki_url = state.get("loki_url")
            if loki_url:
                loki_client = LokiClient(loki_url)
                # TODO: Loki 쿼리 구현
                logger.info("Loki에서 로그 수집 (구현 예정)")
        
        logger.info(f"로그 수집 완료: {len(logs)}개 로그")
        
        return {
            **state,
            "logs": logs,
            "log_source": log_source,
            "status": "processing"
        }
    except Exception as e:
        logger.error(f"로그 수집 실패: {str(e)}")
        return {
            **state,
            "error": f"로그 수집 실패: {str(e)}",
            "status": "error"
        }
