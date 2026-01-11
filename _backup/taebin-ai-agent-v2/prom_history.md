### dr-kube ai agent의 workflow 구상
1. **로그 수집**: 로컬 파일 또는 외부 소스에서 로그 수집
2. **에러 분류**: 키워드 기반 에러 카테고리 분류
3. **근본 원인 분석**: 에러 카테고리 기반 원인 분석
4. **사용자 피드백**: 분석 결과를 사용자에게 표시 (Phase 1: 자동 승인)
5. **액션 생성**: Git 변경사항 생성
6. **Git 커밋**: 변경사항 커밋 (Phase 1: 시뮬레이션)
7. **복구 검증**: 복구 결과 확인 (Phase 1: 시뮬레이션)
8. **최종 피드백**: 사용자에게 최종 결과 보고
1. **로그 수집**: 로컬 파일 또는 외부 소스에서 로그 수집
2. **에러 분류**: 키워드 기반 에러 카테고리 분류
3. **근본 원인 분석**: 에러 카테고리 기반 원인 분석
4. **사용자 피드백**: 분석 결과를 사용자에게 표시 (Phase 1: 자동 승인)
5. **액션 생성**: Git 변경사항 생성
6. **Git 커밋**: 변경사항 커밋 (Phase 1: 시뮬레이션)
7. **복구 검증**: 복구 결과 확인 (Phase 1: 시뮬레이션)
8. **최종 피드백**: 사용자에게 최종 결과 보고

---

### Cursor한테 질문한 내용을 정리
```
Kubernetes 장애 분석 및 자동 복구 AI Agent 프로젝트를 구성해주세요.

프로젝트 정보:
- 목적: LangGraph를 사용하여 Kubernetes 환경에서 다양한 장애 상황을 감지, 분석, 자동 복구하는 AI Agent 개발
- 기술 스택: 
  - 언어: Python 3.10+
  - 프레임워크: LangGraph
  - LLM: Google Gemini API
  - Kubernetes: Kubernetes Python Client
  - 모니터링: Loki (로그), Prometheus (메트릭), Grafana (대시보드), Alloy (수집기)
  - GitOps: ArgoCD (Git 기반 CD)

아키텍처:
- ArgoCD를 통해 Kubernetes 서비스를 CD하고, 모든 설정은 Git에서 관리
- LangGraph 워크플로우 기반으로 장애 처리 파이프라인 구성

워크플로우:
1. 로그 수집: Loki 또는 Alloy를 통해 로그 수집
2. 에러 분류: 키워드 기반 에러 카테고리 분류
3. 근본 원인 분석: LLM을 활용한 원인 분석
4. 사용자 피드백: 분석 결과 표시 (Phase 1: 자동 승인)
5. 액션 생성: Git 변경사항 생성 (values.yaml 수정 등)
6. Git 커밋: 변경사항 커밋 (Phase 1: 시뮬레이션)
7. 복구 검증: 복구 결과 확인 (Phase 1: 시뮬레이션)
8. 최종 피드백: 사용자에게 최종 결과 보고

프로젝트 구조:
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
│   │   │   ├── __init__.py
│   │   │   ├── collect_logs.py
│   │   │   ├── classify_error.py
│   │   │   ├── analyze_root_cause.py
│   │   │   ├── generate_action.py
│   │   │   └── verify_recovery.py
│   │   └── services/    # 외부 서비스 연동
│   │       ├── __init__.py
│   │       ├── kubernetes_client.py
│   │       ├── loki_client.py
│   │       └── git_client.py
│   ├── cli.py            # CLI 인터페이스
│   └── tools/            # 유틸리티 도구
│       ├── __init__.py
│       └── logger.py
├── tests/                # 테스트 코드
├── README.md
├── requirements.txt
└── .env.example
```

요구사항:
1. 로그 수집 기능:
   - Loki API를 통한 로그 조회 (loki_client.py)
   - Alloy를 통한 로그 수신 (Webhook 또는 API)
   - 로컬 파일에서 로그 읽기

2. Kubernetes 분석 기능:
   - Kubernetes Python Client를 사용한 리소스 조회
   - kubectl 명령어 실행 (subprocess)
   - Pod, Deployment, Service 상태 확인

3. LLM 분석 기능:
   - Google Gemini API를 통한 로그 분석
   - 장애 유형 분류 (OOM, CrashLoop, Config Error 등)
   - 근본 원인 분석 및 복구 가이드 생성

4. GitOps 통합:
   - values.yaml 파일 수정
   - Git 커밋 및 푸시 (ArgoCD 자동 동기화)

환경 변수 (.env.example):
- GOOGLE_API_KEY: Google Gemini API 키
- KUBECONFIG_PATH: Kubernetes 설정 파일 경로 (선택)
- LOKI_URL: Loki 서버 URL
- GIT_REPO_PATH: Git 저장소 경로
- ARGOCD_APP_NAME: ArgoCD Application 이름

코드 스타일:
- 모든 함수와 클래스에 한국어 docstring 추가
- 타입 힌트 사용 (Python 3.10+)
- 에러 처리는 명시적으로 구현
- 로깅은 utils/logger.py의 get_logger 사용

초기 구현:
1. 기본 디렉토리 구조 생성
2. requirements.txt에 필수 패키지 추가
3. .env.example 파일 생성
4. 각 모듈의 기본 구조와 인터페이스 정의
5. README.md에 프로젝트 설명, 설치 방법, 사용법 작성
```