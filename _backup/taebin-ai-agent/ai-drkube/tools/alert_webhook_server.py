"""
Alertmanager Webhook Receiver 서버
Prometheus Alertmanager로부터 알림을 받아서 AI Agent를 실행하는 웹 서버입니다.
"""

import os
import json
import threading
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from loguru import logger
from dotenv import load_dotenv

from .log_analysis_agent import LogAnalysisAgent


class AlertWebhookServer:
    """Alertmanager Webhook Receiver 서버 클래스"""
    
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
        
        # 설정 로드
        self.config = config or self._load_config()
        
        # AI Agent 초기화
        self.agent = LogAnalysisAgent(config=self.config)
        
        # 라우트 등록
        self._register_routes()
        
        logger.info("AlertWebhookServer 초기화 완료")
    
    def _load_config(self) -> Dict[str, Any]:
        """환경 변수에서 설정 로드"""
        return {
            "google_api_key": os.getenv("GOOGLE_API_KEY"),
            "kubeconfig_path": os.getenv("KUBECONFIG_PATH"),
            "repo_path": os.getenv("REPO_PATH", "."),
            "simulate": os.getenv("SIMULATE", "true").lower() == "true",
            "model_name": os.getenv("MODEL_NAME", "gemini-2.5-flash"),
            "auto_approve": os.getenv("AUTO_APPROVE", "true").lower() == "true",
            "interactive_mode": "false",  # 웹훅에서는 상호작용 모드 비활성화
        }
    
    def _register_routes(self):
        """Flask 라우트 등록"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """헬스 체크 엔드포인트"""
            return jsonify({"status": "healthy"}), 200
        
        @self.app.route('/webhook', methods=['POST'])
        def webhook():
            """Alertmanager webhook 엔드포인트"""
            try:
                data = request.get_json()
                if not data:
                    logger.error("웹훅 요청에 JSON 데이터가 없습니다")
                    return jsonify({"error": "JSON 데이터가 필요합니다"}), 400
                
                logger.info(f"웹훅 알림 수신: {json.dumps(data, ensure_ascii=False, indent=2)}")
                
                # 알림 처리 (비동기로 실행)
                thread = threading.Thread(
                    target=self._process_alert,
                    args=(data,),
                    daemon=True
                )
                thread.start()
                
                # 즉시 응답 반환 (Alertmanager 타임아웃 방지)
                return jsonify({"status": "accepted"}), 200
                
            except Exception as e:
                logger.error(f"웹훅 처리 중 오류 발생: {e}")
                return jsonify({"error": str(e)}), 500
    
    def _process_alert(self, alert_data: Dict[str, Any]):
        """
        알림 데이터 처리 및 AI Agent 실행
        
        Args:
            alert_data: Alertmanager에서 받은 알림 데이터
        """
        try:
            # Alertmanager webhook 형식 파싱
            alerts = alert_data.get("alerts", [])
            
            if not alerts:
                logger.warning("알림 데이터에 alerts가 없습니다")
                return
            
            for alert in alerts:
                self._process_single_alert(alert)
                
        except Exception as e:
            logger.error(f"알림 처리 중 오류 발생: {e}", exc_info=True)
    
    def _process_single_alert(self, alert: Dict[str, Any]):
        """
        단일 알림 처리
        
        Args:
            alert: 단일 알림 데이터
        """
        try:
            # 알림 상태 확인 (firing만 처리)
            status = alert.get("status", "")
            if status != "firing":
                logger.info(f"알림 상태가 'firing'이 아니므로 무시: {status}")
                return
            
            # 라벨에서 파드 정보 추출
            labels = alert.get("labels", {})
            pod_name = labels.get("pod", "")
            namespace = labels.get("namespace", "default")
            container = labels.get("container", "")
            alertname = labels.get("alertname", "")
            
            if not pod_name:
                logger.warning("알림에 pod 라벨이 없습니다")
                return
            
            logger.info(f"알림 처리 시작: {alertname} - {namespace}/{pod_name}")
            
            # 추가 컨텍스트 정보 구성
            additional_context = {
                "alert_name": alertname,
                "namespace": namespace,
                "container": container,
                "alert_labels": labels,
                "annotations": alert.get("annotations", {}),
                "starts_at": alert.get("startsAt", ""),
            }
            
            # AI Agent 실행 (비동기로 실행하여 웹훅 응답 지연 방지)
            result = self.agent.run(
                log_source=pod_name,
                source_type="pod",
                additional_context=additional_context
            )
            
            logger.info(f"파드 분석 완료: {pod_name} - 상태: {result.get('status')}")
            
        except Exception as e:
            logger.error(f"단일 알림 처리 중 오류 발생: {e}", exc_info=True)
    
    def run(self, host: str = "0.0.0.0", port: int = 8080, debug: bool = False):
        """
        웹 서버 실행
        
        Args:
            host: 호스트 주소
            port: 포트 번호
            debug: 디버그 모드
        """
        logger.info(f"웹훅 서버 시작: http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug, threaded=True)


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Alertmanager Webhook Receiver 서버")
    parser.add_argument("--host", default="0.0.0.0", help="호스트 주소 (기본값: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="포트 번호 (기본값: 8080)")
    parser.add_argument("--debug", action="store_true", help="디버그 모드 활성화")
    
    args = parser.parse_args()
    
    # 서버 생성 및 실행
    server = AlertWebhookServer()
    server.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()

