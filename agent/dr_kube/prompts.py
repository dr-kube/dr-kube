"""프롬프트 템플릿"""

# =============================================================================
# LLM 수정안 생성 프롬프트: 분석 + YAML 수정 (LLM 1회 호출)
# {retry_context}: retry 시 이전 검증 오류를 주입 (빈 문자열이면 무시됨)
# =============================================================================
LLM_FIX_PROMPT = """당신은 Kubernetes 전문가이자 Helm values YAML 전문가입니다.
다음 K8s 이슈를 분석하고, 해결을 위해 Helm values 파일을 수정해주세요.
{retry_context}
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

심각도: [아래 기준 중 하나 선택]
  - critical: 서비스 전체 중단 (replicas=0, CrashLoopBackOff 전파, 결제/주문 불가)
  - high: 주요 기능 장애 (OOMKilled 반복, 지속적 재시작, 주요 서비스 응답 불가)
  - medium: 성능 저하 (CPU throttle, 높은 레이턴시, 간헐적 오류)
  - low: 경고 수준 (리소스 여유 부족, 단발성 이벤트, 자동 복구됨)

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

## 이슈 타입별 수정 가이드

- 타입이 oom 인 경우:
  - 먼저 logs를 보고 트래픽 급증(loadgenerator, 다수 서비스 동시 장애)이 원인인지 판단하세요
  - 트래픽 급증·카오스 유발 OOM이 의심되는 경우:
    - replicas 를 2로 증설 (단일 장애점 제거, 부하 분산)
    - memory limit은 현재값의 1.5배 수준으로 소폭 상향
    - livenessProbe.failureThreshold 를 5 이상으로 늘려 OOMKill 후 재기동 시간 확보
  - 순수 메모리 부족(점진적 증가)으로 판단되는 경우:
    - resources.limits.memory 를 현재값의 2배 수준으로 상향 (requests도 함께 조정)
- 타입이 cpu_throttle 인 경우:
  - resources.limits.cpu 를 현재값의 2배 수준으로 상향 (requests도 함께 조정)
  - replicas 도 함께 1 증설 (CPU 부하 분산)
- 타입이 pod_unhealthy 인 경우 (liveness/readiness probe 실패):
  - livenessProbe.initialDelaySeconds 를 30 이상으로 늘리세요 (앱 시작 시간 확보)
  - livenessProbe.timeoutSeconds 를 5 이상으로 늘리세요
  - livenessProbe.failureThreshold 를 5 이상으로 늘리세요
  - readinessProbe도 동일하게 조정
  - resources 수정은 하지 마세요
- 타입이 service_latency/nginx_latency 인 경우:
  - env 의 GRPC_TIMEOUT_MS 를 2000 이상으로 늘리세요
  - replicas 를 1 증설해 부하를 분산하세요
  - resources.limits 는 수정하지 마세요
- 타입이 container_waiting 인 경우 (환경변수/설정 오류로 시작 실패):
  - env 에서 누락되거나 잘못된 환경변수를 수정/추가하세요
  - resources 수정은 하지 마세요
- 타입이 replicas_mismatch 인 경우:
  - replicas 값을 목표 레플리카 수에 맞게 증가시키세요 (보통 2~3)
  - resources.requests 가 너무 작아 스케줄링 실패가 의심되면 함께 조정
- 타입이 pod_crash/service_error/upstream_error/service_down 인 경우:
  - resources/limits/requests/memory/cpu 변경 금지
  - replicas, PodDisruptionBudget, timeout/retry/backoff/circuit-breaker 계열을 우선 사용
- 타입이 composite_incident 인 경우 (복합 MSA 장애):
  - **반드시** 최소 2개 이상의 서로 다른 서비스에 걸친 독립 변경이 필요합니다
  - memory/cpu 리소스 단순 상향만으로 끝내는 것은 정책 위반입니다
  - 권장 변경 패턴 (logs에서 영향받은 서비스를 확인 후 선택):
    1. 프론트엔드 진입점 서비스: replicas 2로 증설 + livenessProbe.failureThreshold 5로 상향
    2. 연쇄 장애 원인 서비스(checkout/payment/catalog 등): replicas 2로 증설
    3. 의존 서비스 안정화: readinessProbe.failureThreshold 상향 또는 replicas 증설
  - 예시: frontend.replicas 1→2, checkoutservice.replicas 1→2, productcatalogservice.replicas 1→2
  - OOM이 포함된 경우에는 해당 서비스의 memory limit 소폭 상향(1.5배)을 추가해도 됩니다
  - 변경 설명(변경 설명: ...)은 "scale X services and adjust probes" 형식으로 간결하게 영어로 작성
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

심각도: [아래 기준 중 하나 선택]
  - critical: 서비스 전체 중단 (replicas=0, CrashLoopBackOff 전파, 결제/주문 불가)
  - high: 주요 기능 장애 (OOMKilled 반복, 지속적 재시작, 주요 서비스 응답 불가)
  - medium: 성능 저하 (CPU throttle, 높은 레이턴시, 간헐적 오류)
  - low: 경고 수준 (리소스 여유 부족, 단발성 이벤트, 자동 복구됨)

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
# ArgoCD 전용 분석 프롬프트: Sync 실패 / Health Degraded
# =============================================================================
ARGOCD_ANALYZE_PROMPT = """당신은 Argo CD와 Kubernetes GitOps 전문가입니다.
다음 Argo CD 이벤트를 분석하고 원인과 해결책을 제시해주세요.

## 이슈 정보
- 타입: {type}
- 네임스페이스: {namespace}
- 리소스(Application 이름): {resource}
- 에러 메시지: {error_message}

## 로그
{logs}

## 요청사항
- ArgoCD Sync 실패인 경우: 잘못된 YAML, 리소스 충돌, RBAC/권한 문제, 이미지/Helm 차트 오류 등을 고려해 근본 원인을 분석하세요.
- ArgoCD Health Degraded인 경우: Pod 장애, 리소스 부족, 헬스체크 실패, Readiness/Liveness 설정 등을 고려해 분석하세요.

다음 형식으로 **간결하게** 응답해주세요:

근본 원인: [한 문장으로 핵심만 설명]

심각도: [아래 기준 중 하나 선택]
  - critical: 서비스 전체 중단 (replicas=0, CrashLoopBackOff 전파, 결제/주문 불가)
  - high: 주요 기능 장애 (OOMKilled 반복, 지속적 재시작, 주요 서비스 응답 불가)
  - medium: 성능 저하 (CPU throttle, 높은 레이턴시, 간헐적 오류)
  - low: 경고 수준 (리소스 여유 부족, 단발성 이벤트, 자동 복구됨)

해결책:
1. [즉시 조치: 핵심 해결 방법 한 줄]
2. [근본 해결: 재발 방지 방법 한 줄]
3. [모니터링 또는 GitOps 관점 조치 한 줄]

**주의**:
- 각 해결책은 한 줄로 핵심만 작성
- kubectl 쓰기 명령은 포함하지 마세요. values/매니페스트 수정, 읽기 명령(get, describe, logs)만 참고용으로 포함 가능
"""

# =============================================================================
# PR 리뷰 피드백 프롬프트 (AGENT-2: Human-in-the-Loop)
# 리뷰어 댓글을 받아 수정안을 재생성할 때 사용
# =============================================================================
PR_REVIEW_RESPONSE_PROMPT = """당신은 Kubernetes 전문가이자 Helm values YAML 전문가입니다.
PR 리뷰어의 피드백을 반영하여 수정안을 재생성해주세요.

## 원본 이슈 정보
- 타입: {type}
- 네임스페이스: {namespace}
- 리소스: {resource}
- 에러 메시지: {error_message}

## 기존 수정안
파일: {target_file}
```yaml
{original_fix}
```

## 리뷰어 피드백
{pr_review_comment}

## 현재 values 파일 (원본)
```yaml
{current_yaml}
```

## 요청사항
리뷰어 피드백을 반드시 반영하여 YAML을 재생성해주세요.
다음 형식으로 응답해주세요:

근본 원인: [기존과 동일하거나 피드백 반영 시 수정]

심각도: [아래 기준 중 하나 선택]
  - critical: 서비스 전체 중단 (replicas=0, CrashLoopBackOff 전파, 결제/주문 불가)
  - high: 주요 기능 장애 (OOMKilled 반복, 지속적 재시작, 주요 서비스 응답 불가)
  - medium: 성능 저하 (CPU throttle, 높은 레이턴시, 간헐적 오류)
  - low: 경고 수준 (리소스 여유 부족, 단발성 이벤트, 자동 복구됨)

해결책:
1. [피드백을 반영한 핵심 해결 방법]
2. [재발 방지 방법]

```yaml
[피드백이 반영된 전체 수정된 values YAML 내용]
```

변경 설명: [영어, 30자 이내]

**주의**:
- 리뷰어 피드백의 요청사항을 빠짐없이 반영
- GitOps 원칙 준수: kubectl 명령어 포함 금지
- 전체 파일 내용을 YAML 블록에 포함
"""
