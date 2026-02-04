"""
에러 분류 모듈
키워드 기반으로 에러를 카테고리별로 분류합니다.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from loguru import logger
import re


@dataclass
class ErrorCategory:
    """에러 카테고리 정보"""
    name: str
    keywords: List[str]
    severity: str  # critical, high, medium, low
    description: str


class ErrorClassifier:
    """에러 분류 클래스"""
    
    # 에러 카테고리 정의
    ERROR_CATEGORIES = [
        ErrorCategory(
            name="네트워크 오류",
            keywords=["connection refused", "connection timeout", "network unreachable", 
                     "no route to host", "network error", "dns", "resolve", "timeout"],
            severity="high",
            description="네트워크 연결 관련 오류"
        ),
        ErrorCategory(
            name="인증/인가 오류",
            keywords=["unauthorized", "forbidden", "authentication failed", "access denied",
                     "permission denied", "401", "403", "token expired", "invalid token"],
            severity="high",
            description="인증 및 권한 관련 오류"
        ),
        ErrorCategory(
            name="리소스 부족",
            keywords=["out of memory", "oom", "memory limit", "cpu throttling",
                     "resource quota", "limit exceeded", "insufficient resources"],
            severity="critical",
            description="시스템 리소스 부족 오류"
        ),
        ErrorCategory(
            name="파일 시스템 오류",
            keywords=["no such file", "file not found", "permission denied", "read-only",
                     "disk full", "no space left", "i/o error", "eof"],
            severity="medium",
            description="파일 시스템 관련 오류"
        ),
        ErrorCategory(
            name="데이터베이스 오류",
            keywords=["database error", "sql error", "connection pool", "deadlock",
                     "transaction", "constraint violation", "foreign key"],
            severity="high",
            description="데이터베이스 관련 오류"
        ),
        ErrorCategory(
            name="애플리케이션 오류",
            keywords=["exception", "error", "failed", "panic", "fatal", "crash",
                     "null pointer", "index out of range", "stack overflow"],
            severity="medium",
            description="애플리케이션 런타임 오류"
        ),
        ErrorCategory(
            name="컨테이너/Kubernetes 오류",
            keywords=["container", "pod", "kubelet", "cni", "cgroup", "namespace",
                     "image pull", "crashloopbackoff", "evicted", "pending"],
            severity="high",
            description="컨테이너 및 Kubernetes 관련 오류"
        ),
        ErrorCategory(
            name="서비스 의존성 오류",
            keywords=["service unavailable", "503", "502", "504", "bad gateway",
                     "service not found", "endpoint", "health check failed"],
            severity="high",
            description="외부 서비스 의존성 오류"
        ),
        ErrorCategory(
            name="설정 오류",
            keywords=["config error", "invalid configuration", "missing config",
                     "parse error", "yaml", "json", "syntax error"],
            severity="medium",
            description="설정 파일 및 파라미터 오류"
        ),
        ErrorCategory(
            name="기타 오류",
            keywords=[],
            severity="low",
            description="분류되지 않은 기타 오류"
        ),
    ]
    
    def __init__(self):
        """초기화"""
        # 키워드를 소문자로 변환하여 저장 (대소문자 무시 검색)
        self.category_keywords = {}
        for category in self.ERROR_CATEGORIES:
            self.category_keywords[category.name] = [
                keyword.lower() for keyword in category.keywords
            ]
    
    def classify_error(self, log_line: str) -> Optional[ErrorCategory]:
        """
        단일 로그 라인을 에러 카테고리로 분류
        
        Args:
            log_line: 로그 라인
            
        Returns:
            매칭된 ErrorCategory 또는 None
        """
        log_lower = log_line.lower()
        
        # 각 카테고리에 대해 키워드 매칭
        for category in self.ERROR_CATEGORIES:
            if category.name == "기타 오류":
                continue  # 기타 오류는 마지막에 처리
            
            for keyword in self.category_keywords[category.name]:
                if keyword in log_lower:
                    logger.debug(f"에러 분류: '{category.name}' (키워드: {keyword})")
                    return category
        
        # 매칭되지 않으면 기타 오류
        return self.ERROR_CATEGORIES[-1]  # "기타 오류"
    
    def classify_logs(self, logs: List[str]) -> Dict[str, List[str]]:
        """
        여러 로그를 카테고리별로 분류
        
        Args:
            logs: 로그 라인 리스트
            
        Returns:
            카테고리 이름을 키로 하는 로그 딕셔너리
        """
        logger.debug(f"로그 분류 시작: 총 {len(logs)}줄")
        classified = {category.name: [] for category in self.ERROR_CATEGORIES}
        
        for idx, log_line in enumerate(logs):
            if idx < 5 or (idx % 100 == 0 and idx > 0):  # 처음 5개와 100개마다
                logger.debug(f"로그 라인 {idx+1}/{len(logs)} 분류 중: {log_line[:80]}...")
            category = self.classify_error(log_line)
            if category:
                classified[category.name].append(log_line)
        
        # 빈 카테고리 제거
        classified = {k: v for k, v in classified.items() if v}
        
        category_counts = {k: len(v) for k, v in classified.items()}
        logger.debug(f"로그 분류 완료: {len(classified)}개 카테고리, 카테고리별 로그 수: {category_counts}")
        logger.info(f"로그 분류 완료: {len(classified)}개 카테고리, 총 {len(logs)}줄")
        return classified
    
    def get_error_summary(self, classified_logs: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        분류된 로그의 요약 정보 생성
        
        Args:
            classified_logs: 분류된 로그 딕셔너리
            
        Returns:
            요약 정보 딕셔너리
        """
        summary = {
            "total_errors": sum(len(logs) for logs in classified_logs.values()),
            "categories": {},
            "severity_counts": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }
        
        for category_name, logs in classified_logs.items():
            category = next(
                (c for c in self.ERROR_CATEGORIES if c.name == category_name),
                None
            )
            if category:
                summary["categories"][category_name] = {
                    "count": len(logs),
                    "severity": category.severity,
                    "description": category.description
                }
                summary["severity_counts"][category.severity] += len(logs)
        
        return summary

