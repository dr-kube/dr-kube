# DR-Kube 프로젝트 Copilot 가이드

## 프로젝트 개요

Kubernetes 이슈 자동 감지 → 분석 → PR 생성 → GitOps 복구 시스템

**목표일**: 2026년 2월 28일 (3월 전 완료)

## 시스템 플로우

```
이슈 발생 → 알람(Slack) → 에이전트 감지 → 이슈 분류 → 이슈 분석
                                                            ↓
완료 알람 ← 복구 검증 ← ArgoCD Sync ← PR 생성 ← 수정안 생성
```

## GitOps 원칙 (⚠️ 중요)

> **kubectl은 읽기 전용으로만 사용**

- 클러스터 변경은 **오직 Git을 통해서만** 수행
- 에이전트는 `values/*.yaml` 수정 → PR 생성 → ArgoCD가 동기화
- **금지**: `kubectl apply`, `kubectl patch` 등 쓰기 명령
- **허용**: `kubectl get`, `kubectl describe`, `kubectl logs`

## 핵심 경로

```
dr-kube/
├── agent/
│   ├── cli.py              # CLI 진입점
│   └── dr_kube/            # 메인 에이전트 코드 ⭐
│       ├── graph.py        # LangGraph 워크플로우
│       ├── llm.py          # LLM 프로바이더
│       ├── prompts.py      # 프롬프트 템플릿
│       └── state.py        # 상태 정의
├── values/                 # Helm values (수정 대상)
├── scripts/                # 설정 스크립트
└── docs/                   # 문서
```

## 워크플로우 노드

| 노드 | 역할 | 상태 |
|------|------|------|
| load_issue | 알람에서 이슈 로드 | ✅ 완료 |
| analyze | LLM 분석 | ✅ 완료 |
| generate_fix | YAML 수정안 생성 | ⏳ TODO |
| create_pr | GitHub PR 생성 | ⏳ TODO |
| notify | 완료 알람 | ⏳ TODO |

## 모니터링 스택 (구축 완료)

- Prometheus: 메트릭 수집
- Loki: 로그 수집
- Grafana: 대시보드/알람
- ArgoCD: GitOps 배포
- Alloy: 로그/메트릭 수집기

## 코딩 규칙

- Python 3.11+ (현재 3.12.3)
- LangGraph 기반 워크플로우
- LLM: Ollama(로컬) 또는 Gemini 3.0 Flash
- 한글 주석/문서 사용

## 금지 사항

- `kubectl apply`, `kubectl patch` 등 클러스터 직접 수정 코드 생성 금지
- `values/*.yaml` 외 다른 경로에 K8S 리소스 생성 금지

## 자주 사용하는 명령어

```bash
# 에이전트 설정 및 실행 (프로젝트 루트에서)
make agent-setup         # 환경 설정
make agent-run           # 기본 실행
make agent-oom           # OOM 이슈 분석
make agent-cpu           # CPU Throttle 분석
make help                # 전체 명령어
```

## 로컬 환경

```bash
./scripts/setup.sh           # 원클릭 설치
./scripts/setup.sh cluster   # Kind 클러스터만
./scripts/setup.sh argocd    # ArgoCD 설치
./scripts/teardown.sh        # 환경 삭제
```

## 테스트 (Chaos Mesh)

```bash
./scripts/chaos-test.sh oom        # OOMKilled 발생
./scripts/chaos-test.sh cpu        # CPU 스로틀링
./scripts/chaos-test.sh network    # 네트워크 장애
./scripts/chaos-test.sh pod-kill   # 파드 강제 종료
```

## 참고 문서

- docs/ROADMAP.md - 주간별 상세 계획
- agent/README.md - 에이전트 사용법
- docs/ARCHITECTURE.md - 아키텍처
