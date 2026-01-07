"""LLM 프로바이더 - Ollama/Gemini 선택"""
import os
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()


def get_llm() -> BaseChatModel:
    """환경변수에 따라 LLM 인스턴스 반환"""
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경변수가 필요합니다")

        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-pro"),
            google_api_key=api_key,
            temperature=0.3,
        )

    # 기본값: Ollama
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        temperature=0.3,
    )
