# DR-Kube 🚀

> **D**isaster **R**ecovery for **Kube**rnetes - AI 기반 Kubernetes 장애 자동 복구 시스템

[![ArgoCD](https://img.shields.io/badge/ArgoCD-GitOps-blue?logo=argo)](https://argoproj.github.io/cd/)
[![LangGraph](https://img.shields.io/badge/LangGraph-AI%20Agent-green?logo=langchain)](https://langchain-ai.github.io/langgraph/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Container%20Orchestration-326CE5?logo=kubernetes)](https://kubernetes.io/)

## 📋 개요

DR-Kube는 Kubernetes 클러스터에서 발생하는 장애를 **자동으로 감지, 분석, 복구**하는 AI 기반 DevOps 자동화 시스템입니다. LangGraph를 활용한 지능형 에이전트가 로그를 분석하고, GitOps 패턴(App of Apps)을 통해 안전하게 복구 작업을 수행합니다.

### 🎯 주요 기능

- **🔍 자동 장애 감지**: 로그 분석을 통한 OOM, CrashLoop, 설정 오류 등 다양한 장애 유형 자동 분류
- **🧠 AI 기반 원인 분석**: LLM을 활용한 근본 원인 분석 및 복구 액션 제안
- **🔄 GitOps 자동 복구**: ArgoCD App of Apps 패턴을 활용한 자동 복구 커밋
- **📊 통합 모니터링**: Grafana, Prometheus, Loki, Alloy를 통한 통합 관측성(Observability)
- **🧪 카오스 엔지니어링**: Chaos Mesh를 통한 장애 시뮬레이션 및 복원력 테스트

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DR-Kube System                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   Grafana    │◄───│    Loki      │◄───│    Alloy     │◄── Kubernetes    │
│  │  Dashboard   │    │   (Logs)     │    │  (Collector) │    Cluster       │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│         │                   │                                                │
│         ▼                   ▼                                                │
│  ┌────────────────────────────────────────┐                                 │
│  │          LangGraph Agent               │                                 │
│  │  ┌────────┐ ┌────────┐ ┌────────────┐ │                                 │
│  │  │ 로그   │→│ 에러   │→│ 원인 분석  │ │                                 │
│  │  │ 수집   │ │ 분류   │ │            │ │                                 │
│  │  └────────┘ └────────┘ └────────────┘ │                                 │
│  │       │           │           │       │                                 │
│  │       ▼           ▼           ▼       │                                 │
│  │  ┌────────┐ ┌────────┐ ┌────────────┐ │                                 │
│  │  │ 피드백 │←│ 복구   │←│ 액션 생성  │ │                                 │
│  │  │        │ │ 검증   │ │ & Git 커밋 │ │                                 │
│  │  └────────┘ └────────┘ └────────────┘ │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │                    GitOps (ArgoCD)                                │       │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │       │
│  │  │ Application │  │ Application │  │ Application │   ...         │       │
│  │  │  (Grafana)  │  │ (Prometheus)│  │   (Loki)    │               │       │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │       │
│  │                    App of Apps Pattern                            │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📁 프로젝트 구조

```
dr-kube/
├── README.md                 # 이 파일
├── applications/             # ArgoCD Application 정의 (App of Apps)
│   ├── alloy.yaml           # Grafana Alloy (로그/메트릭 수집)
│   ├── argocd.yaml          # ArgoCD
│   ├── chaos-mesh.yaml      # Chaos Mesh (카오스 엔지니어링)
│   ├── grafana.yaml         # Grafana Dashboard
│   ├── loki.yaml            # Loki (로그 저장)
│   ├── nginx-ingress.yaml   # Nginx Ingress Controller
│   ├── oom-test.yaml        # OOM 테스트용 Application
│   └── prometheus.yaml      # Prometheus (메트릭)
├── values/                   # Helm Values 파일
│   ├── alloy.yaml
│   ├── argocd.yaml
│   ├── chaos-mesh.yaml
│   ├── grafana.yaml
│   ├── loki.yaml
│   ├── nginx-ingress.yaml
│   └── prometheus.yaml
├── manifests/                # Kubernetes 매니페스트
│   ├── application-root.yaml # Root Application (App of Apps)
│   ├── ingress.yaml         # Ingress 설정
│   └── oom-test.yaml        # OOM 테스트용 매니페스트
├── agent/                    # LangGraph 장애 대응 에이전트
│   ├── src/                 # 소스 코드
│   │   ├── cli.py           # CLI 인터페이스
│   │   ├── dr_kube/         # DR-Kube 메인 모듈
│   │   │   ├── graph.py     # LangGraph 그래프 정의
│   │   │   ├── llm.py       # LLM 설정
│   │   │   ├── prompts.py   # 프롬프트 템플릿
│   │   │   └── state.py     # 상태 모델
│   │   ├── .env.example     # 환경 변수 예시
│   │   ├── pyproject.toml   # 프로젝트 설정
│   │   └── requirements.txt # Python 의존성
│   ├── tools/               # 유틸리티 도구
│   │   ├── log_collector.py        # 로그 수집기
│   │   ├── error_classifier.py     # 에러 분류기
│   │   ├── root_cause_analyzer.py  # 근본 원인 분석기
│   │   ├── git_action.py           # Git 액션
│   │   ├── log_analysis_agent.py   # 로그 분석 에이전트
│   │   └── alert_webhook_server.py # 알림 웹훅 서버
│   ├── issues/              # 샘플 이슈 파일
│   │   ├── sample_oom.json
│   │   ├── sample_image_pull.json
│   │   └── sample_cpu_throttle.json
│   ├── env.sample           # 환경 변수 샘플
│   ├── requirements.txt     # 의존성 (루트)
│   └── README.md            # Agent 문서
├── docs/                     # 문서
│   ├── ALLOY_CONFIG.md      # Alloy 설정 가이드
│   ├── CHAOS_MESH_TOKEN.md  # Chaos Mesh 토큰 관리
│   ├── IMPROVEMENTS.md      # 개선 사항
│   └── SETUP.md             # 설정 가이드
├── docker-compose.yml        # Docker Compose 설정
├── Dockerfile.dev            # 개발용 Dockerfile
├── Makefile                  # 빌드/실행 명령어
└── .python-version           # Python 버전 지정
```

## 🚀 빠른 시작

### 사전 요구사항

- Kubernetes 클러스터 (1.25+)
- ArgoCD 설치
- **Docker & Docker Compose** (로컬 개발 환경)
- Git

### 1. Docker 개발 환경 설정 (권장)

모든 팀원이 동일한 환경에서 개발할 수 있도록 Docker Compose를 사용합니다.

```bash
# 환경 변수 설정 (agent/src/.env 파일 생성)
cp agent/src/.env.example agent/src/.env
# .env 파일을 열어서 LLM 설정 수정

# Docker 이미지 빌드 및 컨테이너 시작
make build
make up

# Ollama 모델 다운로드 (최초 1회, 시간 소요)
make ollama-pull

# agent 컨테이너 접속
make shell
```

**Docker 환경의 장점:**
- Python 3.11, kubectl, argocd CLI, helm이 모두 설치됨
- 팀원 간 동일한 개발 환경 보장
- 로컬 kubeconfig 자동 마운트

### 2. ArgoCD App of Apps 배포

```bash
# Root Application 배포 (모든 앱 자동 배포)
kubectl apply -f manifests/application-root.yaml
```

### 3. 장애 대응 에이전트 실행

```bash
# Docker 컨테이너 내에서 실행
make shell

# 컨테이너 내부에서
cd agent/src
python cli.py analyze ../issues/sample_oom.json

# 또는 외부에서 직접 실행
make analyze
```

### 4. 자주 사용하는 명령어

```bash
make help           # 사용 가능한 명령어 목록
make shell          # agent 컨테이너 셸 접속
make logs           # 컨테이너 로그 확인
make test           # pytest 실행
make k8s-status     # K8s 클러스터 상태 확인
make argocd-status  # ArgoCD 상태 확인
make down           # 컨테이너 중지
make clean          # 전체 삭제 (볼륨 포함)
```

### 로컬 개발 환경 (Docker 미사용)

Docker를 사용하지 않는 경우 다음과 같이 설정:

```bash
# Python 가상환경 생성
python -m venv venv
source venv/bin/activate

# 의존성 설치
cd agent
pip install -r src/requirements.txt

# kubectl, argocd CLI, helm 별도 설치 필요
```

## 🔧 지원하는 장애 유형

| 카테고리 | 설명 | 자동 복구 액션 |
|---------|------|---------------|
| `oom` | Out of Memory | 메모리 리소스 제한 증가 |
| `crashloop` | CrashLoopBackOff | 이미지 태그 수정, 의존성 확인 |
| `config_error` | 설정 오류 | values.yaml 수정 |
| `resource_exhausted` | 리소스 부족 | 리소스 쿼터 조정 |
| `network_error` | 네트워크 오류 | 네트워크 정책 수정 |
| `image_pull_error` | 이미지 풀 실패 | 이미지 태그/레지스트리 수정 |
| `scheduling_error` | 스케줄링 실패 | Affinity/Toleration 조정 |

## 📊 모니터링 스택

| 컴포넌트 | 역할 | 포트 |
|---------|------|------|
| **Grafana** | 대시보드 & 시각화 | 3000 |
| **Prometheus** | 메트릭 수집 & 저장 | 9090 |
| **Loki** | 로그 집계 & 쿼리 | 3100 |
| **Alloy** | 로그/메트릭 수집 에이전트 | 12345 |
| **Chaos Mesh** | 카오스 엔지니어링 | 2333 |

## 🧪 카오스 엔지니어링

Chaos Mesh를 활용하여 다양한 장애 시나리오를 시뮬레이션할 수 있습니다:

```bash
# Dashboard 토큰 생성
kubectl create token chaos-dashboard -n chaos-mesh --duration=87600h

# 토큰을 Secret으로 저장
TOKEN=$(kubectl create token chaos-dashboard -n chaos-mesh --duration=87600h)
kubectl create secret generic chaos-dashboard-token -n chaos-mesh \
  --from-literal=token="$TOKEN"
```

자세한 내용은 [Chaos Mesh 토큰 관리](./docs/CHAOS_MESH_TOKEN.md) 문서를 참고하세요.

## 🔄 LangGraph 워크플로우

```
로그 입력 → 에러 분류 → 원인 분석 → 사용자 피드백 → 액션 생성 → Git 커밋 → 복구 검증 → 최종 피드백
```

1. **로그 수집**: 로컬 파일 또는 Loki에서 로그 수집
2. **에러 분류**: 키워드/패턴 기반 에러 카테고리 분류
3. **근본 원인 분석**: 에러 카테고리 기반 원인 분석
4. **사용자 피드백**: 분석 결과 확인 (자동/수동)
5. **액션 생성**: values.yaml 수정 사항 생성
6. **Git 커밋**: 변경사항 커밋 (ArgoCD 자동 동기화)
7. **복구 검증**: Kubernetes 상태 확인
8. **최종 피드백**: 결과 보고

## 📚 문서

- [Alloy 설정 가이드](./docs/ALLOY_CONFIG.md)
- [Chaos Mesh 토큰 관리](./docs/CHAOS_MESH_TOKEN.md)
- [설정 가이드](./docs/SETUP.md)
- [개선 사항](./docs/IMPROVEMENTS.md)

## 🛠️ 기술 스택

- **컨테이너 오케스트레이션**: Kubernetes
- **GitOps**: ArgoCD (App of Apps 패턴)
- **AI/ML**: LangGraph, LangChain, OpenAI/Anthropic LLM
- **모니터링**: Grafana, Prometheus, Loki, Alloy
- **카오스 엔지니어링**: Chaos Mesh
- **언어**: Python 3.10+, YAML
- **CI/CD**: Git 기반 자동화

## 🤝 기여 방법

1. 이 저장소를 Fork합니다
2. 새 Feature 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 Push합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 문의

프로젝트에 대한 질문이나 제안이 있으시면 이슈를 생성해 주세요.