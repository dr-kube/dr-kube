"""
dr-kube LangGraph 에이전트
사용자 인터페이스 및 워크플로우 실행
"""
from typing import Optional
from .graph import compile_agent
from .state import AgentState


class DrKubeAgent:
    """Kubernetes 이슈 해결 에이전트"""
    
    def __init__(self, namespace: str = "default"):
        """
        에이전트 초기화
        
        Args:
            namespace: 기본 네임스페이스 (기본값: "default")
        """
        self.workflow = compile_agent()
        self._current_state: Optional[AgentState] = None
        self.default_namespace = namespace
    
    def analyze(
        self,
        namespace: Optional[str] = None,
        pod_name: Optional[str] = None,
        auto_approve: bool = False
    ) -> str:
        """
        이슈 분석 및 수정 계획 생성
        
        Args:
            namespace: 대상 네임스페이스 (없으면 기본 네임스페이스 사용)
            pod_name: 특정 파드 지정 (없으면 전체 스캔)
            auto_approve: True면 승인 없이 바로 실행
        
        Returns:
            분석 결과 및 수정 계획
        """
        # namespace가 지정되지 않으면 기본값 사용
        if namespace is None:
            namespace = self.default_namespace
            
        initial_state: AgentState = {
            "user_query": f"Analyze issues in namespace {namespace}",
            "target_namespace": namespace,
            "target_pod": pod_name,
            "detected_issues": [],
            "selected_issue": None,
            "pod_details": None,
            "pod_events": [],
            "pod_logs": "",
            "analysis_result": "",
            "root_cause": "",
            "fix_plan": None,
            "approval_status": "approved" if auto_approve else "pending",
            "execution_result": "",
            "final_response": "",
            "error": None
        }
        
        # 워크플로우 실행
        result = self.workflow.invoke(initial_state)
        self._current_state = result
        
        # 결과를 딕셔너리로 반환
        return {
            "response": result.get("final_response", "분석 결과가 없습니다."),
            "fix_plan": result.get("fix_plan"),
            "detected_issues": result.get("detected_issues", []),
            "approval_status": result.get("approval_status"),
            "error": result.get("error")
        }
    
    def approve_fix(self) -> dict:
        """현재 수정 계획 승인 및 실행"""
        if not self._current_state:
            return {
                "response": "❌ 먼저 analyze()를 실행해주세요.",
                "error": "no_state"
            }
        
        if self._current_state.get("approval_status") != "pending":
            return {
                "response": "❌ 승인 대기 중인 수정 계획이 없습니다.",
                "error": "no_pending_plan"
            }
        
        # 승인 상태로 변경하고 워크플로우 재실행
        self._current_state["approval_status"] = "approved"
        
        # execute_fix와 generate_response만 실행
        from .nodes import execute_fix, generate_response
        
        self._current_state = execute_fix(self._current_state)
        self._current_state = generate_response(self._current_state)
        
        return {
            "response": self._current_state.get("final_response", "실행 결과가 없습니다."),
            "execution_result": self._current_state.get("execution_result"),
            "error": self._current_state.get("error")
        }
    
    def reject_fix(self) -> dict:
        """현재 수정 계획 거부"""
        if not self._current_state:
            return {
                "response": "❌ 먼저 analyze()를 실행해주세요.",
                "error": "no_state"
            }
        
        self._current_state["approval_status"] = "rejected"
        
        from .nodes import generate_response
        self._current_state = generate_response(self._current_state)
        
        return {
            "response": self._current_state.get("final_response", ""),
            "approval_status": "rejected"
        }
    
    def get_fix_plan(self) -> Optional[dict]:
        """현재 수정 계획 조회"""
        if not self._current_state:
            return None
        return self._current_state.get("fix_plan")
    
    def get_detected_issues(self) -> list:
        """감지된 이슈 목록 조회"""
        if not self._current_state:
            return []
        return self._current_state.get("detected_issues", [])
