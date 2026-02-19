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
    suggestions: list[str]

    # 수정안
    target_file: str  # 수정할 values 파일 경로
    original_yaml: str  # 원본 YAML (validate에서 diff 비교용)
    fix_content: str  # 수정된 YAML 내용
    fix_description: str  # 변경 설명

    # PR 생성
    branch_name: str  # PR 브랜치명
    pr_url: str  # 생성된 PR URL
    pr_number: int  # PR 번호

    # 워크플로우 제어
    retry_count: int  # 검증 실패 재시도 횟수 (최대 3)
    status: str  # loaded, analyzed, validated, pr_created, done, error
    error: str  # 에러 메시지 (있을 경우)
