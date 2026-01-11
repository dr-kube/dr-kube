# DR-Kube 프로젝트

## 프로젝트 개요
K8s 인프라의 이슈를 자동으로 확인하고 해결하는 LangGraph 기반 에이전트.

## 팀 상황
- 4명 개발팀, 개발 경험 부족
- 목표: 2~3월 MVP 완성
- **원칙: 최대한 간단하게 구현**

## 인프라 (Helm으로 관리)
- K8s 클러스터
- ArgoCD (GitOps)
- 모니터링: Prometheus, Alloy, Loki, Grafana
- nginx ingress
- chaos-mesh (카오스 테스트)

## 에이전트 구조 (`agent/`)

```
agent/
├── src/
│   ├── cli.py              # CLI 엔트리포인트
│   └── dr_kube/
│       ├── graph.py        # LangGraph 워크플로우 (핵심)
│       ├── state.py        # 상태 정의 (IssueState)
│       ├── prompts.py      # LLM 프롬프트
│       └── llm.py          # LLM 프로바이더 (Ollama/Gemini)
└── issues/                 # 샘플 이슈 JSON 파일
```

### 현재 워크플로우
```
load_issue → analyze → suggest → END
```

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

### K8s 디버깅
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
