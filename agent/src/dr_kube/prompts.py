"""프롬프트 템플릿"""

ANALYZE_PROMPT = """당신은 Kubernetes 전문가입니다.
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

실행 계획:
```bash
# 즉시 적용 가능한 kubectl 명령어 (주석 포함)
kubectl patch deployment {resource} -n {namespace} -p '...'
```

YAML 수정:
```yaml
# 수정이 필요한 부분만 표시 (Before → After)
spec:
  template:
    spec:
      containers:
      - name: app
        resources:
          limits:
-           memory: 512Mi  # Before
+           memory: 1Gi     # After (권장)
```

**주의**:
- 각 해결책은 한 줄로 핵심만 작성
- 실행 계획은 실제 적용 가능한 명령어만 작성
- YAML은 변경이 필요한 부분만 diff 형식으로 표시
"""
