# DR-Kube AI Agent

Kubernetes 장애 분석 및 자동 복구 AI Agent

LangGraph를 사용하여 Kubernetes 환경에서 다양한 장애 상황을 감지, 분석, 자동 복구하는 AI Agent입니다.

## 🎯 주요 기능

- **로그 수집**: Loki, Alloy, 로컬 파일에서 로그 수집
- **에러 분류**: LLM을 활용한 자동 에러 카테고리 분류
- **근본 원인 분석**: 장애의 근본 원인을 AI로 분석
- **자동 복구**: values.yaml 수정 및 GitOps를 통한 자동 복구
- **복구 검증**: 복구 작업 성공 여부 확인

## 🏗️ 아키텍처

```
로그 수집 → 에러 분류 → 근본 원인 분석 → 사용자 피드백 → 액션 생성 → Git 커밋 → 복구 검증 → 최종 피드백
```

### 워크플로우

1. **로그 수집**: Loki API, Alloy Webhook, 또는 로컬 파일에서 로그 수집
2. **에러 분류**: 키워드 및 LLM 기반 에러 카테고리 분류
3. **근본 원인 분석**: Google Gemini API를 활용한 원인 분석
4. **사용자 피드백**: 분석 결과 표시 (Phase 1: 자동 승인)
5. **액션 생성**: values.yaml 수정 사항 생성
6. **Git 커밋**: 변경사항 커밋 (Phase 1: 시뮬레이션)
7. **복구 검증**: Kubernetes 리소스 상태 확인
8. **최종 피드백**: 사용자에게 최종 결과 보고

## 📋 요구사항

- Python 3.10+
- Kubernetes 클러스터 접근 권한
- Google Gemini API 키
- (선택) Loki 서버 접근
- (선택) Git 저장소 접근

## 🚀 설치

### 1. 환경 설정

```bash
# 가상환경 생성
cd ./dr-kube/_backup/taebin-ai-agent-v2
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows

# 패키지 설치
cd ./agent
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 필요한 값들을 설정하세요:

```bash
cp .env.example .env
```

`.env` 파일 내용:
```env
GOOGLE_API_KEY=your_google_api_key_here
KUBECONFIG_PATH=/path/to/kubeconfig  # 선택사항
LOKI_URL=http://localhost:3100
GIT_REPO_PATH=/path/to/git/repository
ARGOCD_APP_NAME=application-name
LOG_LEVEL=INFO
```

### 3. Google Gemini API 키 발급

1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
2. API 키 생성
3. `.env` 파일에 `GOOGLE_API_KEY` 설정

## 💻 사용법

### 기본 사용 (로컬 로그 파일)

```bash
python -m src.cli --log-file /path/to/logfile.txt \
  --namespace default \
  --resource-type Pod \
  --resource-name my-pod
```

### Loki에서 로그 수집

```bash
python -m src.cli --loki \
  --namespace default \
  --resource-type Pod \
  --resource-name my-pod
```

### 전체 네임스페이스에서 조회

```bash
# 모든 namespace에서 특정 Pod 조회
python -m src.cli --log-file /path/to/logfile.txt \
  --all-namespaces \
  --resource-type Pod \
  --resource-name my-pod

# 모든 namespace에서 특정 Deployment 조회
python -m src.cli --log-file /path/to/logfile.txt \
  --all-namespaces \
  --resource-type Deployment \
  --resource-name my-deployment
```

### 시뮬레이션 모드 (실제 Git 커밋 안 함)

```bash
python -m src.cli --log-file /path/to/logfile.txt --dry-run
```

## 📁 프로젝트 구조

```
agent/
├── src/
│   ├── dr_kube/          # 메인 패키지
│   │   ├── __init__.py
│   │   ├── graph.py      # LangGraph 워크플로우 정의
│   │   ├── state.py      # 상태 모델 (TypedDict)
│   │   ├── llm.py        # LLM 클라이언트 래퍼
│   │   ├── prompts.py    # 프롬프트 템플릿
│   │   ├── nodes/        # 워크플로우 노드
│   │   │   ├── collect_logs.py
│   │   │   ├── classify_error.py
│   │   │   ├── analyze_root_cause.py
│   │   │   ├── generate_action.py
│   │   │   └── verify_recovery.py
│   │   └── services/    # 외부 서비스 연동
│   │       ├── kubernetes_client.py
│   │       ├── loki_client.py
│   │       └── git_client.py
│   ├── cli.py            # CLI 인터페이스
│   └── tools/            # 유틸리티 도구
│       └── logger.py
├── tests/                # 테스트 코드
├── README.md
├── requirements.txt
└── .env.example
```

## 🔧 지원하는 장애 유형

- **oom**: Out of Memory 에러
- **crashloop**: CrashLoopBackOff 에러
- **config_error**: 설정 파일 오류
- **resource_exhausted**: 리소스 부족
- **network_error**: 네트워크 연결 오류
- **image_pull_error**: 이미지 풀 실패
- **scheduling_error**: 스케줄링 실패

## 📝 Phase 1 제한사항

현재 버전은 Phase 1로, 다음 기능들이 시뮬레이션 모드로 동작합니다:

- 사용자 피드백: 자동 승인
- Git 커밋: 시뮬레이션만 (실제 커밋 안 함)
- 복구 검증: 시뮬레이션만

실제 Git 커밋/푸시를 활성화하려면 각 서비스 파일의 주석을 해제하세요.

## 🧪 테스트

```bash
# 테스트 실행
pytest tests/

# 특정 테스트만 실행
pytest tests/test_graph.py
```

## 📚 문서

- [프롬프트 작성 가이드](../docs/prompt_example.md)
- [프로젝트 히스토리](../docs/history.md)

## 🤝 기여

이슈나 Pull Request를 환영합니다!

## 📄 라이선스

MIT License
