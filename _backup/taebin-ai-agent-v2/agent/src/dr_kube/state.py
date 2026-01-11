"""상태 모델 정의"""
from typing import TypedDict, List, Optional, Dict, Any


class AgentState(TypedDict):
    """LangGraph 워크플로우 상태"""
    
    # 로그 관련
    logs: List[str]  # 수집된 로그
    log_source: str  # 로그 출처 (loki, alloy, file)
    
    # 에러 분류
    error_category: Optional[str]  # 에러 카테고리 (oom, crashloop, config_error 등)
    error_type: Optional[str]  # 구체적인 에러 타입
    
    # 분석 결과
    root_cause: Optional[str]  # 근본 원인 분석 결과
    severity: Optional[str]  # 심각도 (critical, high, medium, low)
    analysis: Optional[str]  # LLM 분석 결과 전체
    
    # 액션 및 복구
    suggested_actions: List[Dict[str, Any]]  # 제안된 복구 액션
    git_changes: Optional[Dict[str, Any]]  # Git 변경사항
    recovery_status: Optional[str]  # 복구 상태 (pending, success, failed)
    
    # 사용자 피드백
    user_feedback: Optional[str]  # 사용자 피드백
    user_approved: bool  # 사용자 승인 여부
    
    # 메타데이터
    namespace: Optional[str]  # Kubernetes 네임스페이스
    resource_name: Optional[str]  # 리소스 이름
    resource_type: Optional[str]  # 리소스 타입 (Pod, Deployment 등)
    
    # 에러 처리
    error: Optional[str]  # 에러 메시지
    status: str  # 현재 상태 (pending, processing, completed, error)
