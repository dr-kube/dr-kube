"""LLM 프롬프트 템플릿"""


def get_classification_prompt(log_text: str) -> str:
    """에러 분류를 위한 프롬프트"""
    return f"""다음 로그를 분석하여 에러를 분류해주세요.

로그 내용:
{log_text}

다음 형식으로 JSON 응답을 제공해주세요:
{{
    "error_category": "에러 카테고리 (oom, crashloop, config_error, resource_exhausted, network_error, image_pull_error, pod_scheduling_error 중 하나 또는 null)",
    "error_severity": "심각도 (critical, warning, info 중 하나)",
    "affected_apps": ["영향받는 애플리케이션 이름 목록"],
    "reasoning": "분류 이유"
}}

에러 카테고리를 찾을 수 없으면 error_category를 null로 설정하세요."""


def get_analysis_prompt(log_text: str, error_category: str, affected_apps: list) -> str:
    """근본 원인 분석을 위한 프롬프트"""
    apps_str = ", ".join(affected_apps) if affected_apps else "알 수 없음"
    
    return f"""다음 로그와 에러 정보를 바탕으로 근본 원인을 분석하고 복구 액션을 제안해주세요.

로그 내용:
{log_text}

에러 카테고리: {error_category}
영향받는 애플리케이션: {apps_str}

다음 형식으로 JSON 응답을 제공해주세요:
{{
    "root_cause": "근본 원인에 대한 상세 분석",
    "suggested_actions": [
        "액션 1: 구체적인 복구 방법",
        "액션 2: 대안 복구 방법"
    ],
    "recommended_action": "가장 권장하는 액션"
}}"""

