# 빠른 시작 가이드

로그 분석 에이전트를 처음 사용하는 경우 다음 순서로 진행하세요.

## 1단계: 환경 설정

### 1-1. .env 파일 생성

```bash
cd ai-drkube
cp env.sample .env
```

### 1-2. .env 파일 수정

`.env` 파일을 열어서 다음 항목을 설정하세요:

```bash
# 필수: Google Gemini API 키 설정
GOOGLE_API_KEY=your-gemini-api-key-here

# 선택: Kubernetes 설정 (Pod 로그 수집 시 필요)
KUBECONFIG_PATH=/path/to/kubeconfig  # 또는 주석 처리하여 기본 경로 사용

# 선택: 로그 분석 에이전트 설정
MODEL_NAME=gemini-pro
REPO_PATH=.
SIMULATE=true  # 처음에는 true로 시작 (시뮬레이션 모드)
AUTO_APPROVE=true
```

**중요**: `GOOGLE_API_KEY`는 반드시 설정해야 합니다!

## 2단계: 의존성 설치

```bash
# 가상환경 활성화 (이미 활성화되어 있다면 생략)
pyenv activate ai-drkube

# 패키지 설치
pip install -r requirements.txt
```

## 3단계: 테스트 실행

### 3-1. 샘플 로그 파일로 테스트

```bash
# 샘플 로그 파일로 테스트 (상호작용 모드, 시뮬레이션 모드)
python -m tools.log_analysis_agent tools/sample_error.log --type file

# 또는 명시적으로 상호작용 모드 활성화
python -m tools.log_analysis_agent tools/sample_error.log --type file --interactive
```

이 명령어는:
1. 샘플 로그 파일을 읽어서
2. 에러를 분류하고
3. **카테고리 선택 UI 표시** (상호작용 모드)
4. **리소스 타입 선택 UI 표시** (상호작용 모드)
5. 선택한 카테고리만 Gemini로 근본 원인 분석
6. 선택한 리소스 타입에 대한 Git 액션 생성 (시뮬레이션 모드이므로 실제 파일은 변경되지 않음)

### 3-2. 결과 확인

실행 후 다음 디렉토리에 생성될 파일들을 확인할 수 있습니다:
- `patches/`: Kubernetes 설정 파일 및 패치
- `reports/`: 분석 리포트

**주의**: 시뮬레이션 모드(`SIMULATE=true`)에서는 실제로 파일이 생성되지 않고 콘솔에만 표시됩니다.

## 4단계: 실제 로그 분석

### 4-1. 로컬 파일 분석

```bash
# 실제 에러 로그 파일 분석
python -m tools.log_analysis_agent /path/to/your/error.log --type file
```

### 4-2. Kubernetes Pod 로그 분석

```bash
# 특정 Pod의 로그 분석 (상호작용 모드 - 기본값)
python -m tools.log_analysis_agent argocd-server-766b6bbb64-k7wch --type pod

# 명시적으로 상호작용 모드 활성화
python -m tools.log_analysis_agent argocd-server-766b6bbb64-k7wch --type pod --interactive

# 라벨로 여러 Pod의 로그 분석
python -m tools.log_analysis_agent "app.kubernetes.io/name=argocd" --type label
```

**상호작용 모드에서의 실행 흐름:**
1. 로그 수집 (자동)
2. 에러 분류 (자동)
3. **카테고리 선택 UI** → 사용자가 분석할 카테고리 선택
4. **리소스 타입 선택 UI** → 사용자가 리포트에 포함할 리소스 타입 선택 (Pod, Service, Deployment 등)
5. 선택한 카테고리만 근본 원인 분석
6. 선택한 리소스 타입에 대한 리포트 생성

### 4-3. 디렉토리의 모든 로그 파일 분석

```bash
# 디렉토리 내 모든 .log 파일 분석
python -m tools.log_analysis_agent /path/to/logs --type directory
```

## 5단계: 실제 파일 생성 및 커밋 (선택사항)

시뮬레이션 모드에서 결과를 확인한 후, 실제로 파일을 생성하고 커밋하려면:

```bash
# 시뮬레이션 모드 비활성화 (상호작용 모드는 유지)
python -m tools.log_analysis_agent error.log --type file --no-simulate

# 비상호작용 모드 + 실제 파일 생성 (모든 카테고리 자동 분석)
python -m tools.log_analysis_agent error.log --type file --no-interactive --no-simulate
```

## 모드 옵션 요약

### 상호작용 모드 (기본값)

```bash
# 기본 실행 (상호작용 모드 활성화)
python -m tools.log_analysis_agent <log-source> --type <type>

# 명시적으로 상호작용 모드 활성화
python -m tools.log_analysis_agent <log-source> --type <type> --interactive
```

**특징:**
- 카테고리 선택 UI 표시
- 리소스 타입 선택 UI 표시
- 사용자가 원하는 항목만 선택하여 분석

### 비상호작용 모드

```bash
# 비상호작용 모드 (모든 카테고리 자동 분석)
python -m tools.log_analysis_agent <log-source> --type <type> --no-interactive
```

**특징:**
- 모든 카테고리 자동 분석
- 모든 리소스 타입에 대한 리포트 생성
- 자동화 스크립트에 적합

**주의**: 이 명령어는 실제로 파일을 생성하고 Git 커밋을 수행합니다. 
프로덕션 환경에서는 먼저 시뮬레이션 모드로 확인한 후 수동으로 적용하는 것을 권장합니다.

## 전체 워크플로우

에이전트는 다음 8단계를 자동으로 수행합니다:

1. **로그 수집**: 지정한 소스에서 로그 수집
2. **에러 분류**: 키워드 기반으로 에러 카테고리 분류
3. **근본 원인 분석**: Gemini LLM으로 상세 분석
4. **사용자 피드백**: 분석 결과 표시 (자동 승인 모드)
5. **액션 생성**: Git 변경사항 생성
6. **Git 커밋**: 변경사항 커밋 (시뮬레이션 모드)
7. **복구 검증**: 복구 결과 확인 (시뮬레이션)
8. **최종 피드백**: 결과 요약 표시

## 문제 해결

### "GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다" 오류

`.env` 파일에 `GOOGLE_API_KEY`가 설정되어 있는지 확인하세요.

### "수집된 로그가 없습니다" 오류

- 파일 경로가 올바른지 확인
- 파일에 로그가 실제로 있는지 확인
- Pod 이름이나 라벨 셀렉터가 올바른지 확인

### Kubernetes Pod 로그 수집 실패

- `kubectl get pods`로 Pod가 존재하는지 확인
- `KUBECONFIG_PATH`가 올바르게 설정되었는지 확인
- 네임스페이스가 올바른지 확인 (기본값: `default`)

## 다음 단계

- `tools/README.md`: 상세한 사용 가이드
- `tools/example_usage.py`: Python 코드에서 사용하는 예제

## 명령어 예시

### 기본 형식
```bash
python -m tools.log_analysis_agent <source> --type <type>
```

### 실제 사용 예시

#### 1. 로컬 파일 분석
```bash
# 샘플 로그 파일 분석
python -m tools.log_analysis_agent tools/sample_error.log --type file

# 특정 경로의 로그 파일 분석
python -m tools.log_analysis_agent /var/log/app/error.log --type file

# 상대 경로 사용
python -m tools.log_analysis_agent ./logs/error.log --type file
```

#### 2. Kubernetes Pod 분석
```bash
# 기본 네임스페이스(default)의 Pod 분석
python -m tools.log_analysis_agent argocd-server-766b6bbb64-k7wch --type pod

# OOMKilled 상태인 Pod 분석
python -m tools.log_analysis_agent oom-pod-sample-747559ffb6-bdlmk --type pod

# ArgoCD Redis Pod 분석
python -m tools.log_analysis_agent argocd-redis-6cb4b96cd8-7rwgv --type pod
```

#### 3. 라벨 셀렉터로 여러 Pod 분석
```bash
# ArgoCD 관련 모든 Pod 분석
python -m tools.log_analysis_agent "app.kubernetes.io/name=argocd" --type label

# Prometheus 관련 Pod 분석
python -m tools.log_analysis_agent "app=prometheus" --type label

# 여러 라벨 조건 사용
python -m tools.log_analysis_agent "app=myapp,env=production" --type label
```

#### 4. 디렉토리에서 모든 로그 파일 분석
```bash
# 현재 디렉토리의 모든 .log 파일 분석
python -m tools.log_analysis_agent ./logs --type directory

# 특정 디렉토리의 로그 파일 분석
python -m tools.log_analysis_agent /var/log/app --type directory
```

#### 5. 옵션 조합 예시
```bash
# 상호작용 모드 + 시뮬레이션 (기본값)
python -m tools.log_analysis_agent tools/sample_error.log --type file

# 비상호작용 모드 (모든 카테고리 자동 분석)
python -m tools.log_analysis_agent tools/sample_error.log --type file --no-interactive

# 실제 파일 생성 및 Git 커밋
python -m tools.log_analysis_agent tools/sample_error.log --type file --no-simulate

# 커스텀 kubeconfig 경로 지정
python -m tools.log_analysis_agent my-pod --type pod --kubeconfig ~/.kube/config

# 사용자 승인 요청 (자동 승인 비활성화)
python -m tools.log_analysis_agent tools/sample_error.log --type file --no-auto-approve
```

#### 6. 실제 Kubernetes 클러스터에서 사용 예시
```bash
# 1단계: Pod 목록 확인
kubectl get pods -n default

# 2단계: 문제가 있는 Pod 찾기
kubectl get pods | grep -i error
kubectl get pods | grep -i oom

# 3단계: 해당 Pod의 로그 분석
python -m tools.log_analysis_agent oom-pod-sample-747559ffb6-bdlmk --type pod

# 또는 서비스의 모든 Pod 분석
python -m tools.log_analysis_agent "app.kubernetes.io/name=argocd" --type label
```
