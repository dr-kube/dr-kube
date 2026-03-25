"""LLM 구조화 출력 스키마 (Pydantic)"""
from typing import Literal
from pydantic import BaseModel, Field, field_validator
import yaml


class AnalysisResult(BaseModel):
    """analyze 노드 LLM 출력"""
    root_cause: str = Field(description="장애의 근본 원인 (한국어, 1-2문장)")
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="심각도: critical=서비스 전체 중단, high=주요 기능 불가, medium=성능 저하, low=경미"
    )
    affected_services: list[str] = Field(
        description="직접 및 연쇄 영향 서비스 목록 (예: ['order-service', 'frontend'])"
    )
    analysis_summary: str = Field(description="분석 요약 (Slack 메시지용, 3줄 이내)")
    requires_human_approval: bool = Field(
        description="True: 위험한 변경(핵심 서비스, 여러 서비스 동시 변경, crash_loop). False: 리소스 단순 조정"
    )


class FixPlanOutput(BaseModel):
    """plan_fix 노드 LLM 출력"""
    target_service: str = Field(
        description="수정할 서비스명 (frontend / order-service / menu-service / delivery-service)"
    )
    target_file: str = Field(
        description="manifests/delivery-app/{service}.yaml 형식"
    )
    modified_manifest: str = Field(
        description="수정된 전체 Kubernetes Deployment YAML"
    )
    changed_fields: list[str] = Field(
        description="변경된 YAML 경로 목록 (예: spec.template.spec.containers[0].resources.limits.memory)"
    )
    fix_description: str = Field(
        max_length=60,
        description="영문, 동사 원형으로 시작 (예: increase memory limit for order-service)"
    )
    rationale: str = Field(description="변경 근거 한 문장 (한국어)")

    @field_validator("modified_manifest")
    @classmethod
    def validate_yaml_syntax(cls, v: str) -> str:
        try:
            yaml.safe_load(v)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML 문법 오류: {e}") from e
        return v

    @field_validator("target_file")
    @classmethod
    def validate_target_path(cls, v: str) -> str:
        if not v.startswith("manifests/delivery-app/"):
            raise ValueError(f"target_file은 manifests/delivery-app/ 로 시작해야 합니다: {v}")
        return v
