import os
from dotenv import load_dotenv

load_dotenv()

# LLM Provider 설정 (openai 또는 gemini)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

# OpenAI 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

# Gemini 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

# Kubernetes 설정
KUBECONFIG = os.getenv("KUBECONFIG", "~/.kube/config")

# 하위 호환성을 위한 설정
MODEL_NAME = GEMINI_MODEL if LLM_PROVIDER == "gemini" else OPENAI_MODEL
