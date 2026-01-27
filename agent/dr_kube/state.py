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
    action_plan: str  # kubectl 명령어 등 실행 계획
    yaml_diff: str  # YAML 수정 diff

    # 수정안 생성 (generate_fix)
    target_file: str  # 수정할 values 파일 경로
    fix_content: str  # 수정된 YAML 내용
    fix_description: str  # 변경 설명

    # PR 생성 (create_pr)
    branch_name: str  # PR 브랜치명
    pr_url: str  # 생성된 PR URL
    pr_number: int  # PR 번호

    # 메타
    status: str  # pending, analyzed, fix_generated, pr_created, done
    error: str  # 에러 메시지 (있을 경우)
