"""복구 검증 노드"""
import json
from src.dr_kube.state import AgentState
from src.dr_kube.llm import get_llm_client
from src.dr_kube.prompts import VERIFY_RECOVERY_PROMPT
from src.dr_kube.services.kubernetes_client import KubernetesClient
from src.tools.logger import get_logger

logger = get_logger(__name__)


def verify_recovery(state: AgentState) -> AgentState:
    """
    복구 작업이 성공했는지 검증하는 노드
    
    Args:
        state: 현재 상태
        
    Returns:
        복구 검증 결과가 추가된 상태
    """
    try:
        logger.info("복구 검증 시작")
        
        if state.get("error"):
            return state
        
        # Phase 1: 시뮬레이션 모드
        suggested_actions = state.get("suggested_actions", [])
        all_namespaces = state.get("all_namespaces", False)
        namespace = state.get("namespace", "default")
        resource_type = state.get("resource_type", "unknown")
        resource_name = state.get("resource_name", "unknown")
        
        # Kubernetes 리소스 상태 확인
        resource_status = ""
        try:
            k8s_client = KubernetesClient()
            
            # 전체 namespace 조회 지원
            if all_namespaces:
                logger.info("전체 namespace에서 리소스 상태 조회")
                resource_status_dict = k8s_client.get_resource_status_all_namespaces(
                    resource_type=resource_type,
                    resource_name=resource_name
                )
                if resource_status_dict:
                    resource_status = "\n".join([
                        f"[{ns}] {status}"
                        for ns, status in resource_status_dict.items()
                    ])
                else:
                    resource_status = "전체 namespace에서 리소스를 찾을 수 없습니다"
            else:
                resource_status = k8s_client.get_resource_status(
                    namespace=namespace,
                    resource_type=resource_type,
                    resource_name=resource_name
                )
        except Exception as e:
            logger.warning(f"리소스 상태 확인 실패: {str(e)}")
            resource_status = f"상태 확인 실패: {str(e)}"
        
        # LLM을 사용하여 복구 검증
        llm_client = get_llm_client()
        
        actions_summary = json.dumps(suggested_actions, ensure_ascii=False, indent=2)
        
        prompt = VERIFY_RECOVERY_PROMPT.format(
            actions=actions_summary,
            resource_status=resource_status
        )
        
        response = llm_client.invoke(prompt)
        
        # JSON 응답 파싱
        try:
            # JSON 블록 추출
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            
            verification = json.loads(response)
            recovery_success = verification.get("recovery_success", False)
            current_status = verification.get("current_status", "알 수 없음")
            
            logger.info(f"복구 검증 완료: 성공={recovery_success}")
            
            return {
                **state,
                "recovery_status": "success" if recovery_success else "failed",
                "current_status": current_status,
                "status": "completed"
            }
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 파싱 실패: {str(e)}")
            # 기본 검증 결과
            return {
                **state,
                "recovery_status": "pending",
                "current_status": response[:200],
                "status": "completed"
            }
            
    except Exception as e:
        logger.error(f"복구 검증 실패: {str(e)}")
        return {
            **state,
            "error": f"복구 검증 실패: {str(e)}",
            "recovery_status": "failed",
            "status": "error"
        }
