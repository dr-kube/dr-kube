"""프롬프트 템플릿"""

ANALYZE_PROMPT = """당신은 Kubernetes 전문가입니다.
다음 K8s 이슈를 분석하고 해결책을 제시해주세요.

## 이슈 정보
- 타입: {type}
- 네임스페이스: {namespace}
- 리소스: {resource}
- 에러 메시지: {error_message}

## 로그
{logs}

## 요청사항
다음 형식으로 응답해주세요:

근본 원인: [한 문장으로 원인 설명]

심각도: [critical/high/medium/low 중 하나]

해결책:[표로 간단히 설명]
"""
