#!/usr/bin/env python
"""
DR-Kube 웹서버
HTTP API를 통해 로그 분석 요청을 받아 처리하는 통합 웹서버입니다.
"""

import sys
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from flask import Flask
from flask_cors import CORS
from loguru import logger
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.log_analysis_agent import LogAnalysisAgent
from tools.server_config import load_config
from tools.server_routes import register_routes
from tools.server_handlers import register_error_handlers


class DRKubeServer:
    """DR-Kube 웹서버 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        초기화
        
        Args:
            config: 설정 딕셔너리 (None이면 환경 변수에서 로드)
        """
        # 환경 변수 로드
        load_dotenv()
        
        # Flask 앱 생성
        self.app = Flask(__name__)
        self.app.config['JSON_AS_ASCII'] = False
        
        # CORS 설정
        CORS(self.app)
        
        # 설정 로드
        self.config = config or load_config()
        
        # AI Agent 초기화
        try:
            self.agent = LogAnalysisAgent(config=self.config)
            logger.info("LogAnalysisAgent 초기화 완료")
            logger.debug(f"Agent config: {self.config}")
        except Exception as e:
            logger.error(f"LogAnalysisAgent 초기화 실패: {e}")
            raise
        
        # 로그 버퍼 (Loki에서 받은 로그 저장)
        self.log_buffer: List[str] = []
        self.log_buffer_lock = threading.Lock()
        
        # 라우트 등록
        register_routes(self.app, self.agent, self.log_buffer, self.log_buffer_lock)
        
        # 에러 핸들러 등록
        register_error_handlers(self.app)
        
        logger.info("DR-Kube 서버 초기화 완료")
        logger.debug(f"Server config: {self.config}")
    
    def run(self, host: str = "0.0.0.0", port: int = 8080, debug: bool = False):
        """
        웹 서버 실행
        
        Args:
            host: 호스트 주소
            port: 포트 번호
            debug: 디버그 모드
        """
        logger.info(f"DR-Kube 서버 시작: http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug, threaded=True)


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="DR-Kube 웹서버")
    parser.add_argument("--host", default="0.0.0.0", help="호스트 주소 (기본값: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="포트 번호 (기본값: 8080)")
    parser.add_argument("--debug", action="store_true", help="디버그 모드 활성화")
    
    args = parser.parse_args()
    
    # 서버 생성 및 실행
    try:
        server = DRKubeServer()
        server.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as e:
        logger.error(f"서버 시작 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

