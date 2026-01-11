# LangGraph 노드 추가 가이드

새로운 노드를 워크플로우에 추가하는 방법을 안내합니다.

## 인자
- $ARGUMENTS: 노드 이름과 설명 (예: "collect_logs 로그 수집 노드")

## 단계

### 1. state.py에 필요한 필드 추가
```python
class IssueState(TypedDict, total=False):
    # 기존 필드...
    new_field: str  # 새 필드 추가
```

### 2. graph.py에 노드 함수 작성
```python
def new_node(state: IssueState) -> IssueState:
    """노드 설명 (한국어)"""
    if state.get("error"):
        return state

    # 로직 수행
    return {"new_field": "value", "status": "상태명"}
```

### 3. create_graph()에 등록
```python
workflow.add_node("new_node", new_node)
workflow.add_edge("이전노드", "new_node")
workflow.add_edge("new_node", "다음노드")
```

## 주의사항
- 에러 전파 패턴 유지: `if state.get("error"): return state`
- status 필드 업데이트
- 반환값은 IssueState 타입
