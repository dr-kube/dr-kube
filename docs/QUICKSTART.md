# DR-Kube Quick Start Guide

> Kubernetes 장애를 AI가 자동 분석 → PR 생성 → GitOps 복구까지 처리하는 시스템을 15분 안에 직접 실행해봅니다.

---

## 1. 사전 요구사항

### 최소 환경

| 항목 | 최소 | 권장 |
|------|------|------|
| CPU | 4코어 | 8코어 |
| 메모리 | 8GB | 16GB |
| 디스크 | 20GB 여유 | 40GB |
| OS | macOS / Ubuntu 22.04+ / Windows WSL2 | - |
| Kubernetes | 자동 설치 (Kind v1.31) | - |

### 필수 계정 (설치 전 준비)

| 서비스 | 용도 | 준비 사항 |
|--------|------|----------|
| **GitHub** | PR 자동 생성 | 계정 + [Fine-grained PAT](#github-token-발급) |
| **Slack** | 장애 알림 + 승인 버튼 | 워크스페이스 + [Bot Token](#slack-app-설정) |
| **Gemini API** | AI 분석 엔진 | [무료 API 키](https://aistudio.google.com/apikey) |

> **GitHub Copilot Pro** 사용자라면 Gemini 대신 Copilot 토큰(`gh auth token`)을 사용할 수 있습니다.

### 필수 도구 (1개만 있으면 됨)

```bash
# Docker만 설치되어 있으면 나머지는 자동 설치됩니다
docker --version   # Docker Desktop 또는 Engine 20+
git --version
```

---

## 2. 설치 (5분)

### Step 1 — 레포지토리 Fork & Clone

```bash
# 1. GitHub에서 이 레포를 본인 계정으로 Fork
#    (에이전트가 수정안 PR을 본인 레포에 올려야 합니다)

# 2. Fork한 레포를 클론
git clone https://github.com/<YOUR_ORG>/dr-kube.git
cd dr-kube
```

### Step 2 — 클러스터 + 전체 스택 설치

```bash
make setup
```

내부적으로 실행되는 작업:
- Kind(로컬 K8s) 클러스터 생성 (control-plane 1 + worker 2)
- ArgoCD 설치 및 App of Apps 등록
- Prometheus, Grafana, Loki, Tempo, Pyroscope, Alloy 설치
- Online Boutique (10개 마이크로서비스 데모 앱) 배포
- Chaos Mesh 설치

> 소요 시간: 약 3~5분 (최초 이미지 풀 시 더 걸릴 수 있습니다)

**설치 확인:**
```bash
kubectl get pods -n monitoring   # prometheus, grafana 등 Running 확인
kubectl get pods -n argocd       # argocd-server Running 확인
kubectl get pods -n online-boutique  # 10개 서비스 Running 확인
```

모든 Pod이 `Running` 상태이면 성공입니다.

### Step 3 — 로컬 도메인 등록

```bash
make hosts
```

`/etc/hosts`에 아래 도메인이 자동 등록됩니다:

| 서비스 | 주소 |
|--------|------|
| Grafana | http://grafana.drkube.local |
| ArgoCD | http://argocd.drkube.local |
| Online Boutique (데모 앱) | http://boutique.drkube.local |
| Prometheus | http://prometheus.drkube.local |
| Alertmanager | http://alert.drkube.local |

브라우저에서 http://grafana.drkube.local 접속 → Grafana 화면이 뜨면 성공.

### Step 4 — 시크릿 설정

`secrets/secrets.yaml` 파일을 열어 값을 입력합니다:

```bash
vi secrets/secrets.yaml
```

```yaml
# 필수 항목만 채우면 됩니다
slack_bot_token: "xoxb-..."          # Slack Bot Token
slack_channel: "C0XXXXXXX"           # Slack 채널 ID (아래 안내 참고)
github_token: "github_pat_..."       # GitHub PAT (아래 안내 참고)
gemini_api_key: "AIza..."            # Gemini API Key (aistudio.google.com)

# 아래는 선택 사항 (외부 접근 불필요하면 비워두세요)
slack_webhook_url: ""
cloudflare_api_token: ""
cloudflare_tunnel_token: ""
```

입력 후 K8s Secret 적용:

```bash
make secrets-apply
```

### Step 5 — 에이전트 이미지 빌드 및 배포

```bash
# 에이전트 이미지 빌드 + Kind 클러스터에 로드
docker build -t dr-kube-agent:local agent/
kind load docker-image dr-kube-agent:local --name dr-kube

# K8s에 배포
kubectl apply -f manifests/dr-kube-agent/deployment.yaml
```

**배포 확인:**
```bash
kubectl get pods -n monitoring -l app=dr-kube-agent
# dr-kube-agent-xxxxx   1/1   Running   0   30s
```

`1/1 Running` 상태이면 설치 완료입니다.

### 삭제 방법

```bash
make teardown        # Kind 클러스터 전체 삭제
make hosts-remove    # /etc/hosts 도메인 제거
```

---

## 3. 첫 번째 시나리오 — 장애 감지 → AI 분석 → PR 생성 (10분)

설치 직후 바로 실행할 수 있는 시나리오입니다.
Online Boutique의 `frontend` 서비스를 강제로 다운시키고, DR-Kube가 자동으로 감지 → 분석 → Slack 알림 → PR 생성하는 전체 흐름을 확인합니다.

### 시나리오 실행

```bash
make test-watcher
```

내부적으로 다음을 수행합니다:
1. `frontend` Deployment를 replicas=0으로 스케일 다운 (강제 장애 주입)
2. Watcher가 변화를 감지 (약 5초)
3. LLM이 근본 원인 분석 + YAML 수정안 생성 (약 20초)
4. Slack에 `[PR 생성] [수정 요청] [무시]` 버튼 전송

**예상 로그 출력:**
```
=== watcher e2e 테스트 시작 ===
1. frontend 정상화 (replicas=1)...
2. frontend 강제 다운 (replicas=0) — watcher 감지 트리거...
3. 에이전트 로그 확인...

[워처] 수상한 변경: Deployment/frontend — replicas 1 → 0 (강제 다운)
[워처] dr_kube 에이전트 라우팅: online-boutique/frontend (MODIFIED)
[analyze_and_fix] DONE root_cause=frontend Deployment의 replicas 값이 0으로 변경...
Slack 제안 전송 완료: action_id=XXXXXXXX

=== Slack 채널에서 [PR 생성] 버튼 확인 후 make test-approve ACTION_ID=<id> 실행 ===
```

### Slack에서 승인하거나 자동 테스트

**옵션 A — Slack 버튼 직접 클릭**
설정한 Slack 채널에서 아래와 같은 메시지를 확인하고 `[PR 생성]` 버튼을 클릭합니다.

```
DR-Kube 분석 완료 🔍

이슈: replicas_mismatch (frontend)
원인: frontend Deployment의 replicas 값이 0으로 변경...
수정안: frontend.replicas를 1로 고정

[✅ PR 생성]  [✏️ 수정 요청]  [❌ 무시]
```

**옵션 B — 커맨드라인에서 시뮬레이션**
Slack 없이도 테스트 가능합니다. 로그에서 `action_id` 를 확인 후:

```bash
make test-approve ACTION_ID=XXXXXXXX
```

### 결과 확인

```
PR 생성 시작: action_id=XXXXXXXX issue=watcher-XXXXXX
[create_pr] DONE pr_url=https://github.com/<YOUR_ORG>/dr-kube/pull/1
PR 생성 완료: https://github.com/<YOUR_ORG>/dr-kube/pull/1
```

GitHub에서 PR이 생성된 것을 확인합니다. PR에는:
- 감지된 이슈 설명
- LLM이 생성한 `values/online-boutique.yaml` 수정 내용
- 변경 이유 요약

이 PR을 머지하면 ArgoCD가 자동으로 동기화하여 서비스가 복구됩니다.

### 정상화

```bash
make test-watcher-reset   # frontend replicas=1 복구
```

---

## 4. 더 복잡한 장애 시나리오

설치 직후 바로 실행 가능한 복합 장애 트랙 3가지:

```bash
# Redis → Payment → Checkout 연쇄 장애
make chaos-track-checkout-cascade

# ProductCatalog DNS 실패 + Frontend 과부하
make chaos-track-catalog-break

# 플랫폼 전반 성능 저하 (Brownout)
make chaos-track-platform-brownout

# 실험 종료
make chaos-stop
```

Grafana (http://grafana.drkube.local)에서 실시간으로 알림 발화 → 에이전트 분석 → PR 생성 흐름을 관측할 수 있습니다.

---

## 부록 — 토큰 발급 방법

### GitHub Token 발급

1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. **Repository access**: Fork한 `dr-kube` 레포 선택
3. **Permissions**:
   - Contents: Read and write
   - Pull requests: Read and write
4. 생성된 토큰을 `secrets/secrets.yaml`의 `github_token`에 입력

### Slack App 설정

1. https://api.slack.com/apps → **Create New App** → From scratch
2. App Name: `DR-Kube`, 워크스페이스 선택
3. **OAuth & Permissions** → Bot Token Scopes 추가:
   - `chat:write`, `chat:write.public`
4. **Install to Workspace** → Bot User OAuth Token 복사 → `slack_bot_token`에 입력
5. **Interactivity & Shortcuts** → Request URL 입력:
   - 로컬: `https://<your-tunnel-url>/webhook/slack/action` (ngrok 등)
   - 클러스터: `https://agent-drkube.<your-domain>/webhook/slack/action`
6. Slack 채널에 앱 초대: `/invite @DR-Kube`
7. 채널 ID 확인: 채널 우클릭 → 채널 세부정보 → 하단 ID 복사 → `slack_channel`에 입력

---

## 5. 다음 단계

| 목적 | 안내 |
|------|------|
| 기존 K8s 클러스터에 연동 | 에이전트만 별도 배포 가능 (values 파일 경로 커스터마이징 필요) |
| 프로덕션 적용 / PoC 미팅 | contact@cloudbro.ai |
| 아키텍처 상세 | [docs/ARCHITECTURE.md](./ARCHITECTURE.md) |
| 전체 명령어 | `make help` |

> 프로덕션 환경 적용, 커스텀 Alert Rule 연동, 기존 GitOps 파이프라인 통합이 필요하시면
> **contact@cloudbro.ai** 로 문의주세요.
