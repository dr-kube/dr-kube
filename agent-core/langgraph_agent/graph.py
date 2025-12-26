"""
LangGraph 워크플로우 정의
"""
from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    detect_issues,
    collect_info,
    analyze_issue,
    create_fix_plan,
    wait_for_approval,
    execute_fix,
    generate_response,
    should_continue_after_detect,
    should_execute
)


def create_agent_graph() -> StateGraph:
    """에이전트 워크플로우 그래프 생성"""
    
    # 그래프 생성
    graph = StateGraph(AgentState)
    
    # 노드 추가
    graph.add_node("detect_issues", detect_issues)
    graph.add_node("collect_info", collect_info)
    graph.add_node("analyze_issue", analyze_issue)
    graph.add_node("create_fix_plan", create_fix_plan)
    graph.add_node("wait_for_approval", wait_for_approval)
    graph.add_node("execute_fix", execute_fix)
    graph.add_node("generate_response", generate_response)
    
    # 엣지 정의 (워크플로우 흐름)
    graph.set_entry_point("detect_issues")
    
    # 조건부 엣지: 이슈 감지 후
    graph.add_conditional_edges(
        "detect_issues",
        should_continue_after_detect,
        {
            "collect_info": "collect_info",
            "end": END
        }
    )
    
    # 순차 엣지
    graph.add_edge("collect_info", "analyze_issue")
    graph.add_edge("analyze_issue", "create_fix_plan")
    graph.add_edge("create_fix_plan", "wait_for_approval")
    
    # 조건부 엣지: 승인 후
    graph.add_conditional_edges(
        "wait_for_approval",
        should_execute,
        {
            "execute_fix": "execute_fix",
            "generate_response": "generate_response"
        }
    )
    
    graph.add_edge("execute_fix", "generate_response")
    graph.add_edge("generate_response", END)
    
    return graph


def compile_agent():
    """컴파일된 에이전트 반환"""
    graph = create_agent_graph()
    return graph.compile()
