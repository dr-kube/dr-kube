"""
LangGraph State 정의
에이전트 워크플로우 전체에서 공유되는 상태
"""
from typing import TypedDict, Optional, Literal
from dataclasses import dataclass, field


class IssueInfo(TypedDict):
    """감지된 이슈 정보"""
    type: str  # oomkilled, crashloop, imagepull, pending
    pod_name: str
    namespace: str
    container_name: Optional[str]
    restart_count: int
    message: str


class PodDetails(TypedDict):
    """파드 상세 정보"""
    name: str
    namespace: str
    labels: dict
    memory_request: Optional[str]
    memory_limit: Optional[str]
    cpu_request: Optional[str]
    cpu_limit: Optional[str]
    node: Optional[str]
    status: str


class FixPlan(TypedDict):
    """수정 계획"""
    action: str  # patch_memory, restart_pod, update_image, etc.
    target_resource: str  # deployment, statefulset, pod
    target_name: str
    namespace: str
    changes: dict  # 구체적인 변경 사항
    kubectl_command: str  # 실행할 kubectl 명령어
    rollback_command: str  # 롤백 명령어


class AgentState(TypedDict):
    """LangGraph 에이전트 상태"""
    # 입력
    user_query: str
    target_namespace: str
    target_pod: Optional[str]
    
    # 이슈 감지 단계
    detected_issues: list[IssueInfo]
    selected_issue: Optional[IssueInfo]
    
    # 정보 수집 단계
    pod_details: Optional[PodDetails]
    pod_events: list[dict]
    pod_logs: str
    
    # 분석 단계
    analysis_result: str
    root_cause: str
    
    # 수정 계획 단계
    fix_plan: Optional[FixPlan]
    
    # 승인 및 실행 단계
    approval_status: Literal["pending", "approved", "rejected", "not_required"]
    execution_result: str
    
    # 최종 결과
    final_response: str
    error: Optional[str]
