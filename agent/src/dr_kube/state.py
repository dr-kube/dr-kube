"""상태 정의"""
from typing import TypedDict


class IssueState(TypedDict, total=False):
    """LangGraph 상태 - 이슈 분석 워크플로우"""

    # 입력
    issue_file: str
    issue_data: dict

    # ArgoCD/K8s 수집 데이터
    argocd_apps: list[dict]  # ArgoCD Application 목록
    unhealthy_apps: list[dict]  # 비정상 Application
    k8s_pods: list[dict]  # K8s Pod 목록
    k8s_events: list[dict]  # K8s Event 목록

    # 분석 결과
    analysis: str
    root_cause: str
    severity: str  # critical, high, medium, low

    # 해결책
    suggestions: list[str]
    fix_files: list[dict]  # 수정할 Git 파일 [{path, diff}, ...]

    # 메타
    status: str  # pending, argocd_collected, k8s_collected, analyzed, done
    error: str  # 에러 메시지 (있을 경우)
