"""
DR-Kube 서버 에러 핸들러 모듈
Flask 에러 핸들러를 정의합니다.
"""

from flask import Flask, request, jsonify
from loguru import logger


def register_error_handlers(app: Flask):
    """
    에러 핸들러 등록
    
    Args:
        app: Flask 앱 인스턴스
    """
    logger.debug("에러 핸들러 등록 시작")
    
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"404 Not Found: {request.path}")
        return jsonify({
            "error": "엔드포인트를 찾을 수 없습니다",
            "error_type": "NotFound",
            "status_code": 404
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        logger.warning(f"405 Method Not Allowed: {request.method} {request.path}")
        return jsonify({
            "error": "허용되지 않은 HTTP 메서드입니다",
            "error_type": "MethodNotAllowed",
            "status_code": 405
        }), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 Internal Server Error: {error}", exc_info=True)
        return jsonify({
            "error": "서버 내부 오류가 발생했습니다",
            "error_type": "InternalError",
            "status_code": 500,
            "detail": str(error) if app.debug else None
        }), 500
    
    logger.debug("에러 핸들러 등록 완료")

