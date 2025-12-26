from typing import TypedDict, List, Dict, Optional
from datetime import datetime


class IncidentState(TypedDict, total=False):
    """LangGraph State 정의 - 장애 대응 워크플로우의 모든 상태를 관리"""
    
    # 입력 데이터
    raw_log: str                    # 원본 로그
    log_source: str                 # 로그 소스 (loki, prometheus, file, etc.)
    timestamp: str                  # 로그 타임스탬프
    log_file_path: Optional[str]    # 로컬 파일 경로 (로컬 실행용)
    
    # 에러 분류
    error_category: Optional[str]   # 에러 카테고리 (oom, crashloop, config_error, etc.)
    error_severity: Optional[str]   # 심각도 (critical, warning, info)
    affected_apps: List[str]        # 영향받는 애플리케이션 목록
    
    # 원인 분석
    root_cause: Optional[str]       # 근본 원인 분석
    suggested_actions: List[str]    # 제안된 액션 목록
    
    # 사용자 피드백
    user_recognition: Optional[str] # 사용자 인식 (사용자 확인/수정)
    user_approved_action: Optional[str]  # 사용자 승인된 액션
    
    # Git 작업
    git_changes: Dict[str, str]     # Git 변경사항 (파일 경로: 변경 내용)
    commit_message: Optional[str]   # 커밋 메시지
    commit_hash: Optional[str]      # 커밋 해시
    
    # 복구 결과
    recovery_result: Optional[str]  # 복구 결과
    verification_status: Optional[str]  # 검증 상태 (success, failed, pending)
    
    # 메타데이터
    incident_id: str                # 인시던트 ID
    workflow_status: str            # 워크플로우 상태
    user_feedback_history: List[Dict]  # 사용자 피드백 이력
    created_at: str                 # 인시던트 생성 시간
    updated_at: str                 # 마지막 업데이트 시간

