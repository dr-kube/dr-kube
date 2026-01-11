"""Loki 클라이언트"""
import os
from typing import List, Optional, Dict, Any
import httpx
from datetime import datetime, timedelta

from src.tools.logger import get_logger

logger = get_logger(__name__)


class LokiClient:
    """Loki API 클라이언트"""
    
    def __init__(self, loki_url: Optional[str] = None):
        """
        Loki 클라이언트 초기화
        
        Args:
            loki_url: Loki 서버 URL (없으면 환경 변수에서 로드)
        """
        self.loki_url = loki_url or os.getenv("LOKI_URL", "http://localhost:3100")
        if not self.loki_url.endswith("/"):
            self.loki_url += "/"
        logger.info(f"Loki 클라이언트 초기화: {self.loki_url}")
    
    def query_logs(
        self,
        query: str,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[str]:
        """
        Loki에서 로그 쿼리
        
        Args:
            query: LogQL 쿼리
            limit: 반환할 로그 수
            start_time: 시작 시간
            end_time: 종료 시간
            
        Returns:
            로그 리스트
        """
        try:
            if not start_time:
                start_time = datetime.now() - timedelta(hours=1)
            if not end_time:
                end_time = datetime.now()
            
            # 나노초 타임스탬프로 변환
            start_ns = int(start_time.timestamp() * 1e9)
            end_ns = int(end_time.timestamp() * 1e9)
            
            url = f"{self.loki_url}loki/api/v1/query_range"
            params = {
                "query": query,
                "limit": limit,
                "start": start_ns,
                "end": end_ns
            }
            
            logger.info(f"Loki 쿼리 실행: {query}")
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # 로그 추출
            logs = []
            if "data" in data and "result" in data["data"]:
                for stream in data["data"]["result"]:
                    if "values" in stream:
                        for timestamp, log_line in stream["values"]:
                            logs.append(log_line)
            
            logger.info(f"Loki에서 {len(logs)}개 로그 수집")
            return logs
            
        except Exception as e:
            logger.error(f"Loki 쿼리 실패: {str(e)}")
            raise
    
    def query_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        container: Optional[str] = None,
        limit: int = 100
    ) -> List[str]:
        """
        특정 Pod의 로그 조회
        
        Args:
            namespace: 네임스페이스
            pod_name: Pod 이름
            container: 컨테이너 이름 (선택사항)
            limit: 반환할 로그 수
            
        Returns:
            로그 리스트
        """
        query = f'{{namespace="{namespace}", pod="{pod_name}"}}'
        if container:
            query = f'{{namespace="{namespace}", pod="{pod_name}", container="{container}"}}'
        
        return self.query_logs(query, limit=limit)
