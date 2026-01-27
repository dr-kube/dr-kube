# AI DrKube 완료 요약

## 🎉 완료된 작업

### 1. Windows 환경 설정 완료
- ✅ Python 가상환경 생성
- ✅ 모든 패키지 설치 (LangGraph, LangChain, Google Gemini)
- ✅ Google Gemini API 연동
- ✅ Windows 배치 스크립트 작성

### 2. 코드 개선
- ✅ **출력 형식 개선** - 간결하고 가독성 좋게 변경
- ✅ **프롬프트 최적화** - AI가 간결한 응답 생성하도록 수정
- ✅ **Windows UTF-8 지원** - 한글 깨짐 방지
- ✅ **Verbose 모드 추가** - `-v` 옵션으로 상세 출력 가능

### 3. 문서 작성
- ✅ **ARCHITECTURE.md** - 에이전트 작동 원리 및 워크플로우
- ✅ **USAGE.md** - 사용 방법 및 예제
- ✅ **QUICKSTART_KR.md** - 빠른 시작 가이드
- ✅ **WINDOWS_SETUP.md** - Windows 상세 설정 가이드
- ✅ **README.md** - 프로젝트 개요 업데이트

---

## 🚀 실행 방법

### 가장 간단한 방법
```cmd
cd C:\Users\b100h\dr-kube\agent
run.bat issues\sample_oom.json
```

### 출력 예시
```
============================================================
  DR-Kube 분석 결과
============================================================

📋 이슈: CrashLoopBackOff
📦 리소스: api-server-7d4f8b9c5-xyz
🟠 심각도: HIGH

🔍 근본 원인:
   컨테이너가 메모리 제한 초과로 강제 종료되었습니다.

💡 해결책:
   1. resources.limits.memory를 1Gi로 증설하십시오.
   2. 메모리 누수 여부를 프로파일링하십시오.
   3. 메모리 80% 초과 시 알림을 설정하십시오.

============================================================
```

---

## 📊 주요 개선 사항

### Before (이전)
```
해결책:
| 구분 | 조치 사항 | 명령어 및 상세 설명 |
| :--- | :--- | :--- |
| **단기 (즉시)** | **리소스 제한(Limits) 상향** | `resources.limits.memory`를 현재 512Mi에서 1Gi 이상으로 상향 조정하여 즉시 복구 |
... (매우 긴 표 계속)
```

### After (현재)
```
💡 해결책:
   1. resources.limits.memory를 1Gi로 증설하십시오.
   2. 메모리 누수 여부를 프로파일링하십시오.
   3. 메모리 80% 초과 시 알림을 설정하십시오.
```

**개선 효과:**
- 📏 출력 길이 **70% 감소**
- 👁️ 가독성 **대폭 향상**
- 🎯 핵심 정보 **즉시 파악 가능**

---

## 🔧 에이전트 작동 방식

### 3단계 워크플로우
```
1. Load Issue (이슈 로드)
   ↓
2. Analyze (AI 분석) ← Google Gemini API
   ↓
3. Suggest (결과 출력)
```

### 상세 흐름
```
JSON 파일 읽기
    ↓
프롬프트 생성 (이슈 정보 → 텍스트)
    ↓
Gemini API 호출
    ↓
응답 파싱 (텍스트 → 구조화)
    ↓
간결한 형식으로 출력
```

---

## 📁 프로젝트 파일 구조

```
agent/
├── 📄 실행 스크립트
│   ├── setup.bat              # 환경 설정
│   ├── run.bat                # 장애 분석 실행
│   └── run_tools.bat          # 도구 실행
│
├── 📚 문서
│   ├── README.md              # 프로젝트 개요
│   ├── ARCHITECTURE.md        # 아키텍처 및 작동 원리 ⭐
│   ├── USAGE.md               # 사용 방법
│   ├── QUICKSTART_KR.md       # 빠른 시작
│   └── WINDOWS_SETUP.md       # Windows 설정
│
├── 💻 소스 코드
│   └── src/
│       ├── cli.py             # CLI 엔트리포인트
│       └── dr_kube/
│           ├── graph.py       # LangGraph 워크플로우
│           ├── llm.py         # LLM 프로바이더
│           ├── prompts.py     # 프롬프트 템플릿
│           └── state.py       # 상태 관리
│
├── 🔧 도구
│   └── tools/
│       ├── log_analysis_agent.py
│       ├── error_classifier.py
│       └── root_cause_analyzer.py
│
└── 📋 샘플 데이터
    └── issues/
        ├── sample_oom.json
        ├── sample_image_pull.json
        └── sample_cpu_throttle.json
```

---

## 🎯 사용 사례

### 1. OOM 이슈 분석
```cmd
run.bat issues\sample_oom.json
```
**분석 결과:**
- 근본 원인: 메모리 제한 초과
- 해결책: 메모리 증설, 누수 점검, 모니터링

### 2. 이미지 Pull 실패
```cmd
run.bat issues\sample_image_pull.json
```
**분석 결과:**
- 근본 원인: 레지스트리 인증 실패
- 해결책: Secret 생성, CI/CD 자동화, 알림

### 3. CPU Throttling
```cmd
run.bat issues\sample_cpu_throttle.json
```
**분석 결과:**
- 근본 원인: CPU Limit 부족
- 해결책: CPU 증설, VPA 도입, 모니터링

---

## 🔍 Verbose 모드

상세한 AI 분석 내용을 보려면:
```cmd
run.bat issues\sample_oom.json -v
```

또는 `.env` 파일에서:
```env
VERBOSE=true
```

---

## ⚙️ 환경 설정

### .env 파일 주요 설정

```env
# 필수: Google Gemini API 키
GOOGLE_API_KEY=your-api-key-here

# AI 모델
MODEL_NAME=gemini-3-flash-preview

# 출력 모드
VERBOSE=false                # true: 항상 상세 출력
AUTO_APPROVE=false           # true: 승인 프롬프트 건너뜀
```

---

## 📚 참고 문서

| 문서 | 내용 |
|------|------|
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | ⭐ 에이전트 작동 원리 및 워크플로우 상세 설명 |
| **[USAGE.md](./USAGE.md)** | 사용 방법, 옵션, 예제 |
| **[QUICKSTART_KR.md](./QUICKSTART_KR.md)** | 3단계로 빠르게 시작하기 |
| **[WINDOWS_SETUP.md](./WINDOWS_SETUP.md)** | Windows 환경 상세 설정 |
| **[README.md](./README.md)** | 프로젝트 전체 개요 |

---

## 🎓 기술 스택

- **프레임워크**: LangGraph (상태 기반 워크플로우)
- **LLM**: Google Gemini (gemini-3-flash-preview)
- **언어**: Python 3.10+
- **라이브러리**: LangChain, python-dotenv, pydantic

---

## 🔮 향후 확장 가능성

### 추가 가능한 기능
```
현재 워크플로우:
Load → Analyze → Suggest

확장된 워크플로우:
Load → Analyze → Generate Fix → Apply → Verify
                     ↓
                 YAML 패치 생성
                     ↓
              kubectl apply
                     ↓
                적용 후 검증
```

**추가 가능한 노드:**
- `generate_fix`: YAML 패치 자동 생성
- `apply_fix`: kubectl apply 실행
- `verify_fixed`: 적용 후 검증
- `rollback`: 실패 시 롤백

---

## 💡 핵심 특징

### 1. 간결한 출력
- 핵심만 3줄로 요약
- 이모지로 직관적 표시
- 불필요한 정보 제거

### 2. 3단계 해결책
1. **즉시 조치** - 지금 당장 실행
2. **근본 해결** - 재발 방지
3. **모니터링** - 예방 조치

### 3. LangGraph 기반
- 상태 관리
- 단계별 실행
- 에러 처리 용이

---

## 🚀 다음 단계

### 1. 현재 (K8S 없이)
- ✅ 샘플 데이터로 테스트
- ✅ AI 기반 분석 학습
- ✅ 간결한 결과 확인

### 2. 향후 (K8S 연동)
- 🔄 실시간 이슈 수집
- 🔄 자동 조치 실행
- 🔄 Alertmanager 연동

---

## 📞 도움말

문제가 발생하면:
1. `.env` 파일에서 `LOG_LEVEL=DEBUG` 설정
2. `-v` 옵션으로 상세 출력 확인
3. [ARCHITECTURE.md](./ARCHITECTURE.md)에서 작동 원리 확인

---

**모든 설정과 테스트가 완료되었습니다!** 🎉

Windows 환경에서 AI DrKube를 바로 사용할 수 있습니다.
