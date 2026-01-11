# ArgoCD 연동 설계

## 현재 상황
- ArgoCD로 모든 인프라 관리 (GitOps)
- `applications/`, `manifests/`, `values/` 디렉토리로 구성
- **kubectl로 직접 수정 금지** (Git이 single source of truth)

## 에이전트 - ArgoCD 연동 방식

### 1. 읽기 전용 모니터링 (현재 단계)
에이전트가 ArgoCD + K8s 상태를 읽고 분석만 수행

```
ArgoCD 상태 수집 → K8s 리소스 확인 → 문제 분석 → 해결책 제시
```

**수집 정보:**
- `argocd app list` - 전체 Application 상태
- `argocd app get <app>` - 특정 앱 상세 (Sync 상태, Health)
- `kubectl get pods/events` - 실제 리소스 상태
- `kubectl logs` - 로그 수집

**에이전트 결과:**
- 문제 진단
- 수정해야 할 Git 파일 경로 제시
- 수정할 내용 (YAML diff) 제시

### 2. Git PR 자동 생성 (다음 단계)
에이전트가 해결책을 Git PR로 자동 생성

```
문제 분석 → Git 파일 수정 → 브랜치 생성 → PR 생성 → 사람이 리뷰/승인
```

**워크플로우:**
1. 에이전트가 `values/` 또는 `manifests/` 수정
2. `fix/issue-xxx` 브랜치 생성
3. Git commit & push
4. GitHub/GitLab PR 생성
5. 팀원 리뷰 후 merge
6. ArgoCD가 자동 sync

### 3. Auto-Remediation (최종 단계)
특정 이슈는 자동 수정 (승인 없이)

**허용 기준 (예시):**
- Pod restart (OOM 등)
- Image tag 업데이트
- Resource limit 증가
- Replica 수 조정

## 에이전트 워크플로우 (제안)

```
┌─────────────────┐
│  Webhook/Cron   │ ← Prometheus AlertManager, 주기적 실행
└────────┬────────┘
         ↓
┌─────────────────┐
│ collect_argocd  │ ← argocd app list, get
└────────┬────────┘
         ↓
┌─────────────────┐
│ collect_k8s     │ ← kubectl get pods/events/logs
└────────┬────────┘
         ↓
┌─────────────────┐
│ analyze (LLM)   │ ← 문제 분석, 근본 원인 파악
└────────┬────────┘
         ↓
┌─────────────────┐
│ generate_fix    │ ← 수정할 파일/내용 생성
└────────┬────────┘
         ↓
┌─────────────────┐
│ create_pr       │ ← Git 브랜치 생성, PR 생성
└────────┬────────┘
         ↓
┌─────────────────┐
│ notify_team     │ ← Slack/Email 알림
└─────────────────┘
```

## 필요한 노드 추가

### 1. `collect_argocd` 노드
```python
def collect_argocd(state: IssueState) -> IssueState:
    """ArgoCD Application 상태 수집"""
    # argocd app list -o json
    # argocd app get <app> --hard-refresh
    return {"argocd_apps": [...], "status": "argocd_collected"}
```

### 2. `collect_k8s` 노드
```python
def collect_k8s(state: IssueState) -> IssueState:
    """K8s 리소스 상태 수집"""
    # kubectl get pods -A -o json
    # kubectl get events --sort-by='.lastTimestamp'
    return {"k8s_resources": {...}, "status": "k8s_collected"}
```

### 3. `generate_fix` 노드
```python
def generate_fix(state: IssueState) -> IssueState:
    """Git 파일 수정 내용 생성"""
    # LLM에게 어떤 파일을 어떻게 수정할지 물어봄
    return {
        "fix_files": [
            {"path": "values/grafana-values.yaml", "diff": "..."},
            {"path": "manifests/deployment.yaml", "diff": "..."}
        ],
        "status": "fix_generated"
    }
```

### 4. `create_pr` 노드
```python
def create_pr(state: IssueState) -> IssueState:
    """Git 브랜치 생성 및 PR 생성"""
    # git checkout -b fix/auto-fix-xxx
    # git add, commit, push
    # gh pr create (GitHub CLI)
    return {"pr_url": "https://...", "status": "pr_created"}
```

## ArgoCD CLI 주요 명령어

```bash
# Application 목록
argocd app list

# 특정 앱 상태
argocd app get monitoring/grafana

# Sync 상태 확인
argocd app sync monitoring/grafana --dry-run

# Health 확인
argocd app wait monitoring/grafana --health
```

## 권한 설정

### 읽기 전용
- `kubectl get`, `describe`, `logs` 만 허용
- `argocd app list`, `get` 허용
- `kubectl apply/delete/edit` **차단**

### Git 작업
- `git checkout`, `add`, `commit`, `push` 허용
- `gh pr create` 허용

## 다음 단계

1. ✅ 권한 설정 업데이트 (kubectl 쓰기 차단)
2. ⏳ `collect_argocd`, `collect_k8s` 노드 추가
3. ⏳ `generate_fix` 노드로 Git 파일 수정 제안
4. ⏳ `create_pr` 노드로 자동 PR 생성
5. ⏳ Prometheus AlertManager Webhook 연동
