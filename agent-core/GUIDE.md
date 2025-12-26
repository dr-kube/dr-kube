# 개발자 가이드 📘

## 파이썬이 처음이신가요?

괜찮습니다! 이 가이드는 파이썬을 처음 접하는 분들도 코드를 이해하고 수정할 수 있도록 도와드립니다.

## 기본 개념

### 1. 함수 (Function)

```python
def hello(name):
    """이것은 docstring - 함수가 무엇을 하는지 설명"""
    return f"안녕하세요, {name}님!"

# 사용법
result = hello("철수")  # "안녕하세요, 철수님!"
```

### 2. 딕셔너리 (Dictionary)

```python
# 딕셔너리는 키-값 쌍으로 데이터를 저장
person = {
    "name": "홍길동",
    "age": 30,
    "city": "서울"
}

# 값 가져오기
name = person["name"]  # "홍길동"
# 또는
name = person.get("name")  # "홍길동"
```

### 3. 리스트 (List)

```python
# 리스트는 여러 항목을 순서대로 저장
fruits = ["사과", "바나나", "오렌지"]

# 첫 번째 항목
first = fruits[0]  # "사과"

# 리스트에 추가
fruits.append("포도")
```

## 코드 구조 설명

### state.py - 상태 관리

```python
class AgentState(TypedDict):
    """
    에이전트가 기억하는 모든 정보
    TypedDict = 어떤 키(key)가 있고, 각 값(value)의 타입이 무엇인지 정의
    """
    user_query: str  # 사용자가 입력한 질문
    detected_issues: list[IssueInfo]  # 발견된 이슈들의 리스트
    # ... 더 많은 필드들
```

**쉽게 말하면**: 에이전트의 메모장입니다. 각 단계에서 무엇을 발견했고, 어떻게 처리했는지 기록합니다.

### nodes.py - 작업 단계들

```python
def detect_issues(state: AgentState) -> AgentState:
    """
    1단계: 문제 찾기
    
    Args:
        state: 현재 상태 (딕셔너리)
    
    Returns:
        업데이트된 상태 (딕셔너리)
    """
    # 1. 입력에서 필요한 정보 가져오기
    namespace = state.get("target_namespace", "default")
    
    # 2. 실제 작업 수행
    issues = k8s.get_pods_with_issues(namespace)
    
    # 3. 결과를 상태에 저장해서 반환
    return {
        **state,  # 기존 상태 복사 (spread operator)
        "detected_issues": issues  # 새로운 정보 추가/업데이트
    }
```

**쉽게 말하면**: 각 노드는 한 가지 일을 하는 작업자입니다. 입력을 받아서 일을 하고, 결과를 다음 작업자에게 넘깁니다.

### graph.py - 작업 흐름

```python
# 노드 추가 (작업 단계 정의)
graph.add_node("detect_issues", detect_issues)
graph.add_node("collect_info", collect_info)

# 엣지 추가 (작업 순서 정의)
graph.add_edge("detect_issues", "collect_info")
# detect_issues 끝나면 → collect_info 실행
```

**쉽게 말하면**: 작업의 순서를 정의합니다. "이것 하고 → 저것 하고 → 그 다음 이것"

### tools/k8s.py - Kubernetes 명령

```python
def run_kubectl(args: list[str], namespace: Optional[str] = None):
    """kubectl 명령을 실행하는 헬퍼 함수"""
    cmd = ["kubectl"]
    if namespace:
        cmd.extend(["-n", namespace])  # -n 옵션 추가
    cmd.extend(args)  # 나머지 인자 추가
    
    # subprocess = 외부 명령 실행
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout
```

**쉽게 말하면**: 파이썬에서 쉘 명령(kubectl)을 실행하는 방법입니다.

## 자주 사용하는 파이썬 문법

### 1. **state (딕셔너리 복사)

```python
# 기존 딕셔너리를 복사하고 새 값 추가/수정
old_state = {"a": 1, "b": 2}
new_state = {**old_state, "c": 3}
# 결과: {"a": 1, "b": 2, "c": 3}
```

### 2. Optional 타입

```python
from typing import Optional

def greet(name: Optional[str] = None):
    """name은 문자열이거나 None일 수 있음"""
    if name:
        return f"안녕, {name}"
    return "안녕!"
```

### 3. f-string (문자열 포맷팅)

```python
name = "철수"
age = 25
message = f"{name}님은 {age}살입니다."
# "철수님은 25살입니다."
```

### 4. 리스트 컴프리헨션

```python
# 리스트의 각 항목을 변환
numbers = [1, 2, 3, 4, 5]
doubled = [n * 2 for n in numbers]  # [2, 4, 6, 8, 10]

# 조건 필터링
evens = [n for n in numbers if n % 2 == 0]  # [2, 4]
```

## 코드 수정 예제

### 예제 1: 새로운 이슈 타입 추가

**파일**: `tools/k8s.py`

```python
def get_pods_with_issues(namespace: str = "default") -> list[dict]:
    # ... 기존 코드 ...
    
    # 새로운 이슈 타입 추가: DiskPressure
    if pod.get("status", {}).get("phase") == "Running":
        conditions = pod.get("status", {}).get("conditions", [])
        for cond in conditions:
            # DiskPressure 조건이 True면 문제!
            if cond.get("type") == "DiskPressure" and cond.get("status") == "True":
                issues.append({
                    "type": "disk_pressure",
                    "pod_name": pod_name,
                    "namespace": pod_namespace,
                    "container_name": None,
                    "restart_count": 0,
                    "message": "Disk pressure detected"
                })
    
    return issues
```

### 예제 2: 메모리 증가 비율 변경

**파일**: `tools/llm.py`

```python
def analyze_oom_issue(...):
    # 현재: 2배 증가
    new_limit = _format_memory(limit_value * 2)
    
    # 변경: 1.5배 증가 (더 보수적)
    new_limit = _format_memory(int(limit_value * 1.5))
```

### 예제 3: 추가 kubectl 명령 실행

**파일**: `tools/k8s.py`

```python
def describe_pod(pod_name: str, namespace: str = "default") -> str:
    """파드의 상세 정보를 가져옵니다"""
    success, output = run_kubectl(
        ["describe", "pod", pod_name],
        namespace=namespace
    )
    return output if success else "Failed to describe pod"
```

## 디버깅 팁

### 1. print로 값 확인

```python
def my_function(state):
    # 변수 값 확인하기
    print(f"현재 상태: {state}")
    print(f"이슈 개수: {len(state.get('detected_issues', []))}")
    
    # 계속 진행...
    return state
```

### 2. 에러 메시지 읽기

```
Traceback (most recent call last):
  File "nodes.py", line 42, in detect_issues
    issues = k8s.get_pods_with_issues(namespace)
  File "tools/k8s.py", line 55, in get_pods_with_issues
    pods_data = json.loads(output)
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**읽는 방법**:
- 아래에서 위로 읽기
- 마지막 줄이 실제 에러: `json.JSONDecodeError`
- 그 위 줄들이 에러가 발생한 위치

### 3. try-except로 에러 처리

```python
try:
    # 에러가 날 수 있는 코드
    result = some_risky_operation()
except Exception as e:
    # 에러 발생 시 처리
    print(f"에러 발생: {e}")
    result = "기본값"
```

## 다음 단계

1. **작은 변경부터 시작**: 메시지 텍스트 변경, 기본값 수정 등
2. **테스트**: 변경 후 항상 실행해서 확인
3. **로그 추가**: `print()`로 무슨 일이 일어나는지 확인
4. **질문하기**: 이해 안 되는 부분은 주저 말고 질문!

## 유용한 리소스

- [Python 공식 튜토리얼](https://docs.python.org/ko/3/tutorial/)
- [LangGraph 문서](https://langchain-ai.github.io/langgraph/)
- [Kubernetes Python Client](https://github.com/kubernetes-client/python)

## 자주 묻는 질문

**Q: `**state`가 뭔가요?**
A: 딕셔너리의 모든 내용을 "펼쳐서" 복사하는 문법입니다. `{**state, "new_key": "value"}`는 기존 state의 모든 키-값을 복사하고 new_key를 추가합니다.

**Q: Type hints (`: str`, `-> AgentState`)가 뭔가요?**
A: 타입을 명시하는 것입니다. 실행에는 영향 없지만, 코드를 읽기 쉽게 하고 에디터가 자동완성을 도와줍니다.

**Q: `Optional[str]`이 뭔가요?**
A: "문자열이거나 None일 수 있음"을 의미합니다. `str | None`과 같습니다.

**Q: lambda가 뭔가요?**
A: 간단한 익명 함수입니다.
```python
# lambda
double = lambda x: x * 2

# 위와 동일한 일반 함수
def double(x):
    return x * 2
```
