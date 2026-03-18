"""LLM 프로바이더 - GitHub Copilot / Ollama 선택"""
import logging
import os
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()

logger = logging.getLogger("dr-kube-llm")

COPILOT_BASE_URL = "https://api.githubcopilot.com"


def get_llm() -> BaseChatModel:
    """환경변수에 따라 LLM 인스턴스 반환"""
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
