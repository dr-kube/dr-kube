"""LLM 프로바이더 - GitHub Copilot / Gemini / Ollama 선택"""
import logging
import os
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()

logger = logging.getLogger("dr-kube-llm")

COPILOT_BASE_URL = "https://api.githubcopilot.com"


def get_llm() -> BaseChatModel:
    """환경변수에 따라 LLM 인스턴스 반환

    우선순위: GitHub Copilot > Gemini > Ollama
    """
    provider = os.getenv("LLM_PROVIDER", "").lower()

    # GitHub Copilot (OpenAI 호환 API)
    if provider == "github" or os.getenv("GITHUB_TOKEN"):
        from langchain_openai import ChatOpenAI

        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        model_name = os.getenv("COPILOT_MODEL", "claude-haiku-4-5")
        logger.info("[llm] provider=github-copilot model=%s", model_name)
        return ChatOpenAI(
            model=model_name,
            openai_api_key=token,
            openai_api_base=COPILOT_BASE_URL,
            temperature=0.3,
        )

    # Gemini
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

    # Ollama (로컬 fallback)
    from langchain_ollama import ChatOllama

    model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
    logger.info("[llm] provider=ollama model=%s", model_name)
    return ChatOllama(
        model=model_name,
        temperature=0.3,
    )
