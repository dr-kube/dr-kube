"""LLM 프로바이더 - Copilot / Gemini / Ollama 선택"""
import os
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()


def get_llm() -> BaseChatModel:
    """환경변수에 따라 LLM 인스턴스 반환

    우선순위: GitHub Copilot → Gemini → Ollama (로컬)
    """
    # GitHub Copilot API (OAuth gho_ 토큰 - Copilot Pro 전용 모델 접근)
    copilot_token = os.getenv("COPILOT_TOKEN")
    if copilot_token:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("COPILOT_MODEL", "gpt-5.3-codex"),
            base_url="https://api.githubcopilot.com",
            api_key=copilot_token,
            temperature=0.3,
        )

    # GitHub Models (PAT로 사용 가능한 Azure AI 호환 API)
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("COPILOT_MODEL", "gpt-4o"),
            base_url="https://models.inference.ai.azure.com",
            api_key=github_token,
            temperature=0.3,
        )

    # GOOGLE_API_KEY가 설정되어 있으면 Gemini 사용
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
            google_api_key=api_key,
            temperature=0.3,
        )

    # 폴백: Ollama (로컬)
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        temperature=0.3,
    )
