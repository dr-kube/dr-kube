"""LLM 프로바이더 - Copilot / Gemini / Ollama 선택"""
import os
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()


def get_llm() -> BaseChatModel:
    """환경변수에 따라 LLM 인스턴스 반환

    LLM_PROVIDER 우선순위: copilot → github → gemini → ollama
    LLM_PROVIDER 미설정 시: COPILOT_TOKEN → GEMINI_API_KEY → Ollama 순 자동 감지
    (GITHUB_TOKEN은 git 용도로만 사용 — LLM 자동 감지에서 제외)
    """
    provider = os.getenv("LLM_PROVIDER", "").lower()

    # GitHub Copilot Pro API
    if provider == "copilot" or (not provider and os.getenv("COPILOT_TOKEN")):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.getenv("COPILOT_MODEL", "gpt-4o"),
            base_url="https://api.githubcopilot.com",
            api_key=os.getenv("COPILOT_TOKEN"),
            temperature=0.3,
            default_headers={
                "Editor-Version": "vscode/1.96.0",
                "Editor-Plugin-Version": "copilot-chat/0.22.4",
                "Openai-Intent": "conversation-panel",
                "X-GitHub-Api-Version": "2023-07-07",
            },
        )

    # GitHub Models (Azure AI 호환)
    if provider == "github":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.getenv("COPILOT_MODEL", "gpt-4o"),
            base_url="https://models.inference.ai.azure.com",
            api_key=os.getenv("GITHUB_TOKEN"),
            temperature=0.3,
        )

    # Gemini
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if provider == "gemini" or (not provider and api_key):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            google_api_key=api_key,
            temperature=0.3,
        )

    raise ValueError("LLM 설정 없음: COPILOT_TOKEN 또는 GEMINI_API_KEY 환경변수를 설정하세요.")
