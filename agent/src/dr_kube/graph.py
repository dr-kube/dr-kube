"""LangGraph 그래프 정의"""
import json
import re
from langgraph.graph import StateGraph, END
from dr_kube.state import IssueState
from dr_kube.llm import get_llm
from dr_kube.prompts import ANALYZE_PROMPT


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
    """결과 완료 표시"""
    if state.get("error"):
        return state
    return {"status": "done"}


def create_graph():
    """LangGraph 워크플로우 생성"""
    workflow = StateGraph(IssueState)

    # 노드 추가
    workflow.add_node("load_issue", load_issue)
    workflow.add_node("analyze", analyze)
    workflow.add_node("suggest", suggest)

    # 엣지 정의
    workflow.set_entry_point("load_issue")
    workflow.add_edge("load_issue", "analyze")
    workflow.add_edge("analyze", "suggest")
    workflow.add_edge("suggest", END)

    return workflow.compile()
