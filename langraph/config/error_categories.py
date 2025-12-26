"""에러 카테고리 정의 및 매칭 로직"""
from typing import Optional

ERROR_CATEGORIES = {
    "oom": {
        "keywords": ["out of memory", "oomkilled", "memory limit", "memory pressure"],
        "severity": "critical",
        "description": "Out of Memory 에러"
    },
    "crashloop": {
        "keywords": ["crashloopbackoff", "back-off", "restarting", "exited with code"],
        "severity": "critical",
        "description": "CrashLoopBackOff 에러"
    },
    "config_error": {
        "keywords": ["config error", "configuration", "invalid config", "parse error"],
        "severity": "warning",
        "description": "설정 오류"
    },
    "resource_exhausted": {
        "keywords": ["resource quota", "cpu limit", "resource exhausted", "quota exceeded"],
        "severity": "warning",
        "description": "리소스 부족"
    },
    "network_error": {
        "keywords": ["connection refused", "timeout", "network error", "dns error"],
        "severity": "warning",
        "description": "네트워크 오류"
    },
    "image_pull_error": {
        "keywords": ["imagepullbackoff", "pull access denied", "image not found"],
        "severity": "critical",
        "description": "이미지 풀 오류"
    },
    "pod_scheduling_error": {
        "keywords": ["unschedulable", "no nodes available", "taint", "affinity"],
        "severity": "warning",
        "description": "Pod 스케줄링 오류"
    }
}


def categorize_error(log_text: str) -> tuple[Optional[str], Optional[str]]:
    """
    로그 텍스트를 분석하여 에러 카테고리와 심각도를 반환
    
    Args:
        log_text: 분석할 로그 텍스트
        
    Returns:
        (error_category, error_severity) 튜플
    """
    log_lower = log_text.lower()
    
    for category, info in ERROR_CATEGORIES.items():
        for keyword in info["keywords"]:
            if keyword in log_lower:
                return category, info["severity"]
    
    return None, None

