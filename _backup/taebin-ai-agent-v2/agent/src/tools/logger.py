"""로깅 유틸리티"""
import os
import logging
import sys
from typing import Optional

# 로깅 레벨 설정
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    로거 인스턴스 생성
    
    Args:
        name: 로거 이름 (보통 __name__)
        level: 로깅 레벨 (없으면 환경 변수에서 로드)
        
    Returns:
        로거 인스턴스
    """
    logger = logging.getLogger(name)
    
    # 레벨 설정
    log_level = level or LOG_LEVEL
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # 핸들러가 이미 있으면 추가하지 않음
    if logger.handlers:
        return logger
    
    # 콘솔 핸들러
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level, logging.INFO))
    
    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger
