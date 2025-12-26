import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # LLM 설정
    llm_provider: str = "openai"  # openai, anthropic
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    model_name: str = "gpt-4o-mini"
    
    # Git 설정
    git_repo_path: str = "."  # Git 저장소 경로 (기본값: 현재 디렉토리)
    git_branch: str = "main"
    git_remote: Optional[str] = None  # 원격 저장소 (선택적)
    
    # Kubernetes 설정
    kubeconfig_path: Optional[str] = None  # kubeconfig 파일 경로
    
    # ArgoCD 설정
    argocd_server: Optional[str] = None
    argocd_token: Optional[str] = None
    
    # Loki 설정
    loki_url: Optional[str] = None
    loki_username: Optional[str] = None
    loki_password: Optional[str] = None
    
    # 로깅 설정
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

