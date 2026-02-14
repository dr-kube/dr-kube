"""프롬프트 템플릿"""

# =============================================================================
# 통합 프롬프트: 분석 + 수정안 생성 (LLM 1회 호출)
# =============================================================================
ANALYZE_AND_FIX_PROMPT = """당신은 Kubernetes 전문가이자 Helm values YAML 전문가입니다.
다음 K8s 이슈를 분석하고, 해결을 위해 Helm values 파일을 수정해주세요.

## 이슈 정보
- 타입: {type}
- 네임스페이스: {namespace}
- 리소스: {resource}
- 에러 메시지: {error_message}

## 로그
{logs}

## 현재 values 파일
파일: {target_file}
```yaml
{current_yaml}
```

## 요청사항
다음 형식으로 **정확하게** 응답해주세요:

근본 원인: [한 문장으로 핵심만 설명]

심각도: [critical/high/medium/low 중 하나]

해결책:
1. [핵심 해결 방법 한 줄]
2. [재발 방지 방법 한 줄]

```yaml
[전체 수정된 values YAML 내용]
```

변경 설명: [영어, 30자 이내, 예: "increase memory limit to 256Mi"]

**주의**:
- 기존 YAML 구조를 반드시 유지하면서 필요한 부분만 수정
- 주석 유지, 들여쓰기 정확하게 유지
- {resource} 서비스의 설정만 수정 (다른 서비스는 그대로 유지)
- kubectl 명령어를 포함하지 마세요 (GitOps 원칙: 변경은 Git을 통해서만)
- YAML 블록에는 반드시 전체 파일 내용을 포함해주세요
- 타입이 pod_crash/service_error/upstream_error/service_down 인 경우:
  - resources/limits/requests/memory/cpu 변경 금지
  - replicas, PodDisruptionBudget, timeout/retry/backoff/circuit-breaker 계열을 우선 사용
"""

# =============================================================================
# 분석 전용 프롬프트: values 파일이 없는 이슈용
# =============================================================================
ANALYZE_ONLY_PROMPT = """당신은 Kubernetes 전문가입니다.
다음 K8s 이슈를 분석하고 간결하게 해결책을 제시해주세요.

## 이슈 정보
- 타입: {type}
- 네임스페이스: {namespace}
- 리소스: {resource}
- 에러 메시지: {error_message}

## 로그
{logs}

## 요청사항
다음 형식으로 **간결하게** 응답해주세요:

근본 원인: [한 문장으로 핵심만 설명]

심각도: [critical/high/medium/low 중 하나]

해결책:
1. [즉시 조치: 핵심 해결 방법 한 줄]
2. [근본 해결: 재발 방지 방법 한 줄]
3. [모니터링: 추가 권장사항 한 줄]

**주의**:
- 각 해결책은 한 줄로 핵심만 작성
- kubectl 쓰기 명령(apply, patch, delete 등)은 포함하지 마세요
- 읽기 명령(get, describe, logs)만 참고용으로 포함 가능
"""

# =============================================================================
# 레거시 프롬프트 (하위 호환용, 새 워크플로우에서는 미사용)
# =============================================================================
ANALYZE_PROMPT = ANALYZE_ONLY_PROMPT

GENERATE_FIX_PROMPT = """당신은 Kubernetes YAML 전문가입니다.
이슈 분석 결과를 바탕으로 Helm values 파일을 수정해주세요.

## 이슈 정보
- 타입: {type}
- 네임스페이스: {namespace}
- 리소스: {resource}
- 에러: {error_message}

## 분석 결과
- 근본 원인: {root_cause}
- 심각도: {severity}

## 현재 values 파일 내용
파일: {target_file}
```yaml
{current_yaml}
```

## 요청사항
위 values 파일을 수정하여 이슈를 해결해주세요.

응답 형식:
```yaml
# 전체 수정된 YAML 내용
```

변경 설명: [50자 이내, 예: "frontend memory limit 128Mi → 256Mi"]

**주의**:
- 기존 YAML 구조를 유지하면서 필요한 부분만 수정
- 주석은 유지
- 들여쓰기 정확하게 유지
- resources.limits.memory, resources.requests 등 리소스 관련 값 수정
"""
