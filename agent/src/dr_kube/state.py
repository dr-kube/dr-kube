"""상태 정의"""
from typing import TypedDict


class IssueState(TypedDict, total=False):
    """LangGraph 상태 - 이슈 분석 워크플로우"""

    # 입력
    issue_file: str
    issue_data: dict

    # 분석 결과
    analysis: str
    root_cause: str
    severity: str  # critical, high, medium, low

    # 해결책
    suggestions: list[str]

    # 메타
    status: str  # pending, analyzed, done
    error: str  # 에러 메시지 (있을 경우)
