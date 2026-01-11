"""LLM 프롬프트 템플릿"""

# 에러 분류 프롬프트
CLASSIFY_ERROR_PROMPT = """다음 Kubernetes 로그를 분석하여 에러 카테고리를 분류해주세요.

로그:
{logs}

다음 카테고리 중 하나를 선택하고 JSON 형식으로 응답해주세요:
- oom: Out of Memory 에러
- crashloop: CrashLoopBackOff 에러
- config_error: 설정 파일 오류
- resource_exhausted: 리소스 부족
- network_error: 네트워크 연결 오류
- image_pull_error: 이미지 풀 실패
- scheduling_error: 스케줄링 실패
- unknown: 알 수 없는 에러

응답 형식:
{{
    "category": "에러 카테고리",
    "type": "구체적인 에러 타입",
    "confidence": 0.0-1.0
}}
"""

# 근본 원인 분석 프롬프트
ANALYZE_ROOT_CAUSE_PROMPT = """Kubernetes 장애의 근본 원인을 분석해주세요.

에러 카테고리: {error_category}
에러 타입: {error_type}
네임스페이스: {namespace}
리소스: {resource_type}/{resource_name}

로그:
{logs}

다음 항목을 포함하여 분석해주세요:
1. 근본 원인: 장애가 발생한 핵심 원인
2. 심각도: critical, high, medium, low 중 하나
3. 영향 범위: 이 장애가 영향을 미치는 범위
4. 해결 방안: 구체적인 해결 방법

응답 형식:
{{
    "root_cause": "근본 원인 설명",
    "severity": "심각도",
    "impact": "영향 범위",
    "solutions": ["해결 방법 1", "해결 방법 2", ...]
}}
"""

# 액션 생성 프롬프트
GENERATE_ACTION_PROMPT = """다음 장애 상황에 대한 복구 액션을 생성해주세요.

근본 원인: {root_cause}
심각도: {severity}
리소스: {namespace}/{resource_type}/{resource_name}

현재 values.yaml 구조:
{values_yaml_structure}

다음과 같은 액션을 생성해주세요:
1. values.yaml 수정 사항 (메모리 제한 증가, 이미지 태그 변경 등)
2. 필요한 경우 추가 Kubernetes 명령어

응답 형식:
{{
    "actions": [
        {{
            "type": "update_values",
            "target": "values.yaml 경로",
            "changes": {{"key": "value"}},
            "description": "변경 사항 설명"
        }}
    ],
    "kubectl_commands": ["명령어 1", "명령어 2"]
}}
"""

# 복구 검증 프롬프트
VERIFY_RECOVERY_PROMPT = """복구 작업이 성공했는지 검증해주세요.

수행한 액션: {actions}
리소스 상태:
{resource_status}

다음 정보를 제공해주세요:
1. 복구 성공 여부
2. 현재 리소스 상태
3. 추가 조치가 필요한지 여부

응답 형식:
{{
    "recovery_success": true/false,
    "current_status": "현재 상태 설명",
    "additional_actions_needed": ["추가 조치 1", ...]
}}
"""
