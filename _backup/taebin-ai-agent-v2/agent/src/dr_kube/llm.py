"""LLM 클라이언트 래퍼"""
import os
from typing import Optional
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from src.tools.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


class LLMClient:
    """Google Gemini API를 사용하는 LLM 클라이언트"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        LLM 클라이언트 초기화
        
        Args:
            api_key: Google Gemini API 키 (없으면 환경 변수에서 로드)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다. 환경 변수 또는 인자로 제공해주세요.")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=self.api_key,
            temperature=0.7,
        )
        logger.info("LLM 클라이언트 초기화 완료")
    
    def invoke(self, prompt: str) -> str:
        """
        LLM에 프롬프트를 전송하고 응답을 받음
        
        Args:
            prompt: LLM에 전송할 프롬프트
            
        Returns:
            LLM 응답 텍스트
            
        Raises:
            Exception: LLM 호출 실패 시
        """
        try:
            logger.debug(f"LLM 프롬프트 전송: {prompt[:100]}...")
            messages = [HumanMessage(content=prompt)]
            response = self.llm.invoke(messages)
            result = response.content if hasattr(response, 'content') else str(response)
            logger.debug(f"LLM 응답 수신: {result[:100]}...")
            return result
        except Exception as e:
            logger.error(f"LLM 호출 실패: {str(e)}")
            raise


def get_llm_client(api_key: Optional[str] = None) -> LLMClient:
    """
    LLM 클라이언트 인스턴스 생성
    
    Args:
        api_key: Google Gemini API 키 (선택사항)
        
    Returns:
        LLMClient 인스턴스
    """
    return LLMClient(api_key=api_key)
