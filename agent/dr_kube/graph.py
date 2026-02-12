"""LangGraph 그래프 정의

워크플로우:
  with_pr=True:
    load_issue → analyze_and_fix(LLM 1회) → validate → create_pr → END
                                               ↓ 실패 (< 3회)
                                             analyze_and_fix (재시도)
                                               ↓ 실패 (>= 3회)
                                             error_end → END
  with_pr=False:
    load_issue → analyze_and_fix → END
"""
import json
import re
import yaml
from pathlib import Path
from langgraph.graph import StateGraph, END
from dr_kube.state import IssueState
from dr_kube.llm import get_llm
from dr_kube.prompts import ANALYZE_AND_FIX_PROMPT, ANALYZE_ONLY_PROMPT
from dr_kube.github import GitHubClient, generate_branch_name, generate_pr_body

# 프로젝트 루트 경로 (agent/dr_kube/graph.py → dr-kube/)
PROJECT_ROOT = Path(__file__).parent.parent.parent

MAX_RETRIES = 3


# =============================================================================
# 헬퍼 함수
# =============================================================================

def _extract_llm_content(response) -> str:
    """LLM 응답에서 텍스트 추출 (Gemini/Ollama 호환)"""
    if isinstance(response.content, list):
        content = response.content[0] if response.content else ""
        if isinstance(content, dict) and "text" in content:
            return content["text"]
        elif hasattr(content, "text"):
            return content.text
        return str(content)
    elif isinstance(response.content, str):
        return response.content
    return str(response.content)


def _parse_field(text: str, pattern: str) -> str:
    """정규식으로 필드 추출"""
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _parse_severity(text: str) -> str:
    """심각도 파싱"""
    match = re.search(r"심각도:\s*(critical|high|medium|low)", text, re.IGNORECASE)
    return match.group(1).lower() if match else "medium"


def _parse_suggestions(text: str) -> list[str]:
    """해결책 목록 파싱"""
    matches = re.findall(r"^\d+\.\s*(.+)$", text, re.MULTILINE)
    return [s.strip() for s in matches if s.strip()][:3]


def _parse_yaml_block(text: str) -> str:
    """YAML 코드 블록 추출"""
    match = re.search(r"```yaml\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else ""


# =============================================================================
# 노드 함수
# =============================================================================

def load_issue(state: IssueState) -> IssueState:
    """이슈 파일 로드 + target_file 해석 + original_yaml 읽기"""
    if state.get("issue_data"):
        issue_data = state["issue_data"]
    else:
        try:
            with open(state["issue_file"], "r", encoding="utf-8") as f:
                issue_data = json.load(f)
        except Exception as e:
            return {"error": str(e), "status": "error"}

    # target_file 결정 (이슈에 명시된 값 우선, 없으면 converter에서 추론)
    target_file = issue_data.get("values_file", "")
    if not target_file:
        from dr_kube.converter import derive_values_file
        target_file = derive_values_file(
            issue_data.get("resource", ""),
            issue_data.get("namespace", ""),
        )

    # original_yaml 읽기
    original_yaml = ""
    if target_file:
        target_path = PROJECT_ROOT / target_file
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8") as f:
                original_yaml = f.read()
        else:
            target_file = ""  # 파일 없으면 analyze-only 전환

    return {
        "issue_data": issue_data,
        "target_file": target_file,
        "original_yaml": original_yaml,
        "retry_count": 0,
        "status": "loaded",
    }


def analyze_and_fix(state: IssueState) -> IssueState:
    """LLM 1회 호출로 이슈 분석 + YAML 수정안 생성"""
    if state.get("status") == "error":
        return state

    issue = state["issue_data"]
    target_file = state.get("target_file", "")
    original_yaml = state.get("original_yaml", "")
    logs_text = "\n".join(issue.get("logs", []))

    # target_file이 없으면 분석만 수행
    if not target_file or not original_yaml:
        return _analyze_only(state)

    prompt = ANALYZE_AND_FIX_PROMPT.format(
        type=issue.get("type", "unknown"),
        namespace=issue.get("namespace", "default"),
        resource=issue.get("resource", "unknown"),
        error_message=issue.get("error_message", ""),
        logs=logs_text,
        target_file=target_file,
        current_yaml=original_yaml,
    )

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        result = _extract_llm_content(response)

        # 파싱
        root_cause = _parse_field(result, r"근본 원인:\s*(.+?)(?:\n|$)")
        severity = _parse_severity(result)
        suggestions = _parse_suggestions(result)
        fix_content = _parse_yaml_block(result)
        fix_description = _parse_field(result, r"변경 설명:\s*(.+?)(?:\n|$)") or "자동 생성된 수정안"

        if not fix_content:
            return {
                "analysis": result,
                "root_cause": root_cause or "분석 결과를 파싱할 수 없습니다",
                "severity": severity,
                "suggestions": suggestions,
                "error": "LLM 응답에서 YAML 블록을 추출할 수 없습니다",
                "status": "error",
            }

        return {
            "analysis": result,
            "root_cause": root_cause or "분석 결과를 파싱할 수 없습니다",
            "severity": severity,
            "suggestions": suggestions or ["로그를 더 확인하세요"],
            "fix_content": fix_content,
            "fix_description": fix_description,
            "status": "analyzed",
        }
    except Exception as e:
        return {"error": f"분석 + 수정안 생성 실패: {str(e)}", "status": "error"}


def _analyze_only(state: IssueState) -> IssueState:
    """values 파일이 없는 이슈의 분석만 수행"""
    issue = state["issue_data"]
    logs_text = "\n".join(issue.get("logs", []))

    prompt = ANALYZE_ONLY_PROMPT.format(
        type=issue.get("type", "unknown"),
        namespace=issue.get("namespace", "default"),
        resource=issue.get("resource", "unknown"),
        error_message=issue.get("error_message", ""),
        logs=logs_text,
    )

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        result = _extract_llm_content(response)

        return {
            "analysis": result,
            "root_cause": _parse_field(result, r"근본 원인:\s*(.+?)(?:\n|$)") or "분석 결과를 파싱할 수 없습니다",
            "severity": _parse_severity(result),
            "suggestions": _parse_suggestions(result) or ["로그를 더 확인하세요"],
            "status": "done",
        }
    except Exception as e:
        return {"error": f"분석 실패: {str(e)}", "status": "error"}


def validate(state: IssueState) -> IssueState:
    """YAML 수정안 검증: 문법 + 변경 확인"""
    fix_content = state.get("fix_content", "")
    original_yaml = state.get("original_yaml", "")
    retry_count = state.get("retry_count", 0)

    # 1. YAML 문법 검증
    try:
        parsed = yaml.safe_load(fix_content)
        if parsed is None:
            return {"retry_count": retry_count + 1, "error": "YAML 파싱 결과가 비어있습니다", "status": "validation_failed"}
    except yaml.YAMLError as e:
        return {"retry_count": retry_count + 1, "error": f"YAML 문법 오류: {str(e)}", "status": "validation_failed"}

    # 2. 원본과 동일한지 확인
    try:
        original_parsed = yaml.safe_load(original_yaml)
        if parsed == original_parsed:
            return {"retry_count": retry_count + 1, "error": "수정안이 원본과 동일합니다", "status": "validation_failed"}
    except yaml.YAMLError:
        pass  # 원본 파싱 실패해도 수정안 검증은 통과

    # 3. dict 형식인지 확인
    if not isinstance(parsed, dict):
        return {"retry_count": retry_count + 1, "error": "YAML이 dict 형식이 아닙니다", "status": "validation_failed"}

    return {"status": "validated"}


def error_end(state: IssueState) -> IssueState:
    """에러 상태로 워크플로우 종료"""
    retry_count = state.get("retry_count", 0)
    error_msg = state.get("error", "알 수 없는 오류")
    if retry_count >= MAX_RETRIES:
        error_msg = f"검증 {MAX_RETRIES}회 실패 후 종료: {error_msg}"
    return {"status": "error", "error": error_msg}


def create_pr(state: IssueState) -> IssueState:
    """GitHub PR 생성"""
    if state.get("error"):
        return state

    issue = state.get("issue_data", {})
    target_file = state.get("target_file", "")
    fix_content = state.get("fix_content", "")

    if not target_file or not fix_content:
        return {"error": "수정할 파일 또는 내용이 없습니다", "status": "error"}

    # 브랜치명 생성
    branch_name = generate_branch_name(
        issue.get("type", "fix"), issue.get("resource", "unknown")
    )

    # GitHub 클라이언트
    gh = GitHubClient(str(PROJECT_ROOT))

    try:
        # 1. 브랜치 생성
        success, msg = gh.create_branch(branch_name)
        if not success:
            return {"error": f"브랜치 생성 실패: {msg}", "status": "error"}

        # 2. 파일 수정
        target_path = PROJECT_ROOT / target_file
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(fix_content)

        # 3. 커밋 및 푸시
        commit_message = f"fix({issue.get('type', 'unknown')}): {state.get('fix_description', '자동 수정')}"
        success, msg = gh.commit_and_push(target_file, commit_message, branch_name)
        if not success:
            gh.cleanup()
            return {"error": f"커밋/푸시 실패: {msg}", "status": "error"}

        # 4. PR 생성
        pr_title = f"fix({issue.get('type', 'unknown')}): {state.get('fix_description', '자동 수정')}"
        pr_body = generate_pr_body(state)
        success, pr_url, pr_number = gh.create_pr(branch_name, pr_title, pr_body)

        # main으로 복귀
        gh.cleanup()

        if not success:
            return {"error": f"PR 생성 실패: {pr_url}", "status": "error"}

        return {
            "branch_name": branch_name,
            "pr_url": pr_url,
            "pr_number": pr_number,
            "status": "pr_created",
        }
    except Exception as e:
        gh.cleanup()
        return {"error": f"PR 생성 중 오류: {str(e)}", "status": "error"}


# =============================================================================
# 라우팅 함수
# =============================================================================

def _should_create_pr(state: IssueState) -> str:
    """analyze_and_fix 후 라우팅"""
    if state.get("status") == "error":
        return "error_end"
    if state.get("status") == "done":
        return "end"  # 분석만 수행 완료
    return "validate"


def _should_retry(state: IssueState) -> str:
    """validate 후 라우팅"""
    if state.get("status") == "validated":
        return "create_pr"
    if state.get("retry_count", 0) >= MAX_RETRIES:
        return "error_end"
    return "retry"


# =============================================================================
# 그래프 생성
# =============================================================================

def create_graph(with_pr: bool = False):
    """LangGraph 워크플로우 생성

    Args:
        with_pr: True면 PR 생성까지 포함, False면 분석만
    """
    workflow = StateGraph(IssueState)

    workflow.add_node("load_issue", load_issue)
    workflow.add_node("analyze_and_fix", analyze_and_fix)

    if with_pr:
        workflow.add_node("validate", validate)
        workflow.add_node("create_pr", create_pr)
        workflow.add_node("error_end", error_end)

        workflow.set_entry_point("load_issue")
        workflow.add_edge("load_issue", "analyze_and_fix")

        workflow.add_conditional_edges(
            "analyze_and_fix",
            _should_create_pr,
            {"validate": "validate", "end": END, "error_end": "error_end"},
        )

        workflow.add_conditional_edges(
            "validate",
            _should_retry,
            {"create_pr": "create_pr", "retry": "analyze_and_fix", "error_end": "error_end"},
        )

        workflow.add_edge("create_pr", END)
        workflow.add_edge("error_end", END)
    else:
        workflow.set_entry_point("load_issue")
        workflow.add_edge("load_issue", "analyze_and_fix")
        workflow.add_edge("analyze_and_fix", END)

    return workflow.compile()
