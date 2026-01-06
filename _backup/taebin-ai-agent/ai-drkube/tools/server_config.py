"""
DR-Kube 서버 설정 모듈
환경 변수에서 설정을 로드합니다.
"""

import os
from typing import Dict, Any
from loguru import logger


def load_config() -> Dict[str, Any]:
    """
    환경 변수에서 설정 로드
    
    Returns:
        설정 딕셔너리
    """
    logger.debug("서버 설정 로드 시작")
    config = {
        "google_api_key": os.getenv("GOOGLE_API_KEY"),
        "kubeconfig_path": os.getenv("KUBECONFIG_PATH"),
        "repo_path": os.getenv("REPO_PATH", "."),
        "simulate": os.getenv("SIMULATE", "true").lower() == "true",
        "model_name": os.getenv("MODEL_NAME", "gemini-2.5-flash"),
        "auto_approve": os.getenv("AUTO_APPROVE", "true").lower() == "true",
        "interactive_mode": False,  # 웹서버에서는 상호작용 모드 비활성화
    }
    logger.debug(f"서버 설정 로드 완료: {list(config.keys())}")
    return config

