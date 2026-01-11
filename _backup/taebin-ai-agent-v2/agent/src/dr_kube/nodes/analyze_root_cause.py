"""근본 원인 분석 노드"""
import json
from src.dr_kube.state import AgentState
from src.dr_kube.llm import get_llm_client
from src.dr_kube.prompts import ANALYZE_ROOT_CAUSE_PROMPT
from src.tools.logger import get_logger

logger = get_logger(__name__)


def analyze_root_cause(state: AgentState) -> AgentState:
    """
    에러의 근본 원인을 분석하는 노드
    
    Args:
        state: 현재 상태
        
    Returns:
        근본 원인 분석 결과가 추가된 상태
    """
    try:
        logger.info("근본 원인 분석 시작")
        
        if state.get("error"):
            return state
        
        logs = state.get("logs", [])
        error_category = state.get("error_category", "unknown")
        error_type = state.get("error_type", "unknown")
        namespace = state.get("namespace", "default")
        resource_type = state.get("resource_type", "unknown")
        resource_name = state.get("resource_name", "unknown")
        
        if not logs:
            logger.warning("분석할 로그가 없습니다")
            return {
                **state,
                "root_cause": "로그가 없어 분석할 수 없습니다",
                "severity": "low",
                "status": "error"
            }
        
        # LLM을 사용하여 근본 원인 분석
        llm_client = get_llm_client()
        logs_text = "\n".join(logs)
        
        prompt = ANALYZE_ROOT_CAUSE_PROMPT.format(
            error_category=error_category,
            error_type=error_type,
            namespace=namespace,
            resource_type=resource_type,
            resource_name=resource_name,
            logs=logs_text
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
            
            analysis = json.loads(response)
            root_cause = analysis.get("root_cause", "분석 결과를 파싱할 수 없습니다")
            severity = analysis.get("severity", "medium")
            
            logger.info(f"근본 원인 분석 완료: {root_cause[:100]}...")
            
            return {
                **state,
                "root_cause": root_cause,
                "severity": severity,
                "analysis": response,
                "status": "processing"
            }
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 파싱 실패, 텍스트 그대로 사용: {str(e)}")
            # JSON 파싱 실패 시 응답 전체를 root_cause로 사용
            return {
                **state,
                "root_cause": response[:500],  # 처음 500자만
                "severity": "medium",
                "analysis": response,
                "status": "processing"
            }
            
    except Exception as e:
        logger.error(f"근본 원인 분석 실패: {str(e)}")
        return {
            **state,
            "error": f"근본 원인 분석 실패: {str(e)}",
            "status": "error"
        }
