# OOMKilled Agent 🤖

Kubernetes 클러스터에서 OOMKilled 이슈를 자동으로 감지하고 분석하여 해결책을 제시하는 LangChain 기반 AI 에이전트입니다.

## 주요 기능

- 🔍 **자동 감지**: OOMKilled 상태의 파드를 자동으로 찾아냅니다
- 📊 **상세 분석**: 파드의 리소스 설정, 로그, 이벤트를 종합적으로 분석합니다
- 💡 **AI 권장사항**: Gemini 또는 GPT-4를 활용하여 적절한 메모리 리미트와 해결책을 제시합니다
- 🔧 **수정 가이드**: Deployment 수정 방법을 구체적으로 안내합니다
- 🔀 **다중 LLM 지원**: Google Gemini와 OpenAI GPT를 선택해서 사용 가능

## 아키텍처

```
agent-core/
├── agents/           # LangChain 에이전트 로직
├── tools/            # K8s API 호출 도구들
├── prompts/          # LLM 프롬프트
├── examples/         # 사용 예제
├── config.py         # 설정
└── main.py          # CLI 진입점
```

## 사전 요구사항

- Python 3.9+
- Kubernetes 클러스터 접근 권한
- LLM API 키:
  - **Gemini API 키** (권장, 무료): https://makersuite.google.com/app/apikey
  - 또는 **OpenAI API 키**: https://platform.openai.com/api-keys

## 설치 및 설정

### 1. 가상환경 생성

```bash
cd agent-core
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정

`.env` 파일을 생성하고 다음 내용을 추가합니다:

```bash
cp .env.example .env
```

`.env` 파일 편집:

#### 옵션 A: Gemini 사용 (기본값, 권장)

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-1.5-pro
KUBECONFIG=~/.kube/config
```

Gemini API 키는 https://makersuite.google.com/app/apikey 에서 무료로 발급받을 수 있습니다.

#### 옵션 B: OpenAI 사용

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
KUBECONFIG=~/.kube/config
```

### 4. Kubernetes 접근 확인

```bash
kubectl cluster-info
kubectl get pods -n default
```

## 사용 방법

### CLI 사용

#### 1. 네임스페이스의 모든 OOMKilled 파드 분석 (Gemini 사용)

```bash
python main.py -n default
```

#### 2. 특정 파드 분석

```bash
python main.py -n default -p oom-test
```

#### 3. 수정 방법 가이드 받기

```bash
python main.py -n default -p oom-test --fix
```

#### 4. OpenAI 사용하기

```bash
python main.py -n default --provider openai
```

#### 5. 다른 모델 사용

```bash
# Gemini Pro 1.5 사용
python main.py -n default --provider gemini --model gemini-1.5-pro

# GPT-3.5 사용
python main.py -n default --provider openai --model gpt-3.5-turbo
```

### Python 코드에서 사용

#### 기본 사용법 (Gemini)

```python
from agents import OOMKilledAgent
from config import GEMINI_API_KEY

# Gemini 에이전트 초기화
agent = OOMKilledAgent(
    api_key=GEMINI_API_KEY,
    model_name="gemini-1.5-pro",
    provider="gemini"
)

# 모든 OOMKilled 파드 분석
result = agent.analyze_oomkilled_pods(namespace="default")
print(result)

# 특정 파드 분석
result = agent.analyze_specific_pod("oom-test", "default")
print(result)

# 수정 방법 가이드
result = agent.get_fix_instructions("oom-test", "default")
print(result)
```

#### OpenAI 사용법

```python
from agents import OOMKilledAgent
from config import OPENAI_API_KEY

# OpenAI 에이전트 초기화
agent = OOMKilledAgent(
    api_key=OPENAI_API_KEY,
    model_name="gpt-4-turbo-preview",
    provider="openai"
)

# 사용법은 위와 동일
result = agent.analyze_specific_pod("oom-test", "default")
print(result)
```

#### 커스텀 쿼리

```python
from agents import OOMKilledAgent
from config import LLM_PROVIDER, GEMINI_API_KEY, OPENAI_API_KEY

# Provider에 따라 에이전트 생성
if LLM_PROVIDER == "gemini":
    agent = OOMKilledAgent(api_key=GEMINI_API_KEY, provider="gemini")
else:
    agent = OOMKilledAgent(api_key=OPENAI_API_KEY, provider="openai")

custom_query = """
default 네임스페이스에서 scenario=oom-killed 레이블을 가진 파드를 찾아서
메모리 사용 패턴을 분석하고 최적의 리소스 설정을 추천해줘.
"""

result = agent.agent.invoke({"input": custom_query})
print(result["output"])
```

## 예제

### 기본 예제 실행

```bash
cd examples
python basic_usage.py
```

### 고급 예제 실행

```bash
python advanced_usage.py
```

## 에이전트 작동 방식

1. **OOMKilled 파드 감지**
   - Kubernetes API를 통해 OOMKilled 상태의 파드를 찾습니다
   - 컨테이너 상태와 재시작 횟수를 확인합니다

2. **정보 수집**
   - 파드의 리소스 설정 (requests, limits)
   - Kubernetes 이벤트 (OOMKilled 발생 시점)
   - 컨테이너 로그 (메모리 할당 패턴)

3. **AI 분석**
   - GPT-4가 수집된 정보를 종합적으로 분석
   - 메모리 부족의 원인 파악 (메모리 누수, 스파이크 등)
   - 적절한 메모리 리미트 계산

4. **해결책 제시**
   - 추천 메모리 리미트
   - Deployment 수정 방법
   - 추가 최적화 제안

## 테스트

OOM 테스트 파드를 배포하여 에이전트를 테스트할 수 있습니다:

```bash
# OOM 테스트 파드 배포
kubectl apply -f ../manifests/oom-test.yaml

# 파드가 OOMKilled 될 때까지 대기
kubectl get pods -w

# 에이전트로 분석
python main.py -n default -p oom-test
```

## LLM Provider 비교

| 특징 | Gemini | OpenAI |
|------|--------|--------|
| **가격** | 무료 티어 제공 (월 60 요청/분) | 유료 (토큰당 과금) |
| **성능** | Gemini 1.5 Pro - 우수 | GPT-4 Turbo - 최고 |
| **컨텍스트 윈도우** | 2M 토큰 (매우 크다!) | 128K 토큰 |
| **한국어 지원** | 우수 | 우수 |
| **추천 용도** | 테스트, 개발, 무료 사용 | 프로덕션, 최고 성능 필요 시 |

**권장사항**: 개발 및 테스트 단계에서는 Gemini를 사용하고, 프로덕션 배포 시 성능이 중요하다면 OpenAI를 고려하세요.

## 도구 (Tools)

에이전트가 사용하는 Kubernetes 도구들:

| 도구 | 설명 |
|------|------|
| `get_oomkilled_pods` | OOMKilled 파드 목록 조회 |
| `get_pod_details` | 파드 상세 정보 조회 |
| `get_pod_logs` | 컨테이너 로그 조회 |
| `get_pod_events` | Kubernetes 이벤트 조회 |
| `suggest_resource_update` | 리소스 업데이트 가이드 |

## 향후 Go 마이그레이션

이 프로젝트는 Python으로 프로토타입을 만들고, 추후 Go로 포팅할 예정입니다.

Go 버전에서 고려할 사항:
- `client-go` 라이브러리 사용
- Gemini/OpenAI API 직접 호출 또는 LangChain Go 포트 사용
- 성능 최적화 및 동시성 처리
- 바이너리 배포로 간편한 설치

## 문제 해결

### "No module named 'kubernetes'" 에러
```bash
pip install -r requirements.txt
```

### Kubernetes 연결 에러
```bash
# kubeconfig 확인
echo $KUBECONFIG
kubectl cluster-info

# 또는 .env에서 KUBECONFIG 경로 수정
```

### Gemini API 에러
```bash
# API 키 확인
cat .env | grep GEMINI_API_KEY

# 또는 환경변수로 설정
export GEMINI_API_KEY=your-key
```

### OpenAI API 에러
```bash
# API 키 확인
cat .env | grep OPENAI_API_KEY

# 또는 환경변수로 설정
export OPENAI_API_KEY=sk-your-key
```

### Provider 변경하기
```bash
# .env 파일에서 LLM_PROVIDER 변경
LLM_PROVIDER=gemini  # 또는 openai

# 또는 CLI에서 직접 지정
python main.py -n default --provider gemini
```

## 라이선스

MIT

## 기여

이슈와 PR을 환영합니다!
