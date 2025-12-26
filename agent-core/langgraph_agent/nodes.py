"""
LangGraph 노드 정의
각 노드는 워크플로우의 한 단계를 담당
"""
from typing import Literal
from .state import AgentState, FixPlan
from .tools import k8s, llm


def detect_issues(state: AgentState) -> AgentState:
    """이슈 감지 노드: 문제가 있는 파드들을 찾음"""
    namespace = state.get("target_namespace", "default")
    target_pod = state.get("target_pod")
    
    issues = k8s.get_pods_with_issues(namespace)
    
    # 특정 파드 지정된 경우 필터링
    if target_pod:
        issues = [i for i in issues if i["pod_name"] == target_pod]
    
    if not issues:
        return {
            **state,
            "detected_issues": [],
            "final_response": f"✅ {namespace} 네임스페이스에서 이슈가 발견되지 않았습니다.",
            "error": None
        }
    
    return {
        **state,
        "detected_issues": issues,
        "selected_issue": issues[0],  # 첫 번째 이슈 선택
        "error": None
    }


def collect_info(state: AgentState) -> AgentState:
    """정보 수집 노드: 선택된 이슈에 대한 상세 정보 수집"""
    issue = state.get("selected_issue")
    
    if not issue:
        return {**state, "error": "선택된 이슈가 없습니다"}
    
    pod_name = issue["pod_name"]
    namespace = issue["namespace"]
    container = issue.get("container_name")
    
    # 상세 정보 수집
    pod_details = k8s.get_pod_details(pod_name, namespace)
    events = k8s.get_pod_events(pod_name, namespace)
    logs = k8s.get_pod_logs(pod_name, namespace, container)
    
    return {
        **state,
        "pod_details": pod_details,
        "pod_events": events,
        "pod_logs": logs,
        "error": None
    }


def analyze_issue(state: AgentState) -> AgentState:
    """분석 노드: LLM으로 이슈 분석"""
    issue = state.get("selected_issue")
    pod_details = state.get("pod_details")
    events = state.get("pod_events", [])
    logs = state.get("pod_logs", "")
    
    if not issue or not pod_details:
        return {**state, "error": "분석에 필요한 정보가 부족합니다"}
    
    issue_type = issue["type"]
    restart_count = issue.get("restart_count", 0)
    
    try:
        if issue_type == "oomkilled":
            analysis = llm.analyze_oom_issue(pod_details, events, logs, restart_count)
            root_cause = analysis.get("root_cause", "알 수 없음")
            analysis_text = analysis.get("analysis", "")
            
            # 분석 결과를 상태에 저장
            state["_oom_analysis"] = analysis
            
        elif issue_type == "crashloop":
            analysis = llm.analyze_crashloop_issue(pod_details, events, logs, restart_count)
            root_cause = analysis.get("root_cause", "알 수 없음")
            analysis_text = analysis.get("analysis", "")
            
            state["_crashloop_analysis"] = analysis
            
        else:
            root_cause = f"이슈 타입: {issue_type}"
            analysis_text = f"이슈 메시지: {issue.get('message', '')}"
        
        return {
            **state,
            "root_cause": root_cause,
            "analysis_result": analysis_text,
            "error": None
        }
    except Exception as e:
        return {
            **state,
            "root_cause": "분석 실패",
            "analysis_result": str(e),
            "error": str(e)
        }


def create_fix_plan(state: AgentState) -> AgentState:
    """수정 계획 노드: 분석 결과를 바탕으로 수정 계획 생성"""
    issue = state.get("selected_issue")
    pod_details = state.get("pod_details")
    
    if not issue or not pod_details:
        return {**state, "error": "수정 계획에 필요한 정보가 부족합니다"}
    
    issue_type = issue["type"]
    pod_name = issue["pod_name"]
    namespace = issue["namespace"]
    container_name = issue.get("container_name", "")
    
    # Deployment 이름 조회
    deployment_name = k8s.get_deployment_for_pod(pod_name, namespace)
    
    if issue_type == "oomkilled":
        # OOM 분석 결과에서 권장 메모리 가져오기
        oom_analysis = state.get("_oom_analysis", {})
        new_limit = oom_analysis.get("recommended_memory_limit", "512Mi")
        new_request = oom_analysis.get("recommended_memory_request", "256Mi")
        
        if deployment_name:
            fix_plan: FixPlan = {
                "action": "patch_memory",
                "target_resource": "deployment",
                "target_name": deployment_name,
                "namespace": namespace,
                "changes": {
                    "container": container_name,
                    "memory_limit": new_limit,
                    "memory_request": new_request
                },
                "kubectl_command": f"kubectl patch deployment {deployment_name} -n {namespace} -p '{{\"spec\":{{\"template\":{{\"spec\":{{\"containers\":[{{\"name\":\"{container_name}\",\"resources\":{{\"limits\":{{\"memory\":\"{new_limit}\"}},\"requests\":{{\"memory\":\"{new_request}\"}}}}}}]}}}}}}'",
                "rollback_command": f"kubectl rollout undo deployment {deployment_name} -n {namespace}"
            }
        else:
            fix_plan = {
                "action": "manual_fix_required",
                "target_resource": "pod",
                "target_name": pod_name,
                "namespace": namespace,
                "changes": {"message": "Deployment를 찾을 수 없습니다. 수동으로 수정해주세요."},
                "kubectl_command": "",
                "rollback_command": ""
            }
    
    elif issue_type == "crashloop":
        crashloop_analysis = state.get("_crashloop_analysis", {})
        suggested_action = crashloop_analysis.get("suggested_action", "restart")
        
        if suggested_action == "restart" and deployment_name:
            fix_plan = {
                "action": "rollout_restart",
                "target_resource": "deployment",
                "target_name": deployment_name,
                "namespace": namespace,
                "changes": {"action": "restart"},
                "kubectl_command": f"kubectl rollout restart deployment {deployment_name} -n {namespace}",
                "rollback_command": f"kubectl rollout undo deployment {deployment_name} -n {namespace}"
            }
        else:
            fix_plan = {
                "action": "manual_fix_required",
                "target_resource": "pod",
                "target_name": pod_name,
                "namespace": namespace,
                "changes": {"message": crashloop_analysis.get("fix_steps", [])},
                "kubectl_command": "",
                "rollback_command": ""
            }
    
    else:
        fix_plan = {
            "action": "manual_fix_required",
            "target_resource": "pod",
            "target_name": pod_name,
            "namespace": namespace,
            "changes": {"message": f"이슈 타입 {issue_type}은 자동 수정을 지원하지 않습니다."},
            "kubectl_command": "",
            "rollback_command": ""
        }
    
    return {
        **state,
        "fix_plan": fix_plan,
        "approval_status": "pending",
        "error": None
    }


def wait_for_approval(state: AgentState) -> AgentState:
    """승인 대기 노드: 사용자 승인 요청"""
    fix_plan = state.get("fix_plan")
    
    if not fix_plan:
        return {**state, "approval_status": "not_required"}
    
    if fix_plan["action"] == "manual_fix_required":
        return {**state, "approval_status": "not_required"}
    
    # 여기서는 상태만 설정, 실제 승인은 외부에서 처리
    return {**state, "approval_status": "pending"}


def execute_fix(state: AgentState) -> AgentState:
    """수정 실행 노드: 승인된 수정 계획 실행"""
    fix_plan = state.get("fix_plan")
    approval = state.get("approval_status")
    
    if approval != "approved":
        return {
            **state,
            "execution_result": "승인되지 않아 실행하지 않았습니다.",
            "error": None
        }
    
    if not fix_plan or fix_plan["action"] == "manual_fix_required":
        return {
            **state,
            "execution_result": "자동 실행이 불가능합니다.",
            "error": None
        }
    
    action = fix_plan["action"]
    target_name = fix_plan["target_name"]
    namespace = fix_plan["namespace"]
    
    try:
        if action == "patch_memory":
            changes = fix_plan["changes"]
            success, result = k8s.patch_deployment_resources(
                deployment_name=target_name,
                namespace=namespace,
                container_name=changes["container"],
                memory_limit=changes.get("memory_limit"),
                memory_request=changes.get("memory_request")
            )
        elif action == "rollout_restart":
            success, result = k8s.rollout_restart("deployment", target_name, namespace)
        else:
            success, result = False, f"Unknown action: {action}"
        
        if success:
            execution_result = f"✅ 수정 완료: {result}"
        else:
            execution_result = f"❌ 수정 실패: {result}"
        
        return {
            **state,
            "execution_result": execution_result,
            "error": None if success else result
        }
    
    except Exception as e:
        return {
            **state,
            "execution_result": f"❌ 실행 중 오류: {str(e)}",
            "error": str(e)
        }


def generate_response(state: AgentState) -> AgentState:
    """응답 생성 노드: 최종 결과 정리"""
    issue = state.get("selected_issue")
    pod_details = state.get("pod_details")
    analysis = state.get("analysis_result", "")
    root_cause = state.get("root_cause", "")
    fix_plan = state.get("fix_plan")
    approval = state.get("approval_status")
    execution_result = state.get("execution_result", "")
    
    if not issue:
        return state
    
    # 응답 구성
    response_parts = []
    
    response_parts.append(f"## 🔍 이슈 분석 결과\n")
    response_parts.append(f"**파드**: {issue['pod_name']} ({issue['namespace']})")
    response_parts.append(f"**이슈 타입**: {issue['type'].upper()}")
    response_parts.append(f"**재시작 횟수**: {issue.get('restart_count', 0)}")
    
    if pod_details:
        response_parts.append(f"\n### 리소스 설정")
        response_parts.append(f"- Memory Request: {pod_details.get('memory_request', 'Not set')}")
        response_parts.append(f"- Memory Limit: {pod_details.get('memory_limit', 'Not set')}")
    
    response_parts.append(f"\n### 근본 원인")
    response_parts.append(root_cause)
    
    response_parts.append(f"\n### 상세 분석")
    response_parts.append(analysis)
    
    if fix_plan:
        response_parts.append(f"\n## 🔧 수정 계획")
        response_parts.append(f"**액션**: {fix_plan['action']}")
        response_parts.append(f"**대상**: {fix_plan['target_resource']}/{fix_plan['target_name']}")
        
        if fix_plan.get("kubectl_command"):
            response_parts.append(f"\n**실행 명령어**:\n```bash\n{fix_plan['kubectl_command']}\n```")
        
        if fix_plan.get("rollback_command"):
            response_parts.append(f"\n**롤백 명령어**:\n```bash\n{fix_plan['rollback_command']}\n```")
    
    if approval == "approved" and execution_result:
        response_parts.append(f"\n## ✅ 실행 결과")
        response_parts.append(execution_result)
    elif approval == "rejected":
        response_parts.append(f"\n## ⛔ 수정이 거부되었습니다")
    elif approval == "pending":
        response_parts.append(f"\n## ⏳ 승인 대기 중")
        response_parts.append("위 수정 계획을 실행하려면 승인해주세요.")
    
    final_response = "\n".join(response_parts)
    
    return {
        **state,
        "final_response": final_response
    }


# 라우팅 함수들
def should_continue_after_detect(state: AgentState) -> Literal["collect_info", "end"]:
    """이슈 감지 후 다음 단계 결정"""
    if not state.get("detected_issues"):
        return "end"
    return "collect_info"


def should_execute(state: AgentState) -> Literal["execute_fix", "generate_response"]:
    """승인 상태에 따라 실행 여부 결정"""
    approval = state.get("approval_status")
    if approval == "approved":
        return "execute_fix"
    return "generate_response"
