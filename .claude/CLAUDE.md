# DR-Kube 프로젝트 컨텍스트

## 프로젝트 개요

Kubernetes 이슈 자동 감지 → 분석 → PR 생성 → GitOps 복구 시스템

**목표일**: 2026년 2월 28일 (3월 전 완료)

## 시스템 플로우

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  이슈 발생   │ ──▶ │   알람 발생  │ ──▶ │ 에이전트 감지 │ ──▶ │  이슈 분류   │ ──▶ │  이슈 분석   │
└─────────────┘     │   (Slack)   │     └─────────────┘     └─────────────┘     └─────────────┘
                    └─────────────┘                                                     │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐             ▼
│  완료 알람   │ ◀── │  복구 검증   │ ◀── │ ArgoCD Sync │ ◀── │   PR 생성   │ ◀── ┌─────────────┐
│ (변경 내용)  │     └─────────────┘     └─────────────┘     └─────────────┘     │  수정안 생성  │
└─────────────┘                                                                  └─────────────┘
```

### 완료 알람 내용
```
✅ DR-Kube 복구 완료

📌 이슈: frontend-pod OOMKilled
🔍 원인: 메모리 limit 512Mi 초과
🔧 변경: resources.limits.memory 512Mi → 1Gi
📊 상태: Running (정상)
🔗 PR: https://github.com/org/repo/pull/123
```

## GitOps 원칙

> **⚠️ 중요: kubectl은 읽기 전용으로만 사용**

- 클러스터 변경은 **오직 Git을 통해서만** 수행
- 에이전트는 `values/*.yaml` 수정 → PR 생성 → ArgoCD가 동기화
- `kubectl apply`, `kubectl patch` 등 쓰기 명령 **금지**
- 허용: `kubectl get`, `kubectl describe`, `kubectl logs`

## 핵심 경로

```
dr-kube/
├── Makefile                # 프로젝트 명령어
├── scripts/
│   ├── setup.sh            # 클러스터 설치/삭제
│   ├── setup-agent.sh      # 에이전트 환경 설정
│   ├── setup-hosts.sh      # /etc/hosts 도메인 등록
│   ├── setup-tls.sh        # Let's Encrypt TLS 설정
│   ├── setup-secrets.sh    # SOPS + age 시크릿 관리
│   └── setup-slack.sh      # Slack webhook 설정
├── agent/
│   ├── cli.py              # CLI 진입점
│   ├── dr_kube/            # 메인 에이전트 코드 ⭐
│   │   ├── graph.py        # LangGraph 워크플로우
│   │   ├── llm.py          # LLM 프로바이더
│   │   ├── prompts.py      # 프롬프트 템플릿
│   │   ├── state.py        # 상태 정의
│   │   ├── github.py       # GitHub PR 생성
│   │   ├── webhook.py      # Alertmanager 웹훅 서버
│   │   └── converter.py    # Alert → Issue 변환
│   └── issues/             # 샘플 이슈 파일
├── secrets/
│   ├── secrets.yaml        # 평문 시크릿 (gitignored)
│   └── secrets.enc.yaml    # SOPS 암호화 (Git 커밋)
├── values/                 # Helm values (수정 대상)
├── chaos/                  # Chaos Mesh 실험 정의
└── docs/                   # 문서
```

## 팀 구성 및 역할

| 역할 | 인원 | 담당 | 상태 |
|------|------|------|------|
| 에이전트 | 3명 | LangGraph 워크플로우, PR 자동화 | ⏳ 진행 중 |
| 모니터링 | 2명 | 로그 수집, 알림 시스템 | ✅ 완료 |

**현실**: 팀원들이 회사 업무로 바빠서 참여가 어려움

### 모니터링 스택 (구축 완료)
| 도구 | 용도 | 상태 |
|------|------|------|
| Prometheus | 메트릭 수집 | ✅ |
| Loki | 로그 수집 | ✅ |
| Grafana | 대시보드/알람 | ✅ |
| Alloy | 로그/메트릭 수집기 | ✅ |
| Jaeger | 분산 추적 | ✅ |
| ArgoCD | GitOps 배포 | ✅ |
| Slack 알람 | 이슈 발생 알림 | ✅ |
| metrics-server | 실시간 CPU/메모리 | ✅ |
| Chaos Mesh | 장애 주입 테스트 | ✅ |
| cert-manager | TLS 인증서 자동화 | ✅ |

## 환경 설정

### 필수 조건
- NHN 클라우드 사용 불가 → **로컬 K8S 환경 필요**
- 로컬 K8S: **Kind** (Kubernetes in Docker)
- 5명의 일관성 유지를 위한 자동화 필요
- **크로스 플랫폼 지원**: Windows + WSL, macOS

### 지원 플랫폼

| 플랫폼 | 테스트 상태 | 비고 |
|--------|-------------|------|
| macOS (Intel/Apple Silicon) | ✅ | Docker Desktop 또는 Colima |
| Windows + WSL2 | ✅ | Ubuntu 22.04+ 권장 |
| Linux (Ubuntu/Debian) | ✅ | 네이티브 지원 |

### 로컬 환경 구축

```bash
# 원클릭 설치 (모든 플랫폼)
./scripts/setup.sh

# 개별 실행
./scripts/setup.sh cluster   # Kind 클러스터만
./scripts/setup.sh argocd    # ArgoCD 설치
./scripts/setup.sh apps      # 샘플 앱 배포
./scripts/setup.sh all       # 전체 설치

# 환경 삭제
./scripts/teardown.sh
```

### 테스트 환경 (Chaos Mesh + Online Boutique)

Chaos Mesh를 사용해 Online Boutique에 의도적으로 장애를 주입하여 에이전트 테스트

```bash
make chaos-memory       # Frontend OOM 실험 (3분)
make chaos-cpu          # CartService CPU 스트레스 (3분)
make chaos-network      # ProductCatalog 네트워크 지연 (3분)
make chaos-pod-kill     # CheckoutService Pod 강제 종료 (1분)
make chaos-stop         # 모든 실험 중지
make chaos-status       # 실험 상태 확인
```

| 시나리오 | 대상 | 발생 이슈 | 예상 수정 |
|----------|------|-----------|-----------|
| chaos-memory | frontend | OOMKilled | memory limit 증가 |
| chaos-cpu | frontend | CPU Throttling | cpu limit 증가 |
| chaos-network | frontend | 500ms 지연 | timeout 설정 조정 |
| chaos-pod-kill | frontend | CrashLoopBackOff | replicas/restart 정책 |

### 사전 요구사항

**macOS / Windows + WSL2** 모두 동일:
```bash
# 설정 스크립트가 Homebrew, make, uv를 자동 설치
./scripts/setup-agent.sh
```

### 시크릿 관리 (SOPS + age)

팀원 간 시크릿 공유를 위해 **SOPS + age** 암호화 사용.
암호화된 `secrets/secrets.enc.yaml`만 Git에 커밋, 평문은 gitignored.

```bash
# 팀 리더 (최초 1회)
make secrets-init        # age 키 생성 + .sops.yaml 업데이트
# → secrets/age.key를 팀원에게 Slack DM으로 공유

# 팀원
make secrets-import KEY=~/age.key   # 공유받은 키 가져오기
make secrets-decrypt                # 암호화 파일 → 평문 복호화

# 시크릿 수정 후
vi secrets/secrets.yaml             # 값 수정
make secrets-encrypt                # 평문 → 암호화 (Git 커밋 가능)

# 클러스터에 적용
make secrets-apply                  # K8s Secret 생성 + agent/.env 동기화
```

**관리 대상 시크릿:**
| 키 | 용도 | 적용 위치 |
|---|------|----------|
| `slack_webhook_url` | Alertmanager 알림 | monitoring/alertmanager-slack Secret |
| `cloudflare_api_token` | cert-manager DNS-01 | cert-manager/cloudflare-api-token Secret |
| `cloudflare_tunnel_token` | 외부 접근 터널 | cloudflare/cloudflare-tunnel-token Secret |
| `gemini_api_key` | LLM API 호출 | agent/.env (개인별 관리) |

> **agent/.env**는 `make secrets-apply`로 자동 생성됨. 단, `GEMINI_API_KEY`는 **개인별 관리** — 각자 agent/.env에 직접 입력

### 에이전트 환경 설정

```bash
# 프로젝트 루트에서 실행
make agent-setup         # uv + venv + 의존성 자동 설치
make secrets-apply       # agent/.env에 API 키 동기화
```

### 에이전트 실행
```bash
make agent-run           # 기본 이슈 분석
make agent-oom           # OOM 이슈 분석
make agent-cpu           # CPU Throttle 분석
make help                # 전체 명령어
```

## 워크플로우 상태

### 분석 모드 (`make agent-run`)
```
load_issue → analyze → suggest
```

### PR 생성 모드 (`make agent-fix`)
```
load_issue → analyze → generate_fix → create_pr
```

### 프로토타입 목표
```
load_issue → analyze → generate_fix → create_pr → notify (5노드)
```

| 노드 | 역할 | 구현 상태 |
|------|------|-----------|
| load_issue | 알람에서 이슈 로드 | ✅ 완료 |
| analyze | LLM 분석 | ✅ 완료 |
| generate_fix | YAML 수정안 생성 | ⏳ 구현됨, target file 매핑 수정 필요 |
| create_pr | GitHub PR 생성 | ⏳ 구현됨, 실테스트 필요 |
| notify | 완료 알람 (원인, diff, PR링크) | ❌ 미구현 |

### 프로토타입 이후 (스킵)
| 노드 | 역할 | 비고 |
|------|------|------|
| classify | 이슈 유형 분류 | 하드코딩으로 대체 |
| verify | 복구 확인 | 사람이 수동 확인 |
| [ArgoCD Sync] | GitOps 동기화 | 수동 sync |

## 도메인 & 접속

### 로컬 도메인 (hosts 파일)
```bash
make hosts              # /etc/hosts에 도메인 등록 (WSL/macOS/Linux)
make hosts-remove       # 도메인 제거
make hosts-status       # 접속 주소 확인
```

| 서비스 | 로컬 | 외부 |
|--------|------|------|
| Grafana | grafana.drkube.local | grafana.drkube.huik.site |
| Prometheus | prometheus.drkube.local | prometheus.drkube.huik.site |
| Alertmanager | alert.drkube.local | alert.drkube.huik.site |
| ArgoCD | argocd.drkube.local | argocd.drkube.huik.site |
| Boutique | boutique.drkube.local | boutique.drkube.huik.site |
| Chaos Mesh | chaos.drkube.local | chaos.drkube.huik.site |
| Jaeger | jaeger.drkube.local | jaeger.drkube.huik.site |

### TLS (HTTPS)
```bash
make tls                # cert-manager + Let's Encrypt 설정 (Cloudflare DNS-01)
make tls-status         # 인증서 상태 확인
```

## 우선순위 (프로토타입)

### P0 (필수)
1. `generate_fix` - YAML 수정안 생성 (⏳ 구현됨, target file 매핑 수정 필요)
2. `create_pr` - GitHub PR 자동 생성 (⏳ 구현됨, 테스트 필요)
3. `notify` - 완료 알람 (❌ 미구현)
4. ~~로컬 환경 스크립트 (Kind + ArgoCD)~~ ✅ 완료

### P1 (프로토타입 이후)
5. classify 노드
6. verify 노드
7. ArgoCD 자동 sync

### P2 (선택)
8. ~~Chaos Mesh 테스트~~ ✅ 완료
9. ~~Slack/Discord 알림~~ ✅ 완료 (Alertmanager → Slack)
10. 대시보드 UI

## 코딩 규칙

- Python 3.11+
- LangGraph 기반 워크플로우
- LLM: Ollama(로컬) 또는 Gemini 3.0 Flash
- 한글 주석/문서 사용

## AI 도구 사용 가이드

> 팀원들이 다양한 AI 도구 사용 중 (Claude Code, Cursor, Copilot Chat 등)
> 이 문서를 컨텍스트로 제공하여 일관성 유지

### 필수 컨텍스트
AI 도구 사용 시 아래 내용을 항상 전달:
1. **GitOps 원칙**: kubectl은 읽기 전용, 변경은 PR로만
2. **핵심 경로**: `agent/dr_kube/` 가 메인 코드
3. **프로토타입 범위**: `load_issue → analyze → generate_fix → create_pr → notify`

### 금지 사항
- `kubectl apply`, `kubectl patch` 등 클러스터 직접 수정 코드 생성 금지
- `values/*.yaml` 외 다른 경로에 K8S 리소스 생성 금지

## 자주 사용하는 명령어

```bash
# 클러스터
make setup              # Kind + ArgoCD + 전체 앱 설치
make teardown           # 클러스터 삭제
make hosts              # 로컬 도메인 등록

# 시크릿
make secrets-decrypt    # 시크릿 복호화
make secrets-apply      # K8s Secret + agent/.env 동기화

# 에이전트
make agent-setup        # 환경 설치
make agent-run          # 이슈 분석 (기본)
make agent-fix          # 분석 + PR 생성
make agent-webhook      # Alertmanager 웹훅 서버

# Chaos 테스트
make chaos-memory       # OOM 실험
make chaos-stop         # 실험 중지
make help               # 전체 명령어
```

## 참고 문서

- [ROADMAP.md](../docs/ROADMAP.md) - 주간별 상세 계획
- [agent/README.md](../agent/README.md) - 에이전트 사용법
