# DR-Kube 프로젝트

## 프로젝트 개요
K8s 인프라의 이슈를 자동으로 확인하고 해결하는 LangGraph 기반 에이전트.

## 팀 상황
- 4명 개발팀, 개발 경험 부족
- 목표: 2~3월 MVP 완성
- **원칙: 최대한 간단하게 구현**

## 인프라 (Helm으로 관리)
- K8s 클러스터
- **ArgoCD (GitOps)** - Git이 single source of truth
- 모니터링: Prometheus, Alloy, Loki, Grafana
- nginx ingress
- chaos-mesh (카오스 테스트)

### ⚠️ 중요: ArgoCD 기반 운영
- `kubectl apply/delete/edit` **사용 금지**
- 모든 변경은 Git → ArgoCD 경로로만
- 에이전트는 읽기 전용 + Git PR 생성

## 에이전트 구조 (`agent/`)

```
agent/
├── src/
│   ├── cli.py              # CLI 엔트리포인트
│   └── dr_kube/
│       ├── graph.py        # LangGraph 워크플로우 (핵심)
│       ├── state.py        # 상태 정의 (IssueState)
│       ├── prompts.py      # LLM 프롬프트
│       ├── llm.py          # LLM 프로바이더 (Ollama/Gemini)
│       └── argocd.py       # ArgoCD/K8s 데이터 수집
└── issues/                 # 샘플 이슈 JSON 파일
```

### 워크플로우 (ArgoCD 연동)
```
[옵션 1: JSON 파일 기반]
load_issue → analyze → suggest → END

[옵션 2: 실시간 모니터링 - 목표]
collect_argocd → collect_k8s → analyze → generate_fix → create_pr → END
     ↓              ↓             ↓            ↓             ↓
  ArgoCD 상태   K8s 리소스    LLM 분석   Git 파일 수정    PR 생성
```

**주요 노드:**
- `collect_argocd`: ArgoCD Application 상태 수집
- `collect_k8s`: Pod/Event/로그 수집
- `analyze`: LLM으로 문제 분석
- `generate_fix`: 수정할 Git 파일 제안
- `create_pr`: Git 브랜치 생성 및 PR

### 실행 방법
```bash
cd agent
python -m cli analyze issues/sample_oom.json
```

## 코드 컨벤션

### 파일 작성 규칙
- 한국어 주석/docstring 사용
- 타입 힌트 필수 (`TypedDict`, `list[str]` 등)
- 함수는 단일 책임 원칙

### LangGraph 노드 작성 패턴
```python
def node_name(state: IssueState) -> IssueState:
    """노드 설명 (한국어)"""
    if state.get("error"):
        return state  # 에러 전파

    # 로직 수행
    return {"key": "value", "status": "상태명"}
```

### 새 노드 추가 시
1. `state.py`에 필요한 필드 추가
2. `graph.py`에 노드 함수 작성
3. `create_graph()`에 노드와 엣지 추가

## 자주 쓰는 명령어

### ArgoCD (읽기 전용)
```bash
argocd app list                        # Application 목록
argocd app get <app>                   # 상세 정보
argocd app diff <app>                  # Git vs 현재 상태 차이
```

### K8s 디버깅 (읽기 전용)
```bash
kubectl get pods -A                    # 전체 Pod 상태
kubectl logs <pod> -n <namespace>      # 로그 확인
kubectl describe pod <pod> -n <ns>     # Pod 상세 정보
kubectl get events -n <namespace>      # 이벤트 확인
```

### Helm
```bash
helm list -A                           # 설치된 차트 목록
helm status <release> -n <namespace>   # 릴리즈 상태
```

### Git 작업 (에이전트가 PR 생성 시)
```bash
git checkout -b fix/auto-fix-xxx       # 브랜치 생성
git add values/ manifests/             # 수정 파일 추가
git commit -m "fix: ..."               # 커밋
git push origin fix/auto-fix-xxx       # 푸시
gh pr create                           # PR 생성
```

### 에이전트 개발
```bash
cd agent && source ../venv/bin/activate
pip install -e .                       # 개발 모드 설치
python -m cli analyze <issue.json>     # 분석 실행
```

## 환경변수 (.env)
```
LLM_PROVIDER=ollama          # 또는 gemini
OLLAMA_MODEL=llama3.2        # Ollama 사용 시
GEMINI_API_KEY=xxx           # Gemini 사용 시
GEMINI_MODEL=gemini-pro      # Gemini 모델
```
