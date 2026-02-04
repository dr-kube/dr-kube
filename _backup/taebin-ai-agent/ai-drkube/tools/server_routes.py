"""
DR-Kube 서버 라우트 모듈
Flask 라우트 핸들러를 정의합니다.
"""

import os
import threading
from datetime import datetime
from typing import Dict, Any, List
from flask import Flask, request, jsonify
from loguru import logger
from tools.loki_proto import decode_loki_push_request


def register_routes(app: Flask, agent, log_buffer: List[str], log_buffer_lock: threading.Lock):
    """
    Flask 라우트 등록
    
    Args:
        app: Flask 앱 인스턴스
        agent: LogAnalysisAgent 인스턴스
        log_buffer: 로그 버퍼 리스트
        log_buffer_lock: 로그 버퍼 락
    """
    logger.debug("라우트 등록 시작")
    
    @app.route('/', methods=['GET'])
    def root():
        """루트 엔드포인트"""
        logger.debug("GET / 요청 수신")
        return jsonify({
            "service": "dr-kube",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "health": "/health",
                "analyze": "/api/v1/analyze"
            }
        }), 200
    
    @app.route('/health', methods=['GET'])
    def health():
        """헬스 체크 엔드포인트"""
        logger.debug("GET /health 요청 수신")
        return jsonify({
            "status": "healthy",
            "service": "dr-kube",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.0"
        }), 200
    
    @app.route('/api/v1/analyze', methods=['POST'])
    def analyze():
        """로그 분석 요청 엔드포인트"""
        logger.debug("POST /api/v1/analyze 요청 수신")
        try:
            # 요청 데이터 검증
            data = request.get_json()
            if not data:
                logger.warning("로그 분석 요청에 JSON 데이터가 없습니다")
                return jsonify({
                    "error": "JSON 데이터가 필요합니다",
                    "error_type": "ValidationError",
                    "status_code": 400
                }), 400
            
            logger.debug(f"로그 분석 요청 데이터: {data}")
            
            # 필수 필드 검증
            log_source = data.get("log_source")
            source_type = data.get("source_type")
            
            if not log_source:
                logger.warning("log_source 필드가 누락되었습니다")
                return jsonify({
                    "error": "log_source는 필수 필드입니다",
                    "error_type": "ValidationError",
                    "status_code": 400
                }), 400
            
            if not source_type:
                logger.warning("source_type 필드가 누락되었습니다")
                return jsonify({
                    "error": "source_type는 필수 필드입니다",
                    "error_type": "ValidationError",
                    "status_code": 400
                }), 400
            
            # source_type 유효성 검증
            valid_source_types = ["file", "directory", "pod", "label", "stdin"]
            if source_type not in valid_source_types:
                logger.warning(f"유효하지 않은 source_type: {source_type}")
                return jsonify({
                    "error": f"source_type는 다음 중 하나여야 합니다: {', '.join(valid_source_types)}",
                    "error_type": "ValidationError",
                    "status_code": 400
                }), 400
            
            # 요청 파라미터 추출
            namespace = data.get("namespace", "default")
            selected_categories = data.get("selected_categories")
            selected_resource_types = data.get("selected_resource_types", ["all"])
            additional_context = data.get("additional_context", {})
            
            # 추가 컨텍스트 구성
            if namespace:
                additional_context["namespace"] = namespace
            if selected_categories:
                additional_context["selected_categories"] = selected_categories
            if selected_resource_types:
                additional_context["selected_resource_types"] = selected_resource_types
            
            logger.info(f"로그 분석 요청 수신: source={log_source}, type={source_type}, namespace={namespace}")
            logger.debug(f"Agent 실행 파라미터: log_source={log_source}, source_type={source_type}, additional_context={additional_context}")
            
            # Agent 실행
            result = agent.run(
                log_source=log_source,
                source_type=source_type,
                additional_context=additional_context
            )
            
            logger.info(f"로그 분석 완료. 상태: {result.get('status')}")
            logger.debug(f"로그 분석 결과: {result}")
            
            # 결과 반환
            return jsonify({
                "status": "success",
                "result": {
                    "analyses": result.get("analyses", []),
                    "actions": result.get("actions", []),
                    "summary": result.get("summary", {}),
                    "steps": result.get("steps", {})
                }
            }), 200
            
        except ValueError as e:
            logger.error(f"요청 검증 오류: {e}")
            return jsonify({
                "error": str(e),
                "error_type": "ValidationError",
                "status_code": 400
            }), 400
        
        except Exception as e:
            logger.error(f"로그 분석 중 오류 발생: {e}", exc_info=True)
            return jsonify({
                "error": "로그 분석 중 오류가 발생했습니다",
                "error_type": "InternalError",
                "status_code": 500,
                "detail": str(e) if app.debug else None
            }), 500
    
    @app.route('/loki/api/v1/push', methods=['POST'])
    def loki_push():
        """Loki Push API 엔드포인트 - Grafana Alloy에서 로그를 받음"""
        logger.debug("POST /loki/api/v1/push 요청 수신")
        try:
            log_lines, metadata = decode_loki_push_request(request)
            logger.debug(f"Loki Push 수신 로그 수: {len(log_lines)}")
            
            if not log_lines:
                logger.info("Loki Push 요청에 로그가 없습니다")
                return jsonify({"status": "accepted", "message": "로그가 없습니다"}), 200
            
            logger.info(f"Loki에서 {len(log_lines)}줄의 로그를 수신했습니다 (라벨: {metadata})")
            
            # 로그 버퍼에 저장
            with log_buffer_lock:
                log_buffer.extend(log_lines)
                # 버퍼 크기 제한 (최대 10000줄)
                if len(log_buffer) > 10000:
                    log_buffer[:] = log_buffer[-10000:]
                logger.debug(f"로그 버퍼에 {len(log_lines)}줄 추가됨. 현재 버퍼 크기: {len(log_buffer)}")
            
            # 자동 분석 옵션 (환경 변수로 제어)
            auto_analyze = os.getenv("AUTO_ANALYZE_LOKI_LOGS", "false").lower() == "true"
            logger.debug(f"AUTO_ANALYZE_LOKI_LOGS 설정: {auto_analyze}")
            
            if auto_analyze:
                logger.info("Loki 로그 자동 분석 시작 (비동기)")
                # 비동기로 분석 실행
                from tools.loki_handler import analyze_loki_logs
                thread = threading.Thread(
                    target=analyze_loki_logs,
                    args=(agent, log_lines, metadata),
                    daemon=True
                )
                thread.start()
                logger.debug("Loki 로그 분석 스레드 시작됨")
            
            return jsonify({
                "status": "accepted",
                "received_logs": len(log_lines),
                "auto_analyze": auto_analyze
            }), 200
            
        except ValueError as e:
            logger.warning(f"Loki Push 요청 파싱 실패: {e}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"Loki Push API 처리 중 오류 발생: {e}", exc_info=True)
            return jsonify({
                "error": "로그 처리 중 오류가 발생했습니다",
                "detail": str(e) if app.debug else None
            }), 500
    
    @app.route('/api/v1/logs', methods=['GET'])
    def get_logs():
        """수집된 로그 조회 엔드포인트"""
        logger.debug("GET /api/v1/logs 요청 수신")
        try:
            limit = request.args.get('limit', type=int, default=100)
            logger.debug(f"로그 조회 요청 limit: {limit}")
            
            with log_buffer_lock:
                logs = log_buffer[-limit:] if limit > 0 else log_buffer
            logger.debug(f"버퍼에서 {len(logs)}줄의 로그 반환")
            
            return jsonify({
                "status": "success",
                "total_logs": len(log_buffer),
                "returned_logs": len(logs),
                "logs": logs
            }), 200
        except Exception as e:
            logger.error(f"로그 조회 중 오류 발생: {e}", exc_info=True)
            return jsonify({
                "error": "로그 조회 중 오류가 발생했습니다",
                "detail": str(e) if app.debug else None
            }), 500
    
    @app.route('/api/v1/logs/analyze', methods=['POST'])
    def analyze_buffered_logs():
        """버퍼에 저장된 로그 분석 엔드포인트"""
        logger.debug("POST /api/v1/logs/analyze 요청 수신")
        try:
            data = request.get_json() or {}
            limit = data.get("limit", 1000)  # 최대 분석할 로그 수
            logger.debug(f"버퍼 로그 분석 요청 limit: {limit}")
            
            with log_buffer_lock:
                if not log_buffer:
                    logger.info("분석할 버퍼링된 로그가 없습니다")
                    return jsonify({
                        "error": "분석할 로그가 없습니다",
                        "error_type": "NoLogsError",
                        "status_code": 400
                    }), 400
                
                # 최근 로그 추출
                logs_to_analyze = log_buffer[-limit:] if limit > 0 else log_buffer
            
            logger.info(f"버퍼링된 로그 {len(logs_to_analyze)}줄 분석 시작")
            
            # 리스트를 직접 전달하여 분석 (임시 파일 생성 없음)
            result = agent.run(
                log_source=logs_to_analyze,
                source_type="stdin",  # 리스트는 stdin 타입으로 처리
                additional_context={
                    "source": "loki_buffer",
                    "log_count": len(logs_to_analyze)
                }
            )
            
            logger.info(f"버퍼링된 로그 분석 완료. 상태: {result.get('status')}")
            logger.debug(f"버퍼링된 로그 분석 결과: {result}")
            
            return jsonify({
                "status": "success",
                "result": {
                    "analyses": result.get("analyses", []),
                    "actions": result.get("actions", []),
                    "summary": result.get("summary", {}),
                    "steps": result.get("steps", {})
                }
            }), 200
            
        except Exception as e:
            logger.error(f"버퍼링된 로그 분석 중 오류 발생: {e}", exc_info=True)
            return jsonify({
                "error": "로그 분석 중 오류가 발생했습니다",
                "error_type": "InternalError",
                "status_code": 500,
                "detail": str(e) if app.debug else None
            }), 500
    
    logger.debug("라우트 등록 완료")

