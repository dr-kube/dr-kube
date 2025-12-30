"""로그 수집 노드"""
import os
from datetime import datetime
from typing import Dict, Any

import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.models.state import IncidentState
from langraph.utils.logger import get_logger

logger = get_logger(__name__)


def collect_logs_node(state: IncidentState) -> Dict[str, Any]:
    """
    로그를 수집하는 노드
    
    현재는 로컬 파일에서 로그를 읽는 기능만 구현
    향후 Loki, Prometheus 연동 추가 예정
    """
    logger.info("로그 수집 시작")
    
    # 로컬 파일에서 로그 읽기
    if state.get("log_file_path"):
        file_path = state["log_file_path"]
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                raw_log = f.read()
            logger.info(f"파일에서 로그 읽기 완료: {file_path}")
        else:
            logger.error(f"파일을 찾을 수 없습니다: {file_path}")
            raw_log = ""
    else:
        # 기본값: state에 이미 raw_log가 있으면 그대로 사용
        raw_log = state.get("raw_log", "")
        if not raw_log:
            logger.warning("로그 파일 경로가 제공되지 않았고 raw_log도 없습니다")
    
    # 타임스탬프 생성
    timestamp = datetime.now().isoformat()
    
    # 인시던트 ID 생성 (타임스탬프 기반)
    incident_id = f"incident-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "raw_log": raw_log,
        "log_source": state.get("log_source", "file"),
        "timestamp": timestamp,
        "incident_id": incident_id,
        "workflow_status": "logs_collected",
        "created_at": timestamp,
        "updated_at": timestamp,
    }

