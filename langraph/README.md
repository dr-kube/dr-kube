# DevOps 장애 대응 자동화 LangGraph 시스템

로그를 입력받아 에러를 분류하고, 분류된 에러에 따라 GitOps 저장소에 변경사항을 커밋하여 App of Apps 패턴의 장애를 자동으로 복구하는 LangGraph 기반 시스템입니다.

## 프로젝트 구조

```
langraph/
├── PLAN.md                    # 상세 계획 문서
├── README.md                  # 이 파일
├── requirements.txt           # Python 의존성
├── .env.example               # 환경 변수 예시
├── config/                    # 설정 관리
├── agents/                    # LangGraph 노드 및 그래프
│   ├── graph.py              # 메인 그래프
│   └── nodes/                # 워크플로우 노드들
├── models/                    # 데이터 모델
│   └── state.py              # State 정의
├── services/                  # 외부 서비스 클라이언트 (Phase 2+)
├── utils/                     # 유틸리티
└── cli/                       # CLI 인터페이스
    └── main.py
```

## 설치

### 1. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 값 설정
```

## 사용법

### 기본 사용 (로컬 파일)

```bash
# langraph 디렉토리에서 실행
cd dr-kube/langraph
python -m cli.main --log-file examples/sample_log_oom.txt
```

### 직접 로그 텍스트 입력

```bash
python -m cli.main --log-text "Error: Out of memory - pod/grafana was killed"
```

### 로그 소스 지정

```bash
python -m cli.main --log-file log.txt --log-source loki
```

### 예시 실행

```bash
# OOM 에러 예시
python -m cli.main --log-file examples/sample_log_oom.txt

# CrashLoop 에러 예시
python -m cli.main --log-file examples/sample_log_crashloop.txt
```

## 워크플로우

1. **로그 수집**: 로컬 파일 또는 외부 소스에서 로그 수집
2. **에러 분류**: 키워드 기반 에러 카테고리 분류
3. **근본 원인 분석**: 에러 카테고리 기반 원인 분석
4. **사용자 피드백**: 분석 결과를 사용자에게 표시 (Phase 1: 자동 승인)
5. **액션 생성**: Git 변경사항 생성
6. **Git 커밋**: 변경사항 커밋 (Phase 1: 시뮬레이션)
7. **복구 검증**: 복구 결과 확인 (Phase 1: 시뮬레이션)
8. **최종 피드백**: 사용자에게 최종 결과 보고

## Phase 1 구현 상태

- ✅ 기본 프로젝트 구조
- ✅ State 모델 정의
- ✅ 로그 수집 노드 (로컬 파일)
- ✅ 에러 분류 노드 (키워드 기반)
- ✅ 근본 원인 분석 노드 (기본 템플릿)
- ✅ 사용자 피드백 노드 (자동 승인)
- ✅ 액션 생성 노드 (기본 구조)
- ✅ Git 커밋 노드 (시뮬레이션)
- ✅ 복구 검증 노드 (시뮬레이션)
- ✅ 최종 피드백 노드
- ✅ 기본 LangGraph 구조

## 다음 단계 (Phase 2+)

- LLM 기반 고급 에러 분류 및 분석
- 실제 사용자 입력 받기
- Git 작업 실제 구현
- Kubernetes/ArgoCD API 연동
- Loki/Prometheus 연동

## 참고

자세한 계획은 [PLAN.md](./PLAN.md)를 참고하세요.

