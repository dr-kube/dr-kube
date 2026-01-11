"""액션 생성 노드"""
import json
from src.dr_kube.state import AgentState
from src.dr_kube.llm import get_llm_client
from src.dr_kube.prompts import GENERATE_ACTION_PROMPT
from src.dr_kube.services.git_client import GitClient
from src.tools.logger import get_logger

logger = get_logger(__name__)


def generate_action(state: AgentState) -> AgentState:
    """
    복구 액션을 생성하는 노드
    
    Args:
        state: 현재 상태
        
    Returns:
        액션이 추가된 상태
    """
    try:
        logger.info("액션 생성 시작")
        
        if state.get("error"):
            return state
        
        root_cause = state.get("root_cause", "")
        severity = state.get("severity", "medium")
        namespace = state.get("namespace", "default")
        resource_type = state.get("resource_type", "unknown")
        resource_name = state.get("resource_name", "unknown")
        
        if not root_cause:
            logger.warning("근본 원인이 없어 액션을 생성할 수 없습니다")
            return {
                **state,
                "error": "근본 원인이 없습니다",
                "status": "error"
            }
        
        # Git 저장소에서 values.yaml 구조 확인
        git_repo_path = state.get("git_repo_path")
        values_yaml_structure = ""
        if git_repo_path:
            try:
                git_client = GitClient(git_repo_path)
                values_yaml_structure = git_client.get_values_yaml_structure()
            except Exception as e:
                logger.warning(f"values.yaml 구조 확인 실패: {str(e)}")
        
        # LLM을 사용하여 액션 생성
        llm_client = get_llm_client()
        
        prompt = GENERATE_ACTION_PROMPT.format(
            root_cause=root_cause,
            severity=severity,
            namespace=namespace,
            resource_type=resource_type,
            resource_name=resource_name,
            values_yaml_structure=values_yaml_structure or "정보 없음"
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
            
            action_data = json.loads(response)
            suggested_actions = action_data.get("actions", [])
            kubectl_commands = action_data.get("kubectl_commands", [])
            
            logger.info(f"액션 생성 완료: {len(suggested_actions)}개 액션")
            
            return {
                **state,
                "suggested_actions": suggested_actions,
                "kubectl_commands": kubectl_commands,
                "status": "processing"
            }
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 파싱 실패: {str(e)}")
            # 기본 액션 생성
            return {
                **state,
                "suggested_actions": [{
                    "type": "manual_review",
                    "description": "LLM 응답을 수동으로 검토해야 합니다",
                    "raw_response": response[:500]
                }],
                "status": "processing"
            }
            
    except Exception as e:
        logger.error(f"액션 생성 실패: {str(e)}")
        return {
            **state,
            "error": f"액션 생성 실패: {str(e)}",
            "status": "error"
        }
