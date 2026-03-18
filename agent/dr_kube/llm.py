"""LLM 프로바이더 - Ollama/Gemini 선택"""
import logging
import os
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()

logger = logging.getLogger("dr-kube-llm")


def get_llm() -> BaseChatModel:
    """환경변수에 따라 LLM 인스턴스 반환"""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    if api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        logger.info("[llm] provider=gemini model=%s", model_name)
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.3,
        )

    from langchain_ollama import ChatOllama

    model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
    logger.info("[llm] provider=ollama model=%s", model_name)
    return ChatOllama(
        model=model_name,
        temperature=0.3,
    )
