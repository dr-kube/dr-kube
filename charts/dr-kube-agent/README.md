# DR-Kube Agent Helm Chart

Kubernetes 이슈를 자동으로 감지하고, LLM으로 분석한 뒤, GitOps PR을 생성하여 복구하는 에이전트입니다.

```
Alert 발생 → Webhook 수신 → LLM 분석 → YAML 수정안 생성 → PR 생성 → ArgoCD Sync → 복구 검증
```

## 사전 요구사항

| 항목 | 필수 | 설명 |
|------|:----:|------|
| Kubernetes | O | 1.25+ |
| Helm | O | 3.x |
| ArgoCD | O | GitOps 동기화용 (클러스터에 설치 필요) |
| GitHub 레포 | O | `values/*.yaml`을 포함한 GitOps 레포 (에이전트가 PR 생성) |
| GitHub Token | O | 레포 clone + PR 생성 권한 (repo 스코프) |
| LLM API 키 | O | GitHub Copilot / Gemini / Ollama 중 택 1 |
| Slack App | - | Human-in-the-Loop 사용 시 필요 (없으면 `autoPR: true`로 자동 처리) |
| Alertmanager | - | 알림 자동 수신 시 필요 (없으면 CLI로 수동 실행 가능) |

## 빠른 시작 (외부 사용자)

### Step 1. 레포 구조 준비

에이전트가 PR을 생성할 GitOps 레포에 `values/` 디렉토리가 필요합니다:

```
my-gitops-repo/
└── values/
    ├── my-app.yaml          # Helm values (에이전트가 수정하는 대상)
    └── prometheus.yaml      # 모니터링 values 등
```

에이전트는 Alert에서 리소스 이름을 추출하고, `values/` 아래에서 해당 파일을 찾아 수정안을 생성합니다.

### Step 2. Helm 차트 설치

```bash
# OCI 레지스트리에서 직접 설치
helm install dr-kube oci://ghcr.io/dr-kube/charts/dr-kube-agent \
  --namespace monitoring --create-namespace \
  --set github.repoUrl="https://github.com/<your-org>/<your-repo>.git" \
  --set secrets.githubToken="ghp_xxxx" \
  --set secrets.copilotToken="gho_xxxx" \
  --set secrets.slackBotToken="xoxb-xxxx" \
  --set secrets.slackChannel="C0XXXXXXX"
```

또는 values 파일을 만들어서:

```bash
cat <<EOF > my-values.yaml
github:
  repoUrl: "https://github.com/my-org/my-repo.git"

secrets:
  githubToken: "ghp_xxxx"
  copilotToken: "gho_xxxx"
  slackBotToken: "xoxb-xxxx"
  slackChannel: "C0XXXXXXX"

# Slack 없이 자동 PR 생성 모드
# autoPR: true
# llm:
#   copilotMode: false
EOF

helm install dr-kube oci://ghcr.io/dr-kube/charts/dr-kube-agent \
  --namespace monitoring --create-namespace \
  -f my-values.yaml
```

### Step 3. Alertmanager 연동

Alertmanager가 에이전트로 알림을 보내도록 webhook receiver를 설정합니다:

```yaml
# Alertmanager config에 추가
receivers:
  - name: dr-kube
    webhook_configs:
      - url: "http://dr-kube-dr-kube-agent.monitoring.svc:8081/webhook/alertmanager"
        send_resolved: false

route:
  routes:
    - receiver: dr-kube
      matchers:
        - severity=~"critical|warning"
```

### Step 4. 설치 확인

```bash
# Pod 상태
kubectl get pods -n monitoring -l app.kubernetes.io/name=dr-kube-agent

# 로그
kubectl logs -n monitoring -l app.kubernetes.io/name=dr-kube-agent -f

# 헬스체크
kubectl exec -n monitoring deploy/dr-kube-dr-kube-agent -- curl -s localhost:8081/health
```

## 시크릿 획득 방법

| 키 | 획득 방법 |
|----|----------|
| `githubToken` | GitHub Settings → Developer settings → Personal access tokens → `repo` 스코프 |
| `copilotToken` | `gh auth token` (GitHub Copilot Pro 구독 + copilot 스코프 필요) |
| `slackBotToken` | [Slack API](https://api.slack.com/apps) → Create App → OAuth & Permissions → Bot Token (`xoxb-...`) |
| `slackChannel` | Slack 채널 우클릭 → 채널 세부정보 → 하단 채널 ID (`C0...`) |

> Slack 앱에 필요한 Bot Token Scopes: `chat:write`, `files:write`, `reactions:read`

### 기존 Secret 사용

이미 클러스터에 Secret이 있으면 직접 참조할 수 있습니다:

```bash
# Secret 생성
kubectl create secret generic my-agent-secrets \
  --namespace monitoring \
  --from-literal=copilot-token="gho_xxxx" \
  --from-literal=github-token="ghp_xxxx" \
  --from-literal=slack-bot-token="xoxb-xxxx" \
  --from-literal=slack-channel="C0XXXXXXX"

# 차트에서 참조
helm install dr-kube oci://ghcr.io/dr-kube/charts/dr-kube-agent \
  --namespace monitoring \
  --set existingSecret=my-agent-secrets \
  --set github.repoUrl="https://github.com/my-org/my-repo.git"
```

## Slack 없이 사용하기

Slack 연동 없이 자동 모드로 운영할 수 있습니다:

```yaml
autoPR: true          # Alert → 자동 PR 생성 (승인 없이)
llm:
  copilotMode: false  # Slack 제안 단계 건너뛰기
```

이 경우 `slackBotToken`과 `slackChannel`은 빈 값으로 두면 됩니다.

## 로컬 개발 (Kind)

레포를 clone해서 로컬에서 빌드/테스트하려는 경우:

```bash
git clone https://github.com/dr-kube/dr-kube.git
cd dr-kube

# 이미지 빌드 + Kind 로드
docker build -t dr-kube-agent:local ./agent
kind load docker-image dr-kube-agent:local --name dr-kube

# 로컬 이미지로 설치
helm install dr-kube charts/dr-kube-agent/ \
  --namespace monitoring --create-namespace \
  --set image.repository=dr-kube-agent \
  --set image.tag=local \
  --set image.pullPolicy=Never \
  -f my-values.yaml
```

## 전체 설정값 레퍼런스

### 이미지

| 파라미터 | 설명 | 기본값 |
|----------|------|--------|
| `image.repository` | 컨테이너 이미지 | `ghcr.io/dr-kube/dr-kube-agent` |
| `image.tag` | 이미지 태그 | `latest` |
| `image.pullPolicy` | 풀 정책 | `IfNotPresent` |

### GitHub

| 파라미터 | 설명 | 기본값 |
|----------|------|--------|
| `github.repoUrl` | PR 대상 레포 URL | `https://github.com/dr-kube/dr-kube.git` |
| `github.botName` | 커밋 작성자 이름 | `dr-kube-agent[bot]` |
| `github.botEmail` | 커밋 작성자 이메일 | `dr-kube-agent@users.noreply.github.com` |

### LLM

| 파라미터 | 설명 | 기본값 |
|----------|------|--------|
| `llm.provider` | LLM 프로바이더 (`copilot` / `github` / `gemini` / `ollama`) | `copilot` |
| `llm.copilotModel` | 사용할 모델 | `gpt-5.3-codex` |
| `llm.copilotMode` | Slack Human-in-the-Loop | `true` |

### 비용 제어

| 파라미터 | 설명 | 기본값 |
|----------|------|--------|
| `cost.mode` | `normal` / `high` | `normal` |
| `cost.maxLLMCallsPerDay` | 일일 LLM 호출 상한 | `20` |
| `cost.dedupCooldownMinutes` | 동일 알림 중복 방지 (분) | `60` |
| `cost.prGroupCooldownMinutes` | PR 그룹핑 윈도우 (분) | `180` |
| `cost.maxIssuesPerWebhookWithPR` | 웹훅당 PR 생성 이슈 수 | `1` |
| `cost.compositeIncidentMode` | 복합 장애 처리 모드 | `true` |

### 워처

| 파라미터 | 설명 | 기본값 |
|----------|------|--------|
| `watcher.enabled` | K8s 리소스 변경 감지 | `true` |
| `watcher.namespaces` | 감시 대상 네임스페이스 (쉼표 구분) | `online-boutique` |

### Ingress

| 파라미터 | 설명 | 기본값 |
|----------|------|--------|
| `ingress.enabled` | Ingress 생성 여부 | `false` |
| `ingress.className` | IngressClass | `nginx` |
| `ingress.host` | 외부 도메인 | `agent-drkube.huik.site` |
| `ingress.tls.enabled` | TLS 활성화 | `true` |
| `ingress.tls.secretName` | TLS Secret 이름 | `dr-kube-agent-tls` |

### 기타

| 파라미터 | 설명 | 기본값 |
|----------|------|--------|
| `replicaCount` | 레플리카 수 | `1` |
| `autoPR` | Slack 승인 없이 자동 PR | `false` |
| `checkpoints.hostPath` | LangGraph 체크포인트 경로 | `/var/dr-kube/checkpoints` |
| `rbac.create` | RBAC 리소스 생성 | `true` |
| `serviceAccount.create` | ServiceAccount 생성 | `true` |
| `existingSecret` | 기존 Secret 이름 (빈 값이면 자동 생성) | `""` |

## 업그레이드 / 삭제

```bash
# 업그레이드
helm upgrade dr-kube oci://ghcr.io/dr-kube/charts/dr-kube-agent \
  --namespace monitoring -f my-values.yaml

# 삭제
helm uninstall dr-kube --namespace monitoring
```

## 아키텍처

```
                    ┌──────────────────────────────┐
                    │        dr-kube-agent Pod      │
┌──────────┐       │                               │
│Alertmanager├─────▶│  POST /webhook/alertmanager   │
└──────────┘       │         │                     │
                    │         ▼                     │
┌──────────┐       │  LangGraph Workflow            │
│  Slack   │◀─────▶│  load → analyze → validate    │
│  (승인)   │       │         │                     │
└──────────┘       │         ▼                     │
                    │  GitHub PR 생성               │
                    │         │                     │
                    └─────────┼─────────────────────┘
                              ▼
                    ┌──────────────────┐
                    │  ArgoCD Sync     │
                    │  → 클러스터 반영  │
                    └──────────────────┘
```

## 지원하는 Alert 타입

| Alert Rule | 이슈 타입 | 설명 |
|------------|----------|------|
| ContainerOOMKilled | `oom` | 컨테이너 메모리 초과 |
| HighMemoryUsage | `oom` | 메모리 사용량 임계치 |
| CPUThrottling | `cpu_throttle` | CPU 쓰로틀링 |
| PodCrashLooping | `pod_crash` | Pod 반복 재시작 |
| PodNotReady | `pod_unhealthy` | Pod 준비 안 됨 |
| ServiceHighErrorRate | `service_error` | 서비스 에러율 급증 |
| ServiceDown | `service_down` | 서비스 다운 |
| UpstreamConnectionError | `upstream_error` | 업스트림 연결 실패 |
| DeploymentReplicasMismatch | `replicas_mismatch` | 레플리카 수 불일치 |

## 트러블슈팅

**Pod이 CrashLoopBackOff**

```bash
kubectl logs -n monitoring -l app.kubernetes.io/name=dr-kube-agent --previous
```

- `GITHUB_TOKEN` 확인 — 레포 clone 권한 필요 (`repo` 스코프)
- Secret 키 이름 확인 — `copilot-token`, `slack-bot-token`, `slack-channel`, `github-token`

**Alertmanager 웹훅이 안 옴**

```bash
# 서비스 접근 확인
kubectl exec -n monitoring deploy/prometheus-server -- \
  wget -qO- http://dr-kube-dr-kube-agent.monitoring.svc:8081/health
```

- Alertmanager config의 URL에서 `<release>-dr-kube-agent` 형식 확인
- NetworkPolicy가 네임스페이스 간 통신을 차단하는지 확인

**LLM 호출 제한 도달**

에이전트 로그에 `daily LLM call limit reached`가 보이면:

```bash
# 일일 호출 제한 늘리기
helm upgrade dr-kube oci://ghcr.io/dr-kube/charts/dr-kube-agent \
  --namespace monitoring --reuse-values \
  --set cost.maxLLMCallsPerDay=50
```

**이미지 Pull 실패 (ErrImagePull)**

```bash
# GHCR 이미지가 public인지 확인, 아니면 imagePullSecrets 설정
kubectl create secret docker-registry ghcr-secret \
  --namespace monitoring \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<github-pat>
```
