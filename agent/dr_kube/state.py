"""상태 정의"""
from typing import TypedDict


class IssueState(TypedDict, total=False):
    """LangGraph 상태 - 이슈 분석 워크플로우"""

    # 입력
    issue_file: str
    issue_data: dict

    # 분류 (classify_issue 출력)
    route: str  # argocd, analyze_only, rule_based, llm
    target_file: str   # 수정할 values 파일 경로
    original_yaml: str  # 원본 YAML (validate에서 diff 비교용)

    # 분석 결과
    root_cause: str
    severity: str  # critical, high, medium, low
    suggestions: list[str]

    # 수정안
    fix_content: str      # 수정된 YAML 내용
    fix_description: str  # 변경 설명 (30자 이내 영어)
    fix_method: str       # rule_based, llm, none
    previous_fix_content: str  # 이전 수정안 (수정 요청 시 PR_REVIEW_RESPONSE_PROMPT용)

    # 검증
    retry_count: int
    validation_error: str  # 검증 실패 사유 (retry 시 LLM 프롬프트에 주입)

    # PR 생성
    branch_name: str
    pr_url: str
    pr_number: int
    pr_review_comment: str  # AGENT-2: 리뷰어 댓글 (Human-in-the-Loop)

    # 워크플로우 제어
    status: str  # loaded, classified, analyzed, validated, pr_created, done, error
    error: str
