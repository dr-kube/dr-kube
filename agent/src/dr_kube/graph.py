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
        analysis = response.content

        # 응답 파싱
        root_cause = ""
        severity = "medium"
        suggestions = []

        lines = analysis.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "근본 원인" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    root_cause = parts[1].strip()
                current_section = "root_cause"
            elif "심각도" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    sev = parts[1].strip().lower()
                    if sev in ["critical", "high", "medium", "low"]:
                        severity = sev
            elif "해결책" in line:
                current_section = "suggestions"
            elif current_section == "suggestions" and line:
                # 번호 제거
                suggestion = re.sub(r"^\d+\.\s*", "", line)
                if suggestion:
                    suggestions.append(suggestion)

        return {
            "analysis": analysis,
            "root_cause": root_cause or "분석 결과를 파싱할 수 없습니다",
            "severity": severity,
            "suggestions": suggestions or ["로그를 더 확인하세요"],
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
