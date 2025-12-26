# 🎉 완료! dr-kube LangGraph Agent

Kubernetes 클러스터의 문제를 자동으로 감지하고 수정하는 AI 에이전트가 완성되었습니다!

## ✅ 설치 확인

```bash
# 설치 테스트 실행
python test_installation.py

# 결과:
# 🎉 모든 테스트 통과! (5/5)
# ✅ dr-kube 에이전트가 정상적으로 설치되었습니다!
```

## 🚀 지금 바로 시작하기

### 방법 1: 가장 빠른 방법 (추천!)

```bash
./quickstart.py
```

자동으로:
- 클러스터의 문제를 찾습니다
- AI로 분석합니다
- 수정 방법을 제안합니다
- 승인하면 자동으로 수정합니다

### 방법 2: 시나리오 예제

```bash
./examples_scenarios.py
```

6가지 시나리오를 보여줍니다:
1. OOMKilled 자동 수정
2. CPU Throttling 해결
3. CrashLoopBackOff 재시작
4. 파드 개수 증가
5. NodeSelector 추가
6. 여러 문제 일괄 수정

### 방법 3: CLI 명령어

```bash
# 기본 사용
python -m langgraph_agent.cli

# 네임스페이스 지정
python -m langgraph_agent.cli -n production

# 시뮬레이션 (실제로 수정하지 않음)
python -m langgraph_agent.cli --dry-run
```

## 📚 문서

- **[README.md](README.md)** - 전체 프로젝트 설명
- **[QUICKSTART.md](QUICKSTART.md)** - 5분 빠른 시작 가이드
- **[GUIDE.md](GUIDE.md)** - Python 초보자 가이드
- **[SUMMARY.md](SUMMARY.md)** - 프로젝트 요약

## 🎯 주요 기능

### 1. 5가지 이슈 자동 감지
- ✅ OOMKilled (메모리 부족)
- ✅ CrashLoopBackOff (크래시 반복)
- ✅ ImagePullBackOff (이미지 다운로드 실패)
- ✅ Pending (파드 시작 대기)
- ✅ NodeIssue (노드 문제)

### 2. AI 분석 (Gemini)
- Gemini 2.0-flash 모델
- Mock 모드 지원 (API 키 없이도 작동)
- 규칙 기반 폴백

### 3. 자동 수정 도구
- 메모리/CPU 리소스 조정
- 파드 재시작
- 파드 개수 조정
- NodeSelector 추가
- 이미지 변경

### 4. 안전 장치
- 승인 단계 필수
- 시뮬레이션 모드 (--dry-run)
- 롤백 명령어 자동 제공

## 💡 사용 예제

### 간단한 사용

```python
from langgraph_agent.agent import DrKubeAgent

# 에이전트 생성
agent = DrKubeAgent(namespace="default")

# 분석 실행
result = agent.analyze()
print(result["response"])

# 수정 승인
if result.get("fix_plan"):
    result = agent.approve_fix()
```

### AutoFixer 직접 사용

```python
from langgraph_agent.tools.auto_fix import quick_fix_oom, quick_restart

# OOM 문제 빠른 수정
quick_fix_oom("pod-name", "default", "container-name")

# 파드 재시작
quick_restart("pod-name", "default")
```

## 🔧 커스터마이징

### 새로운 이슈 타입 추가

1. `tools/k8s.py` - 감지 로직 추가
2. `tools/llm.py` - 분석 함수 추가
3. `nodes.py` - 처리 로직 추가

자세한 내용은 [GUIDE.md](GUIDE.md)를 참고하세요.

## ❓ FAQ

**Q: API 키가 필요한가요?**  
A: 아니요! Mock 모드로 기본 분석이 가능합니다.

**Q: 프로덕션에 바로 사용해도 되나요?**  
A: 먼저 `--dry-run`으로 테스트하세요.

**Q: 잘못된 수정을 했어요!**  
A: 출력된 롤백 명령어를 실행하면 복구됩니다.

**Q: Python을 잘 모르는데요?**  
A: [GUIDE.md](GUIDE.md)에 Python 기본 개념이 설명되어 있습니다.

## 📊 프로젝트 정보

- **파일 수**: 20개
- **코드 라인**: ~2,500줄
- **지원 이슈**: 5가지
- **자동 수정**: 6가지 메서드
- **문서**: 4개 가이드

## 🎓 학습 경로

### 초급 (1-2일)
1. quickstart.py 실행
2. CLI 명령어 사용
3. 시나리오 예제 실행

### 중급 (1주)
1. GUIDE.md 읽기
2. 코드 구조 이해
3. 간단한 수정 시도

### 고급 (2-3주)
1. 새로운 이슈 타입 추가
2. AutoFixer 메서드 추가
3. 프로덕션 배포

## 🤝 기여

개선 아이디어나 버그 리포트는 언제든지 환영합니다!

1. Issue 생성
2. Pull Request 제출
3. 피드백 공유

## 📝 다음 단계

1. ✅ **설치 확인**: `python test_installation.py`
2. ✅ **첫 실행**: `./quickstart.py`
3. ✅ **문서 읽기**: [QUICKSTART.md](QUICKSTART.md)
4. ✅ **시나리오 테스트**: `./examples_scenarios.py`
5. ✅ **커스터마이징**: [GUIDE.md](GUIDE.md) 참고

---

**Happy Kubernetes Troubleshooting! 🚀**

문제가 있으면 GUIDE.md의 "문제 해결" 섹션을 확인하세요.
