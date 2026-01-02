# 🚀 빠른 시작 가이드

## 5분 안에 시작하기

### 1단계: 설치 (1분)

```bash
cd agent-core

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements-langgraph.txt
```

### 2단계: 환경 설정 (1분)

```bash
# API 키 설정 (선택사항 - 없어도 Mock 모드로 작동)
cp .env.example .env
# .env 파일을 열어서 GEMINI_API_KEY를 입력하세요
```

**중요**: API 키가 없어도 됩니다! Mock 모드로 작동합니다.

### 3단계: 실행 (1분)

#### 방법 1: 빠른 시작 스크립트

가장 간단한 방법입니다:

```bash
./quickstart.py
```

자동으로:
- 클러스터의 문제를 찾습니다
- 분석 결과를 보여줍니다
- 수정 여부를 물어봅니다
- 승인하면 자동으로 수정합니다

#### 방법 2: CLI 명령어

더 많은 옵션이 필요하면:

```bash
# 기본 사용
python -m langgraph_agent.cli

# 특정 네임스페이스 지정
python -m langgraph_agent.cli -n production

# 특정 파드만 분석
python -m langgraph_agent.cli -p my-app-xxx

# 자동 승인 (테스트용)
python -m langgraph_agent.cli --auto-approve

# 시뮬레이션 (실제로 수정하지 않음)
python -m langgraph_agent.cli --dry-run
```

#### 방법 3: Python 코드로 사용

```python
from langgraph_agent.agent import DrKubeAgent

# 에이전트 생성
agent = DrKubeAgent(namespace="default")

# 분석 실행
result = agent.analyze(auto_approve=False)
print(result["response"])

# 수정 승인
if result.get("fix_plan"):
    result = agent.approve_fix()
    print(result["response"])
```

---

## 📖 시나리오별 사용법

### 시나리오 1: OOMKilled 자동 수정

```bash
# 빠른 시작 스크립트로 실행
./quickstart.py

# 또는 직접 코드로
python -c "
from langgraph_agent.tools.auto_fix import quick_fix_oom
quick_fix_oom('my-pod-xxx', 'default', 'my-container')
"
```

### 시나리오 2: 여러 문제 한번에 해결

```bash
# 예제 스크립트 실행
./examples_scenarios.py
```

이 스크립트는 6가지 시나리오를 보여줍니다:
1. OOMKilled 자동 수정
2. CPU Throttling 해결
3. CrashLoopBackOff 재시작
4. 파드 개수 증가
5. NodeSelector 추가
6. 여러 문제 일괄 수정

### 시나리오 3: 프로덕션 환경 사용

```bash
# 시뮬레이션 먼저 (안전)
python -m langgraph_agent.cli -n production --dry-run

# 문제 없으면 실행
python -m langgraph_agent.cli -n production
```

---

## 🔧 고급 사용법

### AutoFixer 직접 사용

```python
from langgraph_agent.tools.auto_fix import AutoFixer

# AutoFixer 인스턴스 생성
fixer = AutoFixer(namespace="default")

# 메모리 2배 증가
fixer.fix_oom_issue("pod-name", "container-name", multiplier=2.0)

# CPU 1.5배 증가
fixer.fix_cpu_throttling("pod-name", "container-name", multiplier=1.5)

# 파드 재시작
fixer.restart_deployment("pod-name")

# 파드 개수 조정
fixer.scale_deployment("pod-name", replicas=5)

# NodeSelector 추가
fixer.add_node_selector("pod-name", {"disktype": "ssd"})
```

### 커스텀 워크플로우

```python
from langgraph_agent.graph import create_agent_graph

# 그래프 생성
graph = create_agent_graph()

# 초기 상태 설정
initial_state = {
    "namespace": "default",
    "pod_name": None,
    "issues": [],
    "approval_status": "pending",
}

# 실행
result = graph.invoke(initial_state)
```

---

## ❓ 자주 묻는 질문

### Q: API 키가 없으면 어떻게 되나요?

**A**: Mock 모드로 자동 전환됩니다. 규칙 기반 분석을 사용하여 간단한 문제는 해결할 수 있습니다.

### Q: 실수로 잘못된 수정을 하면 어떻게 하나요?

**A**: 각 수정마다 롤백 명령어가 출력됩니다. 그 명령어를 실행하면 되돌릴 수 있습니다.

```bash
# 롤백 예시
kubectl rollout undo deployment/my-app -n default
```

### Q: 어떤 문제들을 자동으로 해결할 수 있나요?

**A**: 현재 지원하는 문제들:
- OOMKilled (메모리 부족)
- CrashLoopBackOff (크래시 반복)
- ImagePullBackOff (이미지 다운로드 실패)
- Pending (파드 시작 대기)
- NodeNotReady (노드 문제)

### Q: 프로덕션 환경에 바로 사용해도 되나요?

**A**: 권장하지 않습니다. 먼저:
1. `--dry-run`으로 시뮬레이션
2. 개발/스테이징 환경에서 테스트
3. 충분히 검증 후 프로덕션 적용

### Q: 문제가 생기면 어떻게 하나요?

**A**: 
1. `--dry-run`으로 문제 확인
2. GUIDE.md의 디버깅 섹션 참조
3. GitHub Issues에 문의

---

## 📚 더 자세한 문서

- [README.md](README.md) - 전체 프로젝트 설명
- [GUIDE.md](GUIDE.md) - 개발자 가이드 (Python 초보자용)
- [examples_scenarios.py](examples_scenarios.py) - 시나리오별 예제 코드

---

## 🎯 다음 단계

1. ✅ quickstart.py로 기본 기능 테스트
2. ✅ examples_scenarios.py로 다양한 시나리오 확인
3. ✅ 실제 클러스터에 적용
4. ✅ 필요에 맞게 커스터마이징

**팁**: 처음에는 `--dry-run` 옵션을 사용하여 안전하게 테스트하세요!
