"""에러 분류 노드"""
import json
from src.dr_kube.state import AgentState
from src.dr_kube.llm import get_llm_client
from src.dr_kube.prompts import CLASSIFY_ERROR_PROMPT
from src.tools.logger import get_logger

logger = get_logger(__name__)


def classify_error(state: AgentState) -> AgentState:
    """
    로그를 분석하여 에러 카테고리를 분류하는 노드
    
    Args:
        state: 현재 상태
        
    Returns:
        에러 카테고리가 추가된 상태
    """
    try:
        logger.info("에러 분류 시작")
        
        if state.get("error"):
            return state
        
        logs = state.get("logs", [])
        if not logs:
            logger.warning("분류할 로그가 없습니다")
            return {
                **state,
                "error_category": "unknown",
                "error_type": "no_logs",
                "status": "error"
            }
        
        # LLM을 사용하여 에러 분류
        llm_client = get_llm_client()
        logs_text = "\n".join(logs)
        
        prompt = CLASSIFY_ERROR_PROMPT.format(logs=logs_text)
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
            
            classification = json.loads(response)
            error_category = classification.get("category", "unknown")
            error_type = classification.get("type", "unknown")
            
            logger.info(f"에러 분류 완료: {error_category} - {error_type}")
            
            return {
                **state,
                "error_category": error_category,
                "error_type": error_type,
                "status": "processing"
            }
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 파싱 실패, 기본값 사용: {str(e)}")
            # 키워드 기반 간단한 분류
            logs_text_lower = logs_text.lower()
            if "oom" in logs_text_lower or "out of memory" in logs_text_lower:
                error_category = "oom"
            elif "crashloop" in logs_text_lower or "crash loop" in logs_text_lower:
                error_category = "crashloop"
            elif "config" in logs_text_lower or "yaml" in logs_text_lower:
                error_category = "config_error"
            else:
                error_category = "unknown"
            
            return {
                **state,
                "error_category": error_category,
                "error_type": "unknown",
                "status": "processing"
            }
            
    except Exception as e:
        logger.error(f"에러 분류 실패: {str(e)}")
        return {
            **state,
            "error": f"에러 분류 실패: {str(e)}",
            "error_category": "unknown",
            "status": "error"
        }
