# dr-kube LangGraph Agent 🤖

Kubernetes 클러스터의 문제를 자동으로 감지하고 수정하는 AI 에이전트입니다.

## 🎯 주요 기능

- **자동 이슈 감지**: OOMKilled, CrashLoopBackOff, ImagePullBackOff, Pending 등 자동 탐지
- **AI 분석**: Gemini를 사용한 근본 원인 분석 (선택)
- **승인 후 자동 수정**: 사용자 승인 후 kubectl 명령으로 자동 수정
- **롤백 지원**: 문제 발생 시 즉시 롤백 가능
- **규칙 기반 폴백**: Gemini 없이도 기본 분석/수정 가능

## 🚀 빠른 시작

### 가장 빠른 방법 ⚡

```bash
cd agent-core

# 1. 가상환경 설정
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# 2. 패키지 설치
pip install -r requirements-langgraph.txt

# 3. 바로 실행!
./quickstart.py
```

그게 다입니다! 자동으로 클러스터를 분석하고 문제를 해결합니다.

> 💡 **더 자세한 가이드**: [QUICKSTART.md](QUICKSTART.md) 참고

### 다른 실행 방법들

#### 방법 1: CLI 명령어

```bash
# 전체 네임스페이스 스캔
python -m langgraph_agent.cli -n default

# 특정 파드만 분석
python -m langgraph_agent.cli -n default -p my-pod

# 분석만 하고 수정하지 않기
python -m langgraph_agent.cli -n default --dry-run

# 승인 없이 자동 수정 (주의!)
python -m langgraph_agent.cli -n default --auto-approve
```

#### 방법 2: 시나리오별 예제

다양한 상황에 맞는 예제를 제공합니다:

```bash
# 6가지 시나리오 예제 실행
./examples_scenarios.py
```

#### 방법 3: Python 코드로

```python
from langgraph_agent.agent import DrKubeAgent

# 에이전트 생성
agent = DrKubeAgent(namespace="default")

# 분석 실행 및 결과 확인
result = agent.analyze(auto_approve=False)
print(result["response"])
```

#### 방법 4: Chaos Engineering 🆕

```bash
# Chaos 시나리오 실행
./chaos_scenarios.py

# 또는 Python으로
from langgraph_agent.tools import chaos

# Pod Kill 실험
chaos.quick_pod_kill("default", {"app": "my-app"}, "30s")
```

자세한 내용: [CHAOS_GUIDE.md](CHAOS_GUIDE.md)

### 환경 설정 (선택사항)

Gemini API를 사용하려면:

```bash
cp .env.example .env
# .env 파일을 편집하여 GEMINI_API_KEY 추가
```

> **참고**: API 키가 없어도 Mock 모드로 작동합니다!

## 📚 프로젝트 구조

```
agent-core/
├── langgraph_agent/          # 메인 패키지
│   ├── state.py              # 상태 정의 (에이전트가 기억하는 것들)
│   ├── nodes.py              # 각 단계의 작업 (이슈 감지, 분석, 수정 등)
│   ├── graph.py              # 작업 흐름 정의
│   ├── agent.py              # 에이전트 메인 클래스
│   ├── cli.py                # 명령줄 인터페이스
│   └── tools/                # 도구 모음
│       ├── k8s.py            # Kubernetes 명령 실행
│       ├── llm.py            # AI 분석 (Gemini)
│       ├── auto_fix.py       # 🆕 자동 수정 도구 모음
│       └── chaos.py          # 🆕 Chaos Engineering (Chaos Mesh)
├── quickstart.py             # 🆕 빠른 시작 스크립트
├── examples_scenarios.py     # 🆕 시나리오별 예제
├── chaos_scenarios.py        # 🆕 Chaos Engineering 시나리오
├── requirements-langgraph.txt # 필요한 라이브러리 목록
├── .env.example              # 환경변수 예시
├── .gitignore                # Git 제외 파일
├── README.md                 # 이 파일
├── QUICKSTART.md             # 🆕 5분 빠른 시작 가이드
├── GUIDE.md                  # 🆕 Python 초보자 가이드
└── CHAOS_GUIDE.md            # 🆕 Chaos Engineering 가이드
```
│   └── tools/                # 도구 모음
│       ├── k8s.py            # Kubernetes 명령 실행
│       ├── llm.py            # AI 분석 (Gemini)
│       └── auto_fix.py       # 🆕 자동 수정 도구 모음
├── quickstart.py             # 🆕 빠른 시작 스크립트
├── examples_scenarios.py     # 🆕 시나리오별 예제
├── requirements-langgraph.txt # 필요한 라이브러리 목록
├── .env.example              # 환경변수 예시
├── .gitignore                # Git 제외 파일
├── README.md                 # 이 파일
├── QUICKSTART.md             # 🆕 5분 빠른 시작 가이드
└── GUIDE.md                  # 🆕 Python 초보자 가이드
```

## 🔄 동작 방식

```
1. [이슈 감지]
   └─ kubectl로 문제 있는 파드 찾기
      (OOMKilled, CrashLoopBackOff, ImagePullBackOff, Pending, NodeIssue)

2. [정보 수집]
   └─ 파드 상세정보, 이벤트, 로그 수집

3. [분석]
   └─ AI 또는 규칙으로 원인 분석
      (Gemini 사용 또는 Mock 모드)

4. [수정 계획 생성]
   └─ 어떻게 고칠지 계획 수립
      (AutoFixer 도구를 사용한 자동 수정)

5. [승인 대기]
   └─ 사용자에게 확인 요청
      (--auto-approve로 건너뛰기 가능)

6. [수정 실행]
   └─ kubectl 명령으로 자동 수정
      (롤백 명령어도 함께 제공)

7. [결과 보고]
   └─ 수정 결과 및 롤백 명령어 제공
```

## 📋 지원하는 이슈 타입

| 이슈 | 설명 | 자동 수정 |
|------|------|----------|
| **OOMKilled** | 메모리 부족 | ✅ 메모리 리미트 2배 증가 |
| **CrashLoopBackOff** | 파드 크래시 반복 | ✅ 재시작 또는 리소스 조정 |
| **ImagePullBackOff** | 이미지 다운로드 실패 | ✅ 이미지 경로 확인/수정 |
| **Pending** | 파드 시작 대기 | ✅ 리소스 조정 또는 노드 추가 |
| **NodeIssue** | 노드 문제 | ℹ️ 노드 상태 확인 및 권장사항 |

## 🔧 자동 수정 도구 (AutoFixer)

새로 추가된 `AutoFixer` 클래스로 다양한 문제를 자동으로 해결할 수 있습니다:

```python
from langgraph_agent.tools.auto_fix import AutoFixer

fixer = AutoFixer(namespace="default")

# 메모리 부족 해결
fixer.fix_oom_issue("pod-name", "container-name", multiplier=2.0)

# CPU 부족 해결
fixer.fix_cpu_throttling("pod-name", "container-name", multiplier=1.5)

# 파드 재시작
fixer.restart_deployment("pod-name")

# 파드 개수 조정
fixer.scale_deployment("pod-name", replicas=5)

# NodeSelector 추가
fixer.add_node_selector("pod-name", {"disktype": "ssd"})
```

또는 간편 함수 사용:

```python
from langgraph_agent.tools.auto_fix import quick_fix_oom, quick_restart

# 빠른 OOM 수정
quick_fix_oom("pod-name", "default", "container-name")

# 빠른 재시작
quick_restart("pod-name", "default")
```

## 🛠️ 코드 수정 가이드

Python을 처음 접하시나요? [GUIDE.md](GUIDE.md)를 확인하세요!

### 새로운 이슈 타입 추가하기

1. [tools/k8s.py](langgraph_agent/tools/k8s.py)의 `get_pods_with_issues()` 함수에 감지 로직 추가
2. [tools/llm.py](langgraph_agent/tools/llm.py)에 분석 함수 추가 (예: `analyze_xxx_issue()`)
3. [nodes.py](langgraph_agent/nodes.py)의 `analyze_issue()`와 `create_fix_plan()`에 처리 추가

### 수정 동작 변경하기

[nodes.py](langgraph_agent/nodes.py)의 `create_fix_plan()` 함수를 수정하거나, [tools/auto_fix.py](langgraph_agent/tools/auto_fix.py)에 새로운 수정 메서드를 추가하세요.

### AI 분석 개선하기

[tools/llm.py](langgraph_agent/tools/llm.py)의 프롬프트를 수정하세요. 더 자세한 지시사항을 추가하면 더 나은 분석을 얻을 수 있습니다.

## 📖 추가 문서

- **[QUICKSTART.md](QUICKSTART.md)** - 5분 안에 시작하는 빠른 가이드
- **[GUIDE.md](GUIDE.md)** - Python 초보자를 위한 상세한 개발 가이드
- **[examples_scenarios.py](examples_scenarios.py)** - 6가지 실전 시나리오 예제

## 🐛 문제 해결

### "GEMINI_API_KEY를 찾을 수 없습니다"

✅ **해결**: Gemini 없이도 동작합니다! Mock 모드로 기본 규칙 기반 분석이 작동합니다.
- 또는 `.env` 파일에 API 키를 추가하세요: `GEMINI_API_KEY=your-key-here`

### "kubectl: command not found"

✅ **해결**: kubectl이 설치되어 있고 PATH에 있는지 확인하세요.
```bash
kubectl version  # 확인
brew install kubectl  # macOS 설치
```

### 이슈가 감지되지 않음

✅ **해결**: 
- 파드 상태 확인: `kubectl get pods -n <namespace>`
- 네임스페이스가 올바른지 확인
- 실제 문제가 있는 파드가 있는지 확인

### "Permission denied" 오류

✅ **해결**: 스크립트에 실행 권한 부여
```bash
chmod +x quickstart.py examples_scenarios.py
```

## 📝 예제

### OOMKilled 파드 자동 수정

```bash
# 간단한 방법
$ ./quickstart.py

# 또는 CLI로
$ python -m langgraph_agent.cli -n default

🤖 dr-kube Agent 시작...
   네임스페이스: default

## 🔍 이슈 분석 결과

**파드**: my-app-xxx (default)
**이슈 타입**: OOMKILLED
**재시작 횟수**: 5

### 근본 원인
메모리 부족으로 OOMKilled 발생 (현재 limit: 256Mi, 재시작: 5회)

## 🔧 수정 계획
**액션**: patch_memory
**대상**: deployment/my-app

**실행 명령어**:
kubectl patch deployment my-app -n default -p '...'

수정을 실행하시겠습니까? (y/n): y

✅ 수정 완료
```

## 🔐 보안 주의사항

- `--auto-approve` 옵션은 주의해서 사용하세요
- 프로덕션 환경에서는 항상 `--dry-run`으로 먼저 확인하세요
- RBAC 권한을 적절히 설정하세요

## 🤝 기여하기

1. 이슈 등록 또는 기능 제안
2. Fork 후 브랜치 생성
3. 코드 작성 (주석 많이!)
4. Pull Request 제출

## 📄 라이선스

MIT

---

**Made with ❤️ by dr-kube team**
