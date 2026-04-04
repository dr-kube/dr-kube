# DR-Kube Quick Start Guide

> Kubernetes 장애를 AI가 자동 분석 → PR 생성 → GitOps 복구까지 처리하는 시스템을 **20분 안에** 실행하고 테스트합니다.

---

## 📋 사전 요구사항

### 환경
- **OS**: macOS / Ubuntu 22.04+ / Windows WSL2
- **Docker**: 20.10+ (Docker Desktop 또는 Engine)
- **kubectl**: 자동 설치됨
- **메모리**: 최소 8GB (권장 16GB)
- **디스크**: 최소 30GB 여유

### 필수 계정 (사전 준비)
| 항목 | 용도 | 준비 |
|------|------|------|
| **GitHub** | PR 자동 생성 | `gh auth token` 발급 (GitHub CLI) |
| **Slack** | 장애 알림 + 승인 | Bot Token + 채널 ID |

> **GitHub Copilot Pro** 사용자는 `gh auth token`으로 무료 테스트 가능

---

## 🚀 설치 (5분)

### Step 1 — 클러스터 생성
```bash
cd dr-kube
make setup
```

내부 작업:
- Kind 로컬 K8s 클러스터 (control-plane 1 + worker 2)
- ArgoCD, Prometheus, Grafana, Loki, Tempo 설치
- Online Boutique (데모 마이크로서비스) 배포

### Step 2 — 시크릿 설정
```bash
# secrets/secrets.yaml 파일 편집
vi secrets/secrets.yaml
```

필수 값:
```yaml
slack_bot_token: "xoxb-..."
slack_channel: "C0XXXXXXX"
github_token: "ghp_xxxx..." # Fine-grained PAT
```

적용:
```bash
make secrets-decrypt    # SOPS 복호화
make secrets-apply      # K8s Secret + 환경 동기화
```

### Step 3 — 에이전트 Helm 배포
```bash
# 1. 이미지 빌드
docker build -t dr-kube-agent:local agent/
kind load docker-image dr-kube-agent:local --name dr-kube

# 2. Helm 설치
helm install dr-kube-agent charts/dr-kube-agent \
  --namespace monitoring \
  --set existingSecret=dr-kube-agent-secrets \
  --set image.repository=dr-kube-agent \
  --set image.tag=local \
  --set image.pullPolicy=Never \
  --set autoPR=true \
  --set llm.provider=copilot \
  --set ingress.enabled=true
```

**배포 확인:**
```bash
kubectl get pods -n monitoring -l app=dr-kube-agent
# dr-kube-agent-xxxxx   1/1   Running   0   1m
```

### Step 4 — 로컬 도메인 등록
```bash
make hosts
```

| 서비스 | URL |
|--------|-----|
| Online Boutique | http://boutique.drkube.local |
| Grafana | http://grafana.drkube.local |
| ArgoCD | http://argocd.drkube.local |

---

## 🧪 에이전트 테스트 (5분)

### 테스트 1 — 단일 알림
```bash
kubectl run -q test --rm -i --restart=Never --image=curlimages/curl -- curl -s -X POST \
  'http://dr-kube-agent.monitoring.svc:8081/webhook/alertmanager' \
  -H 'Content-Type: application/json' \
  -d '{
    "version":"4",
    "groupKey":"test-'$(date +%s)'",
    "status":"firing",
    "receiver":"agent-critical",
    "alerts":[{
      "status":"firing",
      "labels":{"alertname":"KubePodCrashLooping","severity":"critical","namespace":"online-boutique","pod":"cartservice"},
      "annotations":{"summary":"cartservice OOM","description":"Memory limit exceeded"},
      "startsAt":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "generatorURL":"http://prometheus:9090/graph"
    }]
  }'
```

응답: `{"status":"accepted",...}`

### 테스트 2 — 복수 알림
```bash
# 테스트 스크립트 실행
./test-agent.sh all

# 또는 개별 테스트
./test-agent.sh oom        # OOMKilled
./test-agent.sh cpu        # CPU Throttle
./test-agent.sh pending    # Pod Pending
```

### 테스트 결과 확인
```bash
# 실시간 로그
kubectl logs -n monitoring -l app=dr-kube-agent -c agent -f

# 특정 키워드 필터
kubectl logs -n monitoring -l app=dr-kube-agent -c agent | grep "처리\|Slack\|PR"
```

예상 로그:
```
[INFO] 처리 시작: alert-xxxxx (type=KubePodCrashLooping)
[INFO] [analyze_and_fix] LLM invoke done
[INFO] 근본 원인: cartservice 메모리 한도 초과
[INFO] Slack 제안 전송 완료: action_id=xxxxx
[INFO] 코파일럿 대기 중: action_id=xxxxx
```

---

## ✅ 전체 흐름 검증 (E2E Test)

### 1. Slack에서 버튼 클릭
설정한 Slack 채널에서:
```
DR-Kube 분석 완료

이슈: KubePodCrashLooping (cartservice)
원인: 메모리 128Mi 한도 초과
수정: resources.limits.memory 512Mi → 1Gi

[✅ PR 생성]  [✏️ 수정]  [❌ 무시]
```

**[✅ PR 생성]** 클릭 → 자동 PR 생성

### 2. GitHub PR 확인
```
https://github.com/<YOUR_ORG>/dr-kube/pull/NNN

수정 사항:
- values/online-boutique.yaml 변경
- cartservice memory limit 업데이트
```

### 3. PR Merge → 자동 복구
1. PR merge
2. ArgoCD가 변경 감지 (자동)
3. cartservice Pod 재시작
4. Slack 완료 알림

---

## 📊 Online Boutique 접속

### 로컬 (권장)
```
http://boutique.drkube.local
```

### 외부 (Cloudflare Tunnel)
```
https://boutique-drkube.huik.site
```

### 포트 포워드
```bash
kubectl port-forward -n online-boutique svc/frontend 8080:80
# http://localhost:8080
```

---

## 🔧 Helm 재설치

```bash
# 언인스톨
helm uninstall dr-kube-agent -n monitoring

# 재설치
helm install dr-kube-agent charts/dr-kube-agent \
  --namespace monitoring \
  --set existingSecret=dr-kube-agent-secrets \
  --set image.repository=dr-kube-agent \
  --set image.tag=local \
  --set image.pullPolicy=Never \
  --set autoPR=true \
  --set llm.provider=copilot \
  --set ingress.enabled=true
```

---

## 🧹 정리

```bash
make teardown        # Kind 클러스터 삭제
make hosts-remove    # /etc/hosts 제거
helm uninstall dr-kube-agent -n monitoring
```

---

## 📚 추가 정보

### Helm Chart 값 커스터마이징
```bash
helm install dr-kube-agent charts/dr-kube-agent \
  --namespace monitoring \
  --set autoPR=false \           # PR 자동 생성 비활성화
  --set llm.provider=gemini \    # Gemini 사용
  --set ingress.enabled=false    # Ingress 비활성화
```

### 디버깅
```bash
# 에이전트 상태
kubectl get pods -n monitoring -l app=dr-kube-agent
kubectl describe pod -n monitoring -l app=dr-kube-agent

# 웹훅 엔드포인트 확인
kubectl get svc -n monitoring dr-kube-agent
kubectl get endpoints -n monitoring dr-kube-agent

# Secret 확인
kubectl get secret -n monitoring dr-kube-agent-secrets -o yaml
```

---

## 🆘 문제 해결

### Pod가 Running 아님
```bash
kubectl describe pod -n monitoring -l app=dr-kube-agent
kubectl logs -n monitoring -l app=dr-kube-agent -c agent
```

### Slack 버튼 응답 없음
```bash
# Ingress 경로 테스트
kubectl run test --rm -i --restart=Never --image=curlimages/curl -- \
  curl -s -H 'Host: agent-drkube.huik.site' \
  'http://nginx-ingress-ingress-nginx-controller.ingress-nginx.svc/health'
```

### 알림 처리 안 됨
- Cost control cooldown 확인: 3시간 동안 같은 리소스는 1회만 처리
- 다른 `groupKey`로 재시도
- `kubectl logs -n monitoring -l app=dr-kube-agent -c agent | grep "쿨다운"`

---

**👉 다음: [Agent Architecture](../docs/ARCHITECTURE.md) 또는 [Troubleshooting](../docs/TROUBLESHOOTING.md)**
