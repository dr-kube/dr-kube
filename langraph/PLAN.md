# DevOps 장애 대응 자동화 LangGraph 시스템 계획

## 1. 개요

로그를 입력받아 에러를 분류하고, 분류된 에러에 따라 GitOps 저장소에 변경사항을 커밋하여 App of Apps 패턴의 장애를 자동으로 복구하는 LangGraph 기반 시스템입니다.

## 2. 시스템 아키텍처

### 2.1 워크플로우 개요

```
로그 입력(파일 읽기) → 에러 분류 → 원인 분석 → 사용자 피드백(인식) → 액션 결정 → Git 커밋 → 결과 확인 → 사용자 피드백(결과)
```

### 2.2 LangGraph State 구조

```python
class IncidentState(TypedDict):
    # 입력
    raw_log: str                    # 원본 로그
    log_source: str                 # 로그 소스 (loki, prometheus, etc.)
    timestamp: str                  # 로그 타임스탬프
    
    # 분류
    error_category: str             # 에러 카테고리 (oom, crashloop, config_error, etc.)
    error_severity: str             # 심각도 (critical, warning, info)
    affected_apps: List[str]        # 영향받는 애플리케이션 목록
    
    # 분석
    root_cause: str                 # 근본 원인 분석
    suggested_actions: List[str]    # 제안된 액션 목록
    
    # 사용자 피드백
    user_recognition: str           # 사용자 인식 (사용자 확인/수정)
    user_approved_action: str       # 사용자 승인된 액션
    
    # 실행
    git_changes: Dict[str, str]     # Git 변경사항 (파일 경로: 변경 내용)
    commit_message: str             # 커밋 메시지
    commit_hash: str                # 커밋 해시
    
    # 결과
    recovery_result: str            # 복구 결과
    verification_status: str        # 검증 상태 (success, failed, pending)
    
    # 메타데이터
    incident_id: str                # 인시던트 ID
    workflow_status: str            # 워크플로우 상태
    user_feedback_history: List[Dict]  # 사용자 피드백 이력
```

## 3. 노드(Node) 설계

### 3.1 로그 수집 노드 (collect_logs)
- **입력**: 로그 소스, 쿼리 파라미터
- **출력**: raw_log, log_source, timestamp
- **기능**: 
  - Loki API에서 로그 조회
  - Prometheus Alertmanager에서 알림 수신
  - 로컬 파일에서 로그 읽기 (로컬 테스트용)

### 3.2 에러 분류 노드 (classify_error)
- **입력**: raw_log
- **출력**: error_category, error_severity, affected_apps
- **기능**:
  - LLM을 사용한 에러 패턴 인식
  - 사전 정의된 에러 카테고리 매칭
  - 영향받는 애플리케이션 식별
- **에러 카테고리 예시**:
  - `oom` (Out of Memory)
  - `crashloop` (CrashLoopBackOff)
  - `config_error` (설정 오류)
  - `resource_exhausted` (리소스 부족)
  - `network_error` (네트워크 오류)
  - `image_pull_error` (이미지 풀 오류)

### 3.3 원인 분석 노드 (analyze_root_cause)
- **입력**: error_category, raw_log, affected_apps
- **출력**: root_cause, suggested_actions
- **기능**:
  - LLM을 사용한 근본 원인 분석
  - 컨텍스트 기반 액션 제안
  - 기존 인시던트 히스토리 참조

### 3.4 사용자 피드백 노드 (get_user_feedback)
- **입력**: root_cause, suggested_actions
- **출력**: user_recognition, user_approved_action
- **기능**:
  - 사용자에게 원인과 제안된 액션 표시
  - 사용자 수정/승인 대기
  - CLI 또는 웹 인터페이스 제공

### 3.5 액션 생성 노드 (generate_action)
- **입력**: user_approved_action, affected_apps, error_category
- **출력**: git_changes, commit_message
- **기능**:
  - 승인된 액션에 따라 GitOps 변경사항 생성
  - Application.yaml 수정 (리소스 증가, 설정 변경 등)
  - values.yaml 수정 (Helm values 조정)
  - 커밋 메시지 생성

### 3.6 Git 커밋 노드 (commit_changes)
- **입력**: git_changes, commit_message
- **출력**: commit_hash
- **기능**:
  - 로컬 Git 저장소에 변경사항 커밋
  - 원격 저장소에 푸시 (선택적)
  - ArgoCD 자동 동기화 대기

### 3.7 결과 검증 노드 (verify_recovery)
- **입력**: commit_hash, affected_apps
- **출력**: recovery_result, verification_status
- **기능**:
  - Kubernetes API로 Pod 상태 확인
  - ArgoCD Application 상태 확인
  - 로그 재조회하여 에러 해결 확인
  - 타임아웃 처리

### 3.8 최종 피드백 노드 (final_feedback)
- **입력**: recovery_result, verification_status
- **출력**: 사용자에게 최종 결과 보고
- **기능**:
  - 복구 성공/실패 보고
  - 추가 조치 필요 시 알림

## 4. 엣지(Edge) 및 라우팅

### 4.1 조건부 라우팅
- **에러 심각도에 따른 분기**:
  - `critical` → 즉시 사용자 피드백 요청
  - `warning` → 자동 처리 후 사용자 확인
  - `info` → 로그만 기록

- **복구 결과에 따른 분기**:
  - `success` → 최종 피드백 → 종료
  - `failed` → 재시도 또는 수동 개입 요청
  - `pending` → 대기 후 재검증

## 5. 파일 구조

```
langraph/
├── PLAN.md                    # 이 계획 문서
├── README.md                  # 프로젝트 설명 및 사용법
├── requirements.txt           # Python 의존성
├── .env.example               # 환경 변수 예시
├── config/
│   ├── __init__.py
│   ├── settings.py            # 설정 관리
│   └── error_categories.py    # 에러 카테고리 정의
├── agents/
│   ├── __init__.py
│   ├── graph.py               # LangGraph 메인 그래프
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── collect_logs.py
│   │   ├── classify_error.py
│   │   ├── analyze_root_cause.py
│   │   ├── get_user_feedback.py
│   │   ├── generate_action.py
│   │   ├── commit_changes.py
│   │   ├── verify_recovery.py
│   │   └── final_feedback.py
│   └── edges/
│       ├── __init__.py
│       └── routing.py         # 조건부 라우팅 로직
├── services/
│   ├── __init__.py
│   ├── loki_client.py         # Loki API 클라이언트
│   ├── kubernetes_client.py   # Kubernetes API 클라이언트
│   ├── argocd_client.py       # ArgoCD API 클라이언트
│   └── git_client.py          # Git 작업 클라이언트
├── models/
│   ├── __init__.py
│   └── state.py               # State 타입 정의
├── utils/
│   ├── __init__.py
│   ├── logger.py              # 로깅 유틸리티
│   └── prompts.py             # LLM 프롬프트 템플릿
├── cli/
│   ├── __init__.py
│   └── main.py                # CLI 진입점
└── tests/
    ├── __init__.py
    └── test_nodes.py          # 노드 테스트
```

## 6. 기술 스택

### 6.1 핵심 라이브러리
- **LangGraph**: 워크플로우 오케스트레이션
- **LangChain**: LLM 통합
- **OpenAI/Anthropic**: LLM API
- **PyYAML**: YAML 파일 처리
- **GitPython**: Git 작업
- **kubernetes**: Kubernetes API 클라이언트
- **requests**: HTTP 클라이언트 (Loki, ArgoCD API)

### 6.2 로컬 실행 환경
- Python 3.10+
- 가상환경 (venv 또는 conda)
- Git 저장소 로컬 클론
- Kubernetes 클러스터 접근 (kubectl config)
- 환경 변수 설정 (.env)

## 7. 구현 단계

### Phase 1: 기본 구조 및 로그 수집
1. 프로젝트 구조 생성
2. State 모델 정의
3. 로그 수집 노드 구현 (로컬 파일 우선)
4. 기본 그래프 구조 생성

### Phase 2: 에러 분류 및 분석
1. 에러 분류 노드 구현
2. 원인 분석 노드 구현
3. LLM 프롬프트 설계 및 최적화

### Phase 3: 사용자 피드백
1. CLI 인터페이스 구현
2. 사용자 피드백 노드 구현
3. 대화형 입력 처리

### Phase 4: Git 작업 및 복구
1. Git 클라이언트 구현
2. 액션 생성 노드 구현 (Application.yaml 수정)
3. Git 커밋 노드 구현

### Phase 5: 검증 및 통합
1. Kubernetes/ArgoCD 클라이언트 구현
2. 결과 검증 노드 구현
3. 전체 워크플로우 통합 테스트

### Phase 6: 외부 시스템 연동
1. Loki API 연동
2. Prometheus Alertmanager 연동
3. ArgoCD API 연동

## 8. 보안 고려사항

- Git 토큰/자격증명 환경 변수 관리
- Kubernetes 클러스터 접근 권한 최소화
- LLM API 키 보안 관리
- 민감한 로그 정보 마스킹

## 9. 확장 가능성

- 웹 대시보드 추가
- Slack/이메일 알림 통합
- 인시던트 히스토리 데이터베이스
- 머신러닝 기반 에러 패턴 학습
- 다중 클러스터 지원

