"""LLM 프롬프트 템플릿"""

ANALYZE_PROMPT = """당신은 Kubernetes 장애 분석 전문가입니다.
delivery-app MSA의 장애를 분석하고 근본 원인을 파악하세요.

## 서비스 아키텍처
- frontend (nginx): API gateway, 모든 외부 트래픽 진입점
- order-service (FastAPI :8000): 주문 생성/조회, menu-service + delivery-service 호출
- menu-service (FastAPI :8001): 레스토랑/메뉴 데이터 (인메모리)
- delivery-service (FastAPI :8002): 배달 상태 추적

## 이슈 정보
- 이슈 타입: {issue_type}
- 영향 서비스: {affected_service}
- 에러 메시지: {error_message}

## 수집된 컨텍스트

### Pod 로그
{pod_logs}

### Pod 상태 및 재시작 횟수
{pod_status}

### K8s 이벤트
{pod_events}

### Prometheus 메트릭
{metrics}

## 지시사항
1. 근본 원인을 명확하게 분석하세요
2. 연쇄 영향 서비스를 파악하세요
3. 심각도를 판단하세요 (critical/high/medium/low)
4. 자동 수정 가능 여부를 판단하세요

반드시 JSON 형식으로 응답하세요.
"""

PLAN_FIX_PROMPT = """당신은 Kubernetes manifest 수정 전문가입니다.
분석 결과를 바탕으로 delivery-app의 장애를 해결하는 manifest 수정안을 생성하세요.

## GitOps 원칙 (필수 준수)
- kubectl apply/patch 절대 금지 — Git PR을 통해서만 변경
- 수정 대상: manifests/delivery-app/{{service}}.yaml

## 이슈 정보
- 이슈 타입: {issue_type}
- 영향 서비스: {affected_service}
- 근본 원인: {root_cause}
- 심각도: {severity}

## 현재 manifest
```yaml
{current_manifest}
```

## 수정 전략: {strategy}
{strategy_guidance}

## 이전 시도 실패 사유 (있는 경우)
{previous_errors}

## 사용자 요청 (있는 경우)
{human_comment}

## 허용된 변경 필드
{allowed_fields}

## 지시사항
1. 최소한의 변경으로 문제를 해결하세요
2. 수정된 전체 Deployment YAML을 반환하세요
3. 변경된 필드 경로를 명시하세요
4. 변경 근거를 한국어로 설명하세요

반드시 JSON 형식으로 응답하세요.
"""

STRATEGY_GUIDANCE = {
    "conservative": "가장 보수적인 최소 변경만 적용하세요. 예: memory limit 1.5배 증가, replicas 1개 추가",
    "moderate": "보수적 변경 + 안정성 보완. 예: memory 2배 + readinessProbe 임계값 완화",
    "aggressive": "문제 해결에 필요한 더 큰 변경. 예: memory 3배 + CPU limit 증가 + replicas 증설",
}
