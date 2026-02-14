# DR-Kube

> **D**isaster **R**ecovery for **Kube**rnetes - AI 기반 Kubernetes 장애 자동 복구 시스템

[![ArgoCD](https://img.shields.io/badge/ArgoCD-GitOps-blue?logo=argo)](https://argoproj.github.io/cd/)
[![LangGraph](https://img.shields.io/badge/LangGraph-AI%20Agent-green?logo=langchain)](https://langchain-ai.github.io/langgraph/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Container%20Orchestration-326CE5?logo=kubernetes)](https://kubernetes.io/)

## 개요

DR-Kube는 Kubernetes 클러스터에서 발생하는 장애를 **자동으로 감지, 분석, 복구**하는 AI 기반 시스템입니다.

```
이슈 발생 → Prometheus 알림 → Alertmanager → 에이전트 분석 → PR 생성 → ArgoCD Sync → 복구 완료
                                    ↓
                              Slack 알림 (장애 발생)                    ArgoCD Notifications (복구 완료)
```

### 주요 기능

- **자동 장애 감지**: Prometheus 알림 → Alertmanager → 에이전트 웹훅
- **AI 기반 분석**: LLM(Gemini/Ollama)을 활용한 근본 원인 분석 + YAML 수정안 생성
- **GitOps 자동 복구**: values YAML 수정 → PR 생성 → ArgoCD 동기화
- **Human-in-the-Loop**: PR 댓글로 피드백 → 에이전트가 수정안 재생성
- **통합 관측성**: Grafana + Prometheus + Loki + Tempo + Pyroscope (MELT 4가지 시그널)
- **카오스 엔지니어링**: Chaos Mesh를 통한 복합 장애 시뮬레이션

## 아키텍처

```
┌──────────────────────────────────────────────────────────────────────┐
│                           DR-Kube System                             │
│                                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐         │
│  │ Grafana  │◄──│Prometheus│◄──│  Alloy   │◄──│ K8s      │         │
│  │Dashboard │   │ + Alert  │   │(Collector│   │ Cluster  │         │
│  │ Drilldown│   └────┬─────┘   └──────────┘   └──────────┘         │
│  └──┬───┬───┘        │                                               │
│     │   │       ┌────▼─────┐                                         │
│  ┌──▼┐ ┌▼──┐   │Alertmgr  │                                         │
│  │Loki│ │Tem│   │→ Slack   │                                         │
│  │Log │ │po │   │→ Webhook │                                         │
│  └────┘ │Tra│   └────┬─────┘                                         │
│  ┌────┐ │ce │        │                                               │
│  │Pyro│ └───┘   ┌────▼──────────────────────┐   ┌──────────┐        │
│  │scop│         │    LangGraph Agent         │   │  ArgoCD  │        │
│  │e   │         │ load → analyze+fix → PR ───┼──▶│  GitOps  │        │
│  └────┘         │      ↑  validate ↓ (retry) │   │  + Notif │→ Slack │
│                 │      └───────────┘         │   └──────────┘        │
│  trace ID 기반 드릴다운:                       │                        │
│  Traces → Logs → Metrics → Profiles          │                        │
└──────────────────────────────────────────────────────────────────────┘
```

## 프로젝트 구조

```
dr-kube/
├── applications/             # ArgoCD Application 정의 (App of Apps)
│   ├── alloy.yaml
│   ├── argocd.yaml
│   ├── cert-manager.yaml
│   ├── chaos-mesh.yaml
│   ├── grafana.yaml
│   ├── jaeger.yaml
│   ├── loki.yaml
│   ├── metrics-server.yaml
│   ├── nginx-ingress.yaml
│   ├── online-boutique.yaml
│   └── prometheus.yaml
├── values/                   # Helm Values 파일
│   ├── alloy.yaml            # 로그/메트릭 수집 파이프라인
│   ├── argocd.yaml
│   ├── cert-manager.yaml
│   ├── chaos-mesh.yaml
│   ├── grafana.yaml          # 데이터소스 (Prometheus/Loki/Tempo/Pyroscope) + 대시보드
│   ├── loki.yaml             # 로그 집계 (SingleBinary)
│   ├── metrics-server.yaml
│   ├── nginx-ingress.yaml
│   ├── online-boutique.yaml  # 데모 앱 (10 마이크로서비스)
│   ├── prometheus.yaml       # Alert rules + Alertmanager 설정
│   ├── pyroscope.yaml        # Continuous Profiling
│   └── tempo.yaml            # 분산 트레이싱 + span metrics
├── manifests/
│   ├── application-root.yaml # Root Application (App of Apps)
│   └── online-boutique/
│       └── ingress.yaml
├── agent/                    # LangGraph 에이전트
│   ├── cli.py
│   ├── dr_kube/
│   │   ├── graph.py          # LangGraph 워크플로우
│   │   ├── github.py         # GitHub PR 클라이언트
│   │   ├── llm.py            # LLM 프로바이더
│   │   ├── prompts.py        # 프롬프트 템플릿
│   │   ├── state.py          # 상태 정의
│   │   └── webhook.py        # Alertmanager 웹훅 서버
│   └── issues/               # 샘플 이슈 파일
├── chaos/                    # Chaos Mesh 실험 정의
├── secrets/                  # SOPS 암호화 시크릿
│   ├── secrets.yaml          # 평문 (.gitignore)
│   ├── secrets.enc.yaml      # 암호화됨 (Git OK)
│   └── age.key               # 비밀키 (.gitignore)
├── scripts/
│   ├── setup.sh              # Kind + ArgoCD 설치
│   ├── teardown.sh           # 클러스터 삭제
│   ├── setup-hosts.sh        # 로컬 도메인 등록
│   ├── setup-tls.sh          # TLS 인증서 설정
│   ├── setup-secrets.sh      # SOPS 시크릿 관리
│   ├── setup-slack.sh        # Slack webhook Secret
│   └── setup-agent.sh        # 에이전트 환경
├── Makefile                  # 프로젝트 명령어
└── docs/                     # 문서
```

## 빠른 시작

### 사전 요구사항

- Docker
- Git

> `setup.sh`가 Kind, kubectl, Helm 등을 자동 설치합니다.

### 1. 클러스터 설치

```bash
# Kind 클러스터 + ArgoCD + 모니터링 스택 설치
make setup

# 로컬 도메인 등록 (/etc/hosts)
make hosts
```

### 2. 시크릿 설정

```bash
# 팀 리더: 키 생성 (최초 1회)
make secrets-init

# secrets/secrets.yaml 에 값 입력 후 암호화
make secrets-encrypt

# K8s Secret 생성
make secrets-apply

# 팀원: 키 파일 받아서 등록
make secrets-import KEY=age.key
make secrets-decrypt
make secrets-apply
```

### 3. 에이전트 실행

```bash
# 환경 설정
make agent-setup

# agent/.env 에 API 키 설정
vi agent/.env

# 이슈 분석
make agent-run ISSUE=issues/sample_oom.json

# 이슈 분석 + PR 생성
make agent-fix ISSUE=issues/sample_oom.json

# 웹훅 서버 (Alertmanager 연동)
make agent-webhook
```

### 4. 접속 주소

```bash
make hosts-status    # 접속 주소 확인
```

| 서비스 | 로컬 주소 |
|--------|----------|
| Grafana | http://grafana.drkube.local |
| Prometheus | http://prometheus.drkube.local |
| Alertmanager | http://alert.drkube.local |
| ArgoCD | http://argocd.drkube.local |
| Online Boutique | http://boutique.drkube.local |
| Chaos Mesh | http://chaos.drkube.local |

## 관측성 스택 (Observability)

| 컴포넌트 | 역할 | 시그널 |
|---------|------|--------|
| **Prometheus** | 메트릭 수집 + Alert Rules | Metrics |
| **Alertmanager** | 알림 라우팅 → Slack + Agent Webhook | Metrics |
| **Grafana** | 통합 대시보드 + Drilldown | 전체 |
| **Loki** | 로그 집계 | Logs |
| **Alloy** | 로그/메트릭/프로파일 수집 에이전트 | 전체 |
| **Tempo** | 분산 트레이싱 + span metrics | Traces |
| **Pyroscope** | Continuous Profiling (CPU/Memory/eBPF) | Profiles |
| **metrics-server** | `kubectl top` 실시간 리소스 | Metrics |
| **Chaos Mesh** | 카오스 엔지니어링 | - |

### Grafana Drilldown (4가지 시그널 연동)

```
Traces ──(trace ID)──→ Logs
  │
  ├──(span metrics)──→ Metrics (서비스별 latency, error rate)
  │
  └──(service name)──→ Profiles (CPU flame graph, memory)
```

### Alert Rules (Prometheus)

| 알림 | 조건 | 심각도 |
|------|------|--------|
| ContainerOOMKilled | OOM으로 재시작 | critical |
| PodCrashLooping | 10분 내 3회 재시작 | critical |
| CPUThrottling | throttle 50% 이상 | warning |
| HighMemoryUsage | 메모리 limit 85% 초과 | warning |
| PodNotReady | 5분간 Not Ready | warning |
| ContainerWaiting | 5분간 대기 상태 | warning |
| DeploymentReplicasMismatch | replicas 불일치 | warning |
| NodeHighCPU | 노드 CPU 80% 초과 | warning |

### Grafana 대시보드

- **DR-Kube Overview** - 발화 알림, Pod 재시작, OOM 이벤트, CPU Throttle, Replicas 상태
- **Pod Resources (Real-time)** - CPU/Memory 사용량 vs Limit, Throttle Rate (10초 갱신)
- **Kubernetes Cluster** - 클러스터 전체 뷰 (Grafana.net #7249)
- **Node Exporter** - 노드 리소스 상세 (Grafana.net #1860)

## 카오스 엔지니어링

Online Boutique(10 마이크로서비스)에 Chaos Mesh로 장애를 주입하여 에이전트를 테스트합니다.

### 단일 장애
```bash
make chaos-memory    # Frontend OOM 실험
make chaos-cpu       # CartService CPU 스트레스
make chaos-pod-kill  # CheckoutService Pod 강제 종료
make chaos-network   # ProductCatalog 네트워크 지연

make chaos-status    # 실험 상태 확인
make chaos-stop      # 모든 실험 중지
```

### 복합 장애 (5개)
```bash
make chaos-redis-failure    # Redis 장애 -> 연쇄 실패
make chaos-payment-delay    # Payment 2000ms 지연 -> timeout 전파
make chaos-traffic-spike    # 다중 서비스 동시 CPU+Memory 스트레스
make chaos-dns-failure      # ProductCatalog DNS 장애
make chaos-replica-shortage # Checkout 반복 pod-kill (다운타임)
```

| 시나리오 | 내용 | 관측 포인트 |
|----------|------|-------------|
| Redis 연쇄 실패 | Redis 장애 → cart → checkout → frontend 전파 | Tempo 에러 체인, Loki 로그 |
| 결제 지연 전파 | payment 2초 지연 → checkout/frontend 타임아웃 | Tempo latency 체인, span metrics |
| 트래픽 급증 | 다중 서비스 동시 CPU+Memory 스트레스 | 알림 폭풍, NodeHighCPU |
| DNS 장애 | productcatalog DNS 실패 → frontend 부분 장애 | Loki DNS 에러, PodNotReady |
| 단일 Pod 반복 종료 | replicas=1에서 반복 kill → 다운타임 | DeploymentReplicasMismatch |

### 복합 장애 검증 체크리스트 (#1186)
각 시나리오마다 아래 순서로 검증합니다.

1. 실험 적용
```bash
make chaos-<scenario>
```

2. Chaos 리소스 생성 확인
```bash
make chaos-status
```
- 기대값: 해당 `stresschaos/podchaos/networkchaos/dnschaos` 리소스가 `chaos-mesh` 네임스페이스에 표시됨

3. 대상 서비스 영향 확인
```bash
kubectl get pods -n online-boutique -o wide
kubectl logs -n online-boutique deploy/frontend --tail=100
```
- 기대값: 시나리오별 timeout, connection refused, DNS failure 등 증상 로그 확인

4. 관측 포인트 확인
- Prometheus/Grafana: 알림/패널 이상치 발화 (CPUThrottling, OOMKilled, ReplicasMismatch 등)
- Loki: 오류 로그 증가 (timeout, connection refused, DNS error)
- Tempo: 실패 span 또는 latency chain 확인
- Pyroscope: (traffic-spike) CPU flame graph에서 stress workload 확인

5. 실험 종료 및 정리
```bash
make chaos-stop
make chaos-status
```
- 기대값: chaos 리소스가 모두 제거되고 상태 조회 시 실험 없음

## 시크릿 관리 (SOPS + age)

시크릿은 [SOPS](https://github.com/getsops/sops)로 암호화하여 Git에 안전하게 커밋합니다.

```
secrets.yaml (평문)  →  secrets.enc.yaml (암호화)  →  Git 커밋
      ↑                                                  ↓
  복호화 (age.key)  ←──────────────────────────  git pull
      ↓
  make secrets-apply  →  K8s Secret 생성
```

| 시크릿 | 용도 |
|--------|------|
| slack_webhook_url | Alertmanager Slack 알림 |
| cloudflare_api_token | cert-manager DNS-01 인증 |
| gemini_api_key | LLM API 키 |

> `secrets/age.key`만 팀원에게 오프라인으로 공유하면 됩니다.

## 전체 명령어

```bash
make help              # 전체 명령어 목록

# 클러스터
make setup             # Kind + ArgoCD 설치
make teardown          # 클러스터 삭제
make hosts             # 로컬 도메인 등록
make hosts-status      # 접속 주소 확인
make tls               # TLS 설정
make port-forward      # 포트포워딩 시작

# 시크릿
make secrets-init      # 키 생성 (팀 리더)
make secrets-encrypt   # 암호화
make secrets-decrypt   # 복호화
make secrets-apply     # K8s Secret 생성
make secrets-status    # 상태 확인

# 에이전트
make agent-setup       # 환경 설정
make agent-run         # 이슈 분석
make agent-fix         # 분석 + PR 생성
make agent-oom         # OOM 이슈 분석
make agent-webhook     # 웹훅 서버

# Chaos 실험
make chaos-memory      # OOM 실험
make chaos-cpu         # CPU 스트레스
make chaos-pod-kill    # Pod 강제 종료
make chaos-network     # 네트워크 지연
make chaos-redis-failure    # Redis 장애 -> 연쇄 실패
make chaos-payment-delay    # Payment 지연 -> timeout 전파
make chaos-traffic-spike    # 다중 서비스 동시 CPU+Memory 스트레스
make chaos-dns-failure      # DNS 장애
make chaos-replica-shortage # 반복 pod-kill
make chaos-stop        # 실험 중지
```

## 지원 플랫폼

| 플랫폼 | 상태 |
|--------|------|
| macOS (Intel/Apple Silicon) | ✅ |
| Windows + WSL2 | ✅ |
| Linux (Ubuntu/Debian) | ✅ |

## 문서

- [CHANGELOG](./docs/CHANGELOG.md) - 변경 이력
- [ARCHITECTURE](./docs/ARCHITECTURE.md) - 아키텍처 상세
- [ROADMAP](./docs/ROADMAP.md) - 개발 로드맵
- [Alloy 설정](./docs/ALLOY_CONFIG.md) - Alloy 설정 가이드
- [Chaos Mesh 토큰](./docs/CHAOS_MESH_TOKEN.md) - Chaos Mesh 토큰 관리

## 기술 스택

- **오케스트레이션**: Kubernetes (Kind)
- **GitOps**: ArgoCD (App of Apps 패턴)
- **AI**: LangGraph + Gemini / Ollama
- **관측성**: Prometheus, Grafana, Loki, Alloy, Tempo, Pyroscope
- **카오스**: Chaos Mesh
- **시크릿**: SOPS + age
- **언어**: Python 3.11+
