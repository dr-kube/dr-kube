"""LangGraph 그래프 정의"""
import json
import re
import os
from pathlib import Path
from langgraph.graph import StateGraph, END
from dr_kube.state import IssueState
from dr_kube.llm import get_llm
from dr_kube.prompts import ANALYZE_PROMPT, GENERATE_FIX_PROMPT
from dr_kube.github import GitHubClient, generate_branch_name, generate_pr_body


# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def load_issue(state: IssueState) -> IssueState:
    """이슈 파일 로드"""
    try:
        with open(state["issue_file"], "r", encoding="utf-8") as f:
            issue_data = json.load(f)
        return {"issue_data": issue_data, "status": "loaded"}
    except Exception as e:
        return {"error": str(e), "status": "error"}


def analyze(state: IssueState) -> IssueState:
    """LLM으로 이슈 분석"""
    if state.get("error"):
        return state

    issue = state["issue_data"]
    logs_text = "\n".join(issue.get("logs", []))

    prompt = ANALYZE_PROMPT.format(
        type=issue.get("type", "unknown"),
        namespace=issue.get("namespace", "default"),
        resource=issue.get("resource", "unknown"),
        error_message=issue.get("error_message", ""),
        logs=logs_text,
    )

    try:
        llm = get_llm()
        response = llm.invoke(prompt)

        # response.content 처리
        if isinstance(response.content, list):
            # 리스트인 경우 첫 번째 항목 사용
            content = response.content[0] if response.content else ""
            if isinstance(content, dict) and 'text' in content:
                analysis = content['text']
            elif hasattr(content, 'text'):
                analysis = content.text
            else:
                analysis = str(content)
        elif isinstance(response.content, dict) and 'text' in response.content:
            analysis = response.content['text']
        elif isinstance(response.content, str):
            analysis = response.content
        else:
            analysis = str(response.content)

        # 응답 파싱
        root_cause = ""
        severity = "medium"
        suggestions = []
        action_plan = ""
        yaml_diff = ""

        lines = analysis.split("\n")
        current_section = None
        code_block = []
        in_code_block = False
        code_block_type = None

        for line in lines:
            stripped = line.strip()

            # 코드 블록 시작/종료 감지
            if stripped.startswith("```"):
                if not in_code_block:
                    in_code_block = True
                    code_block = []
                    if "bash" in stripped:
                        code_block_type = "bash"
                    elif "yaml" in stripped:
                        code_block_type = "yaml"
                else:
                    # 코드 블록 종료
                    in_code_block = False
                    content = "\n".join(code_block)
                    if code_block_type == "bash":
                        action_plan = content
                    elif code_block_type == "yaml":
                        yaml_diff = content
                    code_block = []
                    code_block_type = None
                continue

            # 코드 블록 내부
            if in_code_block:
                code_block.append(line)
                continue

            # 일반 텍스트 파싱
            if not stripped:
                continue

            if "근본 원인" in stripped:
                parts = stripped.split(":", 1)
                if len(parts) > 1:
                    root_cause = parts[1].strip()
                current_section = "root_cause"
            elif "심각도" in stripped:
                parts = stripped.split(":", 1)
                if len(parts) > 1:
                    sev = parts[1].strip().lower()
                    if sev in ["critical", "high", "medium", "low"]:
                        severity = sev
            elif "해결책" in stripped:
                current_section = "suggestions"
            elif current_section == "suggestions" and stripped and not stripped.startswith("실행") and not stripped.startswith("YAML"):
                # 번호 제거
                suggestion = re.sub(r"^\d+\.\s*", "", stripped)
                if suggestion and not suggestion.startswith("**"):
                    suggestions.append(suggestion)

        return {
            "analysis": analysis,
            "root_cause": root_cause or "분석 결과를 파싱할 수 없습니다",
            "severity": severity,
            "suggestions": suggestions or ["로그를 더 확인하세요"],
            "action_plan": action_plan,
            "yaml_diff": yaml_diff,
            "status": "analyzed",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


def suggest(state: IssueState) -> IssueState:
    """결과 완료 표시 (기존 호환성 유지)"""
    if state.get("error"):
        return state
    return {"status": "done"}


def generate_fix(state: IssueState) -> IssueState:
    """YAML 수정안 생성"""
    if state.get("error"):
        return state

    issue = state.get("issue_data", {})

    # 이슈에 values_file이 명시되어 있으면 사용
    if issue.get("values_file"):
        target_file = issue.get("values_file")
    else:
        # 이슈 타입에 따라 대상 파일 결정 (기본 매핑)
        issue_type = issue.get("type", "unknown")
        target_file_map = {
            "oom": "values/oom-test.yaml",
            "cpu_throttle": "values/oom-test.yaml",
            "pod_crash": "values/oom-test.yaml",
            "default": "values/oom-test.yaml",
        }
        target_file = target_file_map.get(issue_type, target_file_map["default"])

    namespace = issue.get("namespace", "default")
    target_path = PROJECT_ROOT / target_file

    # 파일이 없으면 스킵
    if not target_path.exists():
        return {
            "error": f"대상 파일을 찾을 수 없습니다: {target_file}",
            "status": "error",
        }

    # 현재 YAML 읽기
    with open(target_path, "r", encoding="utf-8") as f:
        current_yaml = f.read()

    # LLM으로 수정안 생성
    prompt = GENERATE_FIX_PROMPT.format(
        type=issue_type,
        namespace=namespace,
        resource=issue.get("resource", "unknown"),
        error_message=issue.get("error_message", ""),
        root_cause=state.get("root_cause", ""),
        severity=state.get("severity", "medium"),
        target_file=target_file,
        current_yaml=current_yaml,
    )

    try:
        llm = get_llm()
        response = llm.invoke(prompt)

        # response.content 처리
        if isinstance(response.content, list):
            content = response.content[0] if response.content else ""
            if isinstance(content, dict) and "text" in content:
                result = content["text"]
            elif hasattr(content, "text"):
                result = content.text
            else:
                result = str(content)
        elif isinstance(response.content, str):
            result = response.content
        else:
            result = str(response.content)

        # YAML 블록 추출
        yaml_match = re.search(r"```yaml\n(.*?)```", result, re.DOTALL)
        fix_content = yaml_match.group(1).strip() if yaml_match else current_yaml

        # 변경 설명 추출
        desc_match = re.search(r"변경 설명:\s*(.+?)(?:\n|$)", result)
        fix_description = (
            desc_match.group(1).strip() if desc_match else "자동 생성된 수정안"
        )

        return {
            "target_file": target_file,
            "fix_content": fix_content,
            "fix_description": fix_description,
            "status": "fix_generated",
        }
    except Exception as e:
        return {"error": f"수정안 생성 실패: {str(e)}", "status": "error"}


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
        pr_title = f"🔧 [{issue.get('type', 'fix').upper()}] {issue.get('resource', 'unknown')} 자동 수정"
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


def create_graph(with_pr: bool = False):
    """LangGraph 워크플로우 생성

    Args:
        with_pr: True면 PR 생성까지 포함, False면 분석만
    """
    workflow = StateGraph(IssueState)

    # 노드 추가
    workflow.add_node("load_issue", load_issue)
    workflow.add_node("analyze", analyze)

    if with_pr:
        # 전체 플로우: load_issue → analyze → generate_fix → create_pr
        workflow.add_node("generate_fix", generate_fix)
        workflow.add_node("create_pr", create_pr)

        workflow.set_entry_point("load_issue")
        workflow.add_edge("load_issue", "analyze")
        workflow.add_edge("analyze", "generate_fix")
        workflow.add_edge("generate_fix", "create_pr")
        workflow.add_edge("create_pr", END)
    else:
        # 기존 플로우: load_issue → analyze → suggest
        workflow.add_node("suggest", suggest)

        workflow.set_entry_point("load_issue")
        workflow.add_edge("load_issue", "analyze")
        workflow.add_edge("analyze", "suggest")
        workflow.add_edge("suggest", END)

    return workflow.compile()
