"""
Loki 로그 처리 모듈
Loki에서 받은 로그를 분석하는 기능을 제공합니다.
"""

from typing import Dict, Any, List
from loguru import logger


def analyze_loki_logs(agent, log_lines: List[str], metadata: Dict[str, Any]):
    """
    Loki에서 받은 로그를 자동 분석
    
    Args:
        agent: LogAnalysisAgent 인스턴스
        log_lines: 로그 라인 리스트
        metadata: 로그 메타데이터 (라벨 등)
    """
    logger.debug(f"비동기 Loki 로그 분석 시작: {len(log_lines)}줄, 메타데이터: {metadata}")
    try:
        logger.info(f"Loki 로그 자동 분석 시작: {len(log_lines)}줄")
        
        # 리스트를 직접 전달하여 분석 (임시 파일 생성 없음)
        result = agent.run(
            log_source=log_lines,
            source_type="stdin",  # 리스트는 stdin 타입으로 처리
            additional_context={
                "source": "loki_auto",
                "metadata": metadata,
                "log_count": len(log_lines)
            }
        )
        
        logger.info(f"Loki 로그 자동 분석 완료: 상태={result.get('status')}")
        logger.debug(f"비동기 Loki 로그 분석 결과: {result}")
    except Exception as e:
        logger.error(f"비동기 Loki 로그 분석 중 오류 발생: {e}", exc_info=True)

