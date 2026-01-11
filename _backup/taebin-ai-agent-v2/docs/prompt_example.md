# Cursor AI 프롬프트 작성법 가이드

Cursor AI와 함께 효율적으로 개발하기 위한 프롬프트 작성법 가이드입니다.

## 📋 목차

1. [기본 원칙](#기본-원칙)
2. [프롬프트 작성 패턴](#프롬프트-작성-패턴)
3. [신규 프로젝트 구성 패턴](#신규-프로젝트-구성-패턴)
4. [실전 예제](#실전-예제)
5. [피해야 할 실수](#피해야-할-실수)
6. [고급 기법](#고급-기법)

---

## 기본 원칙

### 1. 명확성 (Clarity)
**나쁜 예:**
```
버그 고쳐줘
```

**좋은 예:**
```
agent/src/dr_kube/graph.py의 analyze 함수에서 LLM 응답 파싱 시 '근본 원인' 섹션을 찾지 못하면 빈 문자열이 반환되는 문제를 수정해주세요. 
에러 메시지가 없을 때도 적절한 기본값을 제공하도록 개선해주세요.
```

### 2. 컨텍스트 제공 (Context)
**나쁜 예:**
```
함수 추가해줘
```

**좋은 예:**
```
agent/src/dr_kube/graph.py에 새로운 노드 함수를 추가해주세요:
- 함수명: `validate_recovery`
- 입력: IssueState
- 기능: 복구 액션 실행 후 Kubernetes 리소스 상태를 확인하고 검증 결과를 반환
- 기존 analyze 노드 다음에 실행되도록 그래프에 연결
```

### 3. 구체성 (Specificity)
**나쁜 예:**
```
로깅 추가해줘
```

**좋은 예:**
```
agent/src/dr_kube/graph.py의 모든 노드 함수에 로깅을 추가해주세요:
- 각 노드 시작 시: 함수명과 입력 상태 요약 로그
- 에러 발생 시: 에러 메시지와 스택 트레이스 로그
- 노드 완료 시: 처리 결과 요약 로그
- 로거는 utils/logger.py의 get_logger 함수를 사용
- 로그 레벨은 INFO, 에러는 ERROR 레벨로
```

### 4. 단계별 요청 (Step-by-step)
**나쁜 예:**
```
에러 처리 개선해줘
```

**좋은 예:**
```
다음 순서로 에러 처리를 개선해주세요:
1. agent/src/dr_kube/graph.py의 load_issue 함수에 try-except 추가
2. 에러 발생 시 IssueState에 error 필드 설정
3. analyze 함수에서 error 필드 확인하여 에러 상태면 건너뛰기
4. 모든 노드에서 일관된 에러 처리 패턴 적용
```

---

## 프롬프트 작성 패턴

### 패턴 1: 파일 수정 요청
```
[파일 경로]의 [함수/클래스명]에서 [구체적인 변경사항]을 [방법]으로 수정해주세요.

예시:
agent/src/dr_kube/graph.py의 analyze 함수에서 LLM 응답 파싱 로직을 개선해주세요.
정규표현식 대신 구조화된 JSON 응답을 파싱하도록 변경하고, 파싱 실패 시 기본값을 반환하도록 해주세요.
```

### 패턴 2: 새 기능 추가 요청
```
[위치]에 [기능 설명]을 하는 [함수/클래스]를 추가해주세요.
- [요구사항 1]
- [요구사항 2]
- [요구사항 3]

예시:
agent/src/dr_kube/ 디렉토리에 새로운 모듈 recovery.py를 추가해주세요.
Kubernetes 리소스를 복구하는 RecoveryService 클래스를 구현하고:
- 메모리 리소스 제한을 증가시키는 increase_memory_limit 메서드
- 이미지 태그를 수정하는 update_image_tag 메서드
- values.yaml 파일을 수정하는 update_values_yaml 메서드
각 메서드는 에러 처리를 포함하고 한국어 주석을 달아주세요.
```

### 패턴 3: 리팩토링 요청
```
[파일/모듈]의 [문제점]을 해결하기 위해 리팩토링해주세요.
- [개선사항 1]
- [개선사항 2]

예시:
agent/src/dr_kube/graph.py의 analyze 함수를 리팩토링해주세요.
현재 파싱 로직이 복잡하고 유지보수가 어려우므로:
- LLM 응답 파싱을 별도 함수로 분리 (parse_llm_response)
- 파싱 결과를 담는 데이터 클래스 생성 (AnalysisResult)
- 에러 처리를 명시적으로 추가
기존 동작은 유지하면서 코드 가독성을 개선해주세요.
```

### 패턴 4: 테스트 요청
```
[대상]에 대한 테스트를 작성해주세요.
- [테스트 케이스 1]
- [테스트 케이스 2]

예시:
agent/src/dr_kube/graph.py의 analyze 함수에 대한 단위 테스트를 작성해주세요.
tests/ 디렉토리에 test_graph.py 파일을 생성하고:
- 정상적인 LLM 응답 파싱 테스트
- 파싱 실패 시 기본값 반환 테스트
- 에러 발생 시 에러 상태 반환 테스트
pytest를 사용하여 작성해주세요.
```

### 패턴 5: 문서화 요청
```
[대상]에 대한 문서를 작성/업데이트해주세요.
- [포함할 내용 1]
- [포함할 내용 2]

예시:
agent/src/dr_kube/graph.py의 각 노드 함수에 docstring을 추가해주세요.
Google 스타일 docstring 형식을 사용하고:
- 함수의 목적과 동작 설명
- 매개변수 설명 (IssueState의 각 필드)
- 반환값 설명
- 예외 상황 설명
모든 설명은 한국어로 작성해주세요.
```

---

## 신규 프로젝트 구성 패턴

프로젝트 주제만 있고 코드가 없는 상태에서 처음부터 구성을 시작할 때 사용하는 패턴입니다.

### 패턴 1: 프로젝트 구조 설계 요청
```
[프로젝트 주제/목적]을 위한 프로젝트 구조를 설계하고 초기 설정을 해주세요.

프로젝트 정보:
- 목적: [프로젝트의 목적과 기능]
- 기술 스택: [언어, 프레임워크, 라이브러리 등]
- 아키텍처: [MVC, 레이어드 아키텍처 등]

요구사항:
- [요구사항 1]
- [요구사항 2]

예시:
Kubernetes 장애를 자동으로 분석하고 복구하는 AI Agent 프로젝트를 구성해주세요.

프로젝트 정보:
- 목적: Kubernetes 클러스터의 장애를 감지하고, LLM을 활용하여 원인을 분석하며, 자동으로 복구 액션을 수행
- 기술 스택: Python 3.10+, LangGraph, Google Gemini API, Kubernetes Python Client
- 아키텍처: LangGraph 기반 워크플로우, 레이어드 아키텍처 (agents, services, utils)

요구사항:
- 프로젝트 루트에 README.md, requirements.txt, .env.example 파일 생성
- src/ 디렉토리 구조: agents/, services/, utils/, models/
- 각 모듈에 __init__.py 파일 포함
- 한국어 주석과 docstring 사용
- 타입 힌트 사용
```

### 패턴 2: 단계별 프로젝트 구성
```
[프로젝트 주제] 프로젝트를 다음 단계로 구성해주세요:

1단계: 프로젝트 구조 및 기본 설정
   - 디렉토리 구조 생성
   - requirements.txt 작성
   - .env.example 작성
   - README.md 작성

2단계: 핵심 모듈 구현
   - [모듈 1] 구현
   - [모듈 2] 구현

3단계: 통합 및 테스트
   - 메인 진입점 구현
   - 기본 테스트 코드 작성

예시:
Kubernetes 장애 분석 AI Agent 프로젝트를 단계별로 구성해주세요.

1단계: 프로젝트 구조 및 기본 설정
   - agent/ 디렉토리 생성
   - agent/src/ 디렉토리 구조: dr_kube/, cli/, tools/
   - requirements.txt에 LangGraph, google-generativeai, kubernetes 등 추가
   - .env.example에 GOOGLE_API_KEY, KUBECONFIG_PATH 등 환경 변수 정의
   - README.md에 프로젝트 설명, 설치 방법, 사용법 작성

2단계: 핵심 모듈 구현
   - agent/src/dr_kube/state.py: IssueState TypedDict 정의
   - agent/src/dr_kube/llm.py: LLM 클라이언트 래퍼 클래스
   - agent/src/dr_kube/graph.py: LangGraph 워크플로우 정의
   - agent/src/dr_kube/prompts.py: LLM 프롬프트 템플릿

3단계: 통합 및 테스트
   - agent/src/cli.py: CLI 인터페이스 구현
   - agent/tests/ 디렉토리 생성 및 기본 테스트 구조
```

### 패턴 3: 아키텍처 중심 구성
```
[프로젝트 주제] 프로젝트를 [아키텍처 패턴]으로 구성해주세요.

아키텍처 요구사항:
- [레이어/컴포넌트 1]: [역할과 책임]
- [레이어/컴포넌트 2]: [역할과 책임]

기술 스택:
- 언어: [언어 및 버전]
- 프레임워크: [프레임워크]
- 주요 라이브러리: [라이브러리 목록]

예시:
Kubernetes 장애 복구 시스템을 LangGraph 기반 워크플로우 아키텍처로 구성해주세요.

아키텍처 요구사항:
- Graph Layer (agent/src/dr_kube/graph.py): LangGraph 워크플로우 정의, 노드와 엣지 관리
- Node Layer (agent/src/dr_kube/nodes/): 각 워크플로우 노드 구현 (로그 수집, 분석, 복구 등)
- Service Layer (agent/src/dr_kube/services/): Kubernetes API 호출, Git 작업 등 외부 서비스 연동
- Model Layer (agent/src/dr_kube/models/): 데이터 모델 및 상태 정의
- Utils Layer (agent/src/dr_kube/utils/): 로깅, 유틸리티 함수

기술 스택:
- 언어: Python 3.10+
- 프레임워크: LangGraph
- 주요 라이브러리: google-generativeai, kubernetes, pyyaml, gitpython

각 레이어의 기본 구조와 인터페이스를 정의하고, 예제 구현을 포함해주세요.
```

### 패턴 4: 기능 중심 구성
```
[프로젝트 주제] 프로젝트를 구성해주세요.

핵심 기능:
1. [기능 1]: [상세 설명]
2. [기능 2]: [상세 설명]
3. [기능 3]: [상세 설명]

각 기능별로 필요한 모듈과 파일을 생성하고, 기본 구조를 구현해주세요.

예시:
Kubernetes 장애 분석 및 복구 시스템을 구성해주세요.

핵심 기능:
1. 로그 수집: Kubernetes 클러스터에서 Pod 로그를 수집하고 파싱
2. 장애 분석: LLM을 활용하여 로그를 분석하고 근본 원인 도출
3. 자동 복구: 분석 결과를 바탕으로 values.yaml을 수정하고 Git에 커밋

각 기능별 구현:
- 로그 수집: agent/tools/log_collector.py (kubectl 명령어 실행, 로그 파싱)
- 장애 분석: agent/src/dr_kube/graph.py (LangGraph 워크플로우, LLM 호출)
- 자동 복구: agent/tools/git_action.py (YAML 수정, Git 커밋)

각 모듈의 기본 인터페이스와 예제 구현을 포함해주세요.
```

### 패턴 5: 설정 파일 중심 구성
```
[프로젝트 주제] 프로젝트를 구성해주세요.

필요한 설정 파일:
- [설정 파일 1]: [용도]
- [설정 파일 2]: [용도]

각 설정 파일의 기본 구조와 예제 값을 포함해주세요.

예시:
Kubernetes 장애 분석 AI Agent 프로젝트를 구성해주세요.

필요한 설정 파일:
- pyproject.toml: Python 프로젝트 메타데이터 및 빌드 설정
- requirements.txt: Python 패키지 의존성
- .env.example: 환경 변수 템플릿
- .gitignore: Git 무시 파일 목록
- README.md: 프로젝트 문서

각 파일의 기본 구조를 작성하고, 프로젝트 루트에 src/ 디렉토리 구조도 함께 생성해주세요.
```

### 실전 예제: 신규 프로젝트 구성

#### 예제 1: 완전히 새로운 프로젝트
```
Kubernetes 클러스터 모니터링 대시보드 프로젝트를 처음부터 구성해주세요.

프로젝트 목적:
- Kubernetes 클러스터의 리소스 사용량을 실시간으로 모니터링
- Prometheus 메트릭을 수집하여 Grafana 대시보드로 시각화
- 알림 기능 포함

기술 스택:
- Backend: Python 3.11, FastAPI
- Frontend: React, TypeScript
- 모니터링: Prometheus, Grafana
- 데이터베이스: PostgreSQL

프로젝트 구조:
```
monitoring-dashboard/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   ├── services/
│   │   ├── models/
│   │   └── utils/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── README.md
└── .gitignore
```

요구사항:
1. 프로젝트 루트 디렉토리 구조 생성
2. backend/src/api/에 FastAPI 기본 구조 (main.py, routers/)
3. frontend/src/에 React 기본 구조 (App.tsx, components/)
4. docker-compose.yml에 PostgreSQL, Prometheus, Grafana 서비스 정의
5. 각 서비스의 기본 설정 파일 생성
6. README.md에 프로젝트 설명과 실행 방법 작성
```

#### 예제 2: 마이크로서비스 프로젝트
```
이커머스 주문 처리 마이크로서비스 시스템을 구성해주세요.

서비스 구성:
1. API Gateway: 모든 요청의 진입점
2. Order Service: 주문 생성 및 관리
3. Payment Service: 결제 처리
4. Inventory Service: 재고 관리
5. Notification Service: 알림 발송

기술 스택:
- 언어: Python 3.10+
- 프레임워크: FastAPI
- 메시지 큐: RabbitMQ
- 데이터베이스: PostgreSQL, Redis
- 컨테이너: Docker, Kubernetes

구성 요청:
1. 각 서비스별 디렉토리 구조 생성
2. 공통 라이브러리 모듈 (shared/) 생성
3. docker-compose.yml에 모든 서비스 정의
4. Kubernetes 매니페스트 파일 (k8s/) 생성
5. 각 서비스의 기본 FastAPI 구조와 헬스체크 엔드포인트
6. README.md에 전체 아키텍처 설명
```

#### 예제 3: AI/ML 프로젝트
```
이미지 분류 AI 모델 학습 및 서빙 프로젝트를 구성해주세요.

프로젝트 목적:
- 이미지 데이터셋으로 CNN 모델 학습
- 학습된 모델을 REST API로 서빙
- 모델 성능 모니터링

기술 스택:
- 언어: Python 3.10+
- ML 프레임워크: PyTorch
- API: FastAPI
- 모델 저장: MLflow
- 컨테이너: Docker

구성 요청:
1. 프로젝트 디렉토리 구조:
   ```
   image-classifier/
   ├── data/          # 데이터셋
   ├── models/        # 학습된 모델
   ├── src/
   │   ├── training/  # 학습 스크립트
   │   ├── inference/ # 추론 코드
   │   └── api/       # API 서버
   ├── notebooks/     # Jupyter 노트북
   ├── requirements.txt
   └── README.md
   ```

2. src/training/train.py: 기본 학습 스크립트 구조
3. src/inference/predictor.py: 모델 로딩 및 예측 클래스
4. src/api/main.py: FastAPI 서버 기본 구조
5. requirements.txt에 PyTorch, FastAPI, MLflow 등 추가
6. README.md에 데이터 준비, 학습, 서빙 방법 설명
```

### 신규 프로젝트 구성 시 체크리스트

프로젝트를 처음부터 구성할 때 다음을 확인하세요:

- [ ] 프로젝트 목적과 범위가 명확한가?
- [ ] 기술 스택이 구체적으로 명시되었는가?
- [ ] 아키텍처 패턴이나 구조가 정의되었는가?
- [ ] 디렉토리 구조가 계획되었는가?
- [ ] 필요한 설정 파일들이 요청되었는가?
- [ ] 의존성 관리 방법이 명시되었는가? (requirements.txt, package.json 등)
- [ ] 환경 변수 관리 방법이 정의되었는가? (.env.example)
- [ ] 문서화 요구사항이 포함되었는가? (README.md)
- [ ] 컨테이너화 요구사항이 있는가? (Dockerfile, docker-compose.yml)
- [ ] 테스트 구조가 계획되었는가? (tests/ 디렉토리)

---

## 실전 예제

### 예제 1: 기능 추가
```
agent/src/dr_kube/graph.py에 새로운 노드 함수 collect_metrics를 추가해주세요.

기능:
- Kubernetes 클러스터에서 Pod의 CPU/메모리 메트릭을 수집
- Prometheus API를 통해 메트릭 조회
- 수집한 메트릭을 IssueState의 metrics 필드에 저장

요구사항:
- kubectl을 사용하여 Prometheus 서비스에 접근
- 에러 발생 시 IssueState에 error 필드 설정
- 한국어 주석 추가
- 기존 create_graph 함수에 노드 추가 및 엣지 연결 (analyze 노드 다음에 실행)
```

### 예제 2: 버그 수정
```
agent/src/dr_kube/graph.py의 analyze 함수에서 발생하는 문제를 수정해주세요.

문제:
- LLM 응답에서 "근본 원인" 섹션을 찾을 때 대소문자 구분으로 인해 파싱 실패
- 여러 줄에 걸친 근본 원인 설명을 제대로 추출하지 못함

해결 방법:
- 대소문자 구분 없이 검색하도록 개선
- 여러 줄에 걸친 내용도 추출할 수 있도록 정규표현식 수정
- 파싱 실패 시 LLM 응답 전체를 root_cause로 사용하는 fallback 로직 추가
```

### 예제 3: 코드 개선
```
agent/src/dr_kube/graph.py의 코드 품질을 개선해주세요.

개선 사항:
1. 하드코딩된 문자열 ("근본 원인", "심각도" 등)을 상수로 추출
2. 파싱 로직을 별도 함수로 분리하여 가독성 향상
3. 타입 힌트 추가 (IssueState는 TypedDict이므로 적절히 활용)
4. 에러 메시지를 더 구체적으로 개선

기존 동작은 유지하면서 리팩토링해주세요.
```

### 예제 4: 통합 요청
```
다음 기능을 구현해주세요:

1. agent/src/dr_kube/recovery.py 모듈 생성
   - Kubernetes 리소스를 복구하는 RecoveryService 클래스
   - increase_memory_limit(namespace, deployment, new_limit) 메서드
   - update_image_tag(namespace, deployment, new_tag) 메서드

2. agent/src/dr_kube/graph.py 수정
   - suggest 노드를 recovery 노드로 변경
   - recovery 노드에서 RecoveryService를 사용하여 자동 복구 수행
   - 복구 결과를 IssueState에 저장

3. agent/src/cli.py 수정
   - --auto-recovery 플래그 추가 (기본값: False)
   - 플래그가 True일 때만 recovery 노드 실행

모든 코드는 한국어 주석을 포함하고, 에러 처리를 명시적으로 구현해주세요.
```

### 예제 5: 실제 사용된 신규 프로젝트 구성 프롬프트

#### 원본 프롬프트 (개선 전)
```
[프로젝트 주제/목적]을 위한 프로젝트 구조를 설계하고 초기 설정을 해주세요.

프로젝트 정보:
- 목적: LangGraph를 사용하여 Kubernetes 환경에서 다양한 장애 상황을 인지 및 분석하여 장애 분석 및 장애 조치를 수행하는 Ai agent 개발
- 기술 스택: Python 3.10+, LangGraph, Google Gemini API, Kubernetes Python Client, ArgoCD, Loki, Alloy, Prometheus, Grafana
- 아키텍처:
  - ArgoCD를 통해서 Kubernetes 서비스를 CD하고 있고, 관련 Source는 Git에서 관리되고 있습니다.

요구사항:
-  LLM은 아래 상황에 대해 로그를 분석하고 장애 조치를 위한 가이드를 제시합니다.
    - Loki를 통해 수집된 로그를 장애분석에 활용하거나 혹은 Alloy를 통해서 전달받은 로그를 분석가능합니다.
    - Kubernetes Python client등과 같은 script를 사용하여 Agent가 직접 Kubernets의 명령어를 사용해서 장애를 분석합니다.
    - 직접 사용자의 질문을 입력 받아 장애를 분석합니다.
- 프로젝트 루트에 README.md, requirements.txt, .env.example 파일 생성
- src/ 디렉토리 구조: agents/, services/, utils/, models/
- 각 모듈에 __init__.py 파일 포함
- 한국어 주석과 docstring 사용
- 타입 힌트 사용
```

**분석:**
- ✅ 프로젝트 목적과 기술 스택이 명확함
- ✅ 기본 요구사항이 포함됨
- ⚠️ 디렉토리 구조가 구체적이지 않음
- ⚠️ 워크플로우 단계가 명시되지 않음
- ⚠️ 환경 변수 목록이 구체적이지 않음
- ⚠️ 각 모듈의 역할이 불명확함

#### 개선된 프롬프트
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

**개선 사항:**
- ✅ 워크플로우 단계를 명확히 정의
- ✅ 디렉토리 구조를 구체적으로 명시
- ✅ 각 모듈의 역할과 책임을 명확히 함
- ✅ 환경 변수 목록을 구체적으로 제시
- ✅ 코드 스타일 가이드라인 추가
- ✅ 초기 구현 단계를 명시

---

## 피해야 할 실수

### ❌ 나쁜 예제들

1. **너무 모호한 요청**
   ```
   코드 개선해줘
   ```
   → 무엇을 어떻게 개선할지 명시하지 않음

2. **컨텍스트 부족**
   ```
   함수 추가해줘
   ```
   → 어디에, 어떤 함수를, 왜 추가할지 불명확

3. **한 번에 너무 많은 요청**
   ```
   전체 시스템을 리팩토링하고, 테스트를 작성하고, 문서를 업데이트하고, 
   새로운 기능 5개를 추가해줘
   ```
   → 작업이 너무 복잡하여 정확도 저하

4. **기술 스택 명시 누락**
   ```
   API 클라이언트 만들어줘
   ```
   → 어떤 라이브러리를 사용할지, 어떤 스타일로 작성할지 불명확

### ✅ 좋은 예제들

1. **명확하고 구체적인 요청**
   ```
   agent/src/dr_kube/graph.py의 analyze 함수에서 LLM 응답 파싱 로직을 개선해주세요.
   현재는 문자열 분할로 파싱하는데, JSON 형식 응답을 파싱하도록 변경해주세요.
   ```

2. **충분한 컨텍스트 제공**
   ```
   agent/src/dr_kube/graph.py를 참고하여, 
   새로운 모듈 agent/src/dr_kube/recovery.py를 생성하고 
   Kubernetes 리소스 복구 기능을 구현해주세요.
   ```

3. **단계별 요청**
   ```
   1단계: agent/src/dr_kube/recovery.py 모듈 생성
   2단계: RecoveryService 클래스 구현
   3단계: graph.py에 recovery 노드 추가
   ```

4. **기술 스택 명시**
   ```
   agent/src/dr_kube/recovery.py에 Kubernetes API를 사용하는 RecoveryService 클래스를 추가해주세요.
   kubernetes Python 클라이언트 라이브러리를 사용하고, 
   기존 코드 스타일(타입 힌트, 한국어 주석)을 따르세요.
   ```

---

## 고급 기법

### 1. 파일 참조 활용
```
@agent/src/dr_kube/graph.py의 analyze 함수를 참고하여,
비슷한 패턴으로 validate_recovery 함수를 작성해주세요.
```

### 2. 코드 스니펫 제공
```
다음과 같은 형식으로 함수를 작성해주세요:

```python
def example_function(state: IssueState) -> IssueState:
    """함수 설명"""
    # 구현 내용
    return state
```

agent/src/dr_kube/graph.py에 이 패턴을 따르는 새 함수를 추가해주세요.
```

### 3. 제약 조건 명시
```
agent/src/dr_kube/graph.py에 새 노드를 추가해주세요.
단, 다음 조건을 만족해야 합니다:
- 기존 노드들의 패턴을 따름
- IssueState 타입을 사용
- 에러 발생 시 error 필드 설정
- 한국어 주석 포함
- 함수 길이는 50줄 이하
```

### 4. 예외 상황 처리 요청
```
agent/src/dr_kube/graph.py의 analyze 함수를 개선해주세요.
다음 예외 상황을 처리하도록 해주세요:
- LLM API 호출 실패 시
- 응답 형식이 예상과 다를 때
- 네트워크 타임아웃 발생 시
각 경우에 적절한 에러 메시지와 함께 IssueState에 error 필드를 설정해주세요.
```

### 5. 테스트 주도 요청
```
agent/src/dr_kube/graph.py에 validate_recovery 함수를 추가해주세요.

먼저 다음 테스트 케이스를 만족하도록 구현해주세요:
1. 정상적인 복구 검증 시 True 반환
2. 복구 실패 시 False와 에러 메시지 반환
3. Kubernetes API 접근 실패 시 에러 처리

tests/test_graph.py에 테스트 코드도 함께 작성해주세요.
```

### 6. 점진적 개선 요청
```
agent/src/dr_kube/graph.py의 analyze 함수를 단계적으로 개선해주세요:

1단계: 현재 파싱 로직에 로깅 추가
2단계: 파싱 로직을 별도 함수로 분리
3단계: 구조화된 응답 파싱으로 변경
4단계: 에러 처리 강화

각 단계를 완료한 후 다음 단계로 진행해주세요.
```

---

## 체크리스트

### 기존 프로젝트 작업 시
프롬프트를 작성할 때 다음을 확인하세요:

- [ ] 요청이 명확하고 구체적인가?
- [ ] 필요한 컨텍스트(파일 경로, 함수명 등)를 제공했는가?
- [ ] 기술 스택이나 라이브러리를 명시했는가?
- [ ] 예외 상황이나 에러 처리를 요청했는가?
- [ ] 코드 스타일이나 주석 요구사항을 명시했는가?
- [ ] 테스트나 문서화를 요청했는가?
- [ ] 작업을 단계별로 나눌 수 있는가?

### 신규 프로젝트 구성 시
프로젝트를 처음부터 구성할 때 다음을 확인하세요:

- [ ] 프로젝트 목적과 범위가 명확한가?
- [ ] 기술 스택이 구체적으로 명시되었는가?
- [ ] 아키텍처 패턴이나 구조가 정의되었는가?
- [ ] 디렉토리 구조가 계획되었는가?
- [ ] 필요한 설정 파일들이 요청되었는가?
- [ ] 의존성 관리 방법이 명시되었는가? (requirements.txt, package.json 등)
- [ ] 환경 변수 관리 방법이 정의되었는가? (.env.example)
- [ ] 문서화 요구사항이 포함되었는가? (README.md)
- [ ] 컨테이너화 요구사항이 있는가? (Dockerfile, docker-compose.yml)
- [ ] 테스트 구조가 계획되었는가? (tests/ 디렉토리)

---

## 추가 팁

### 1. 대화형 개발
한 번에 모든 것을 요청하지 말고, 대화를 통해 점진적으로 개선하세요:
```
1차 요청: 기본 기능 구현
2차 요청: 에러 처리 추가
3차 요청: 테스트 작성
4차 요청: 문서화
```

### 2. 예제 활용
기존 코드를 예제로 제공하면 더 정확한 결과를 얻을 수 있습니다:
```
agent/src/dr_kube/graph.py의 load_issue 함수를 참고하여,
비슷한 패턴으로 load_config 함수를 작성해주세요.
```

### 3. 피드백 제공
Cursor의 결과에 대해 피드백을 제공하면 다음 요청이 더 정확해집니다:
```
좋습니다! 이제 이 함수에 타입 힌트를 추가해주세요.
또한 에러 처리를 더 구체적으로 개선해주세요.
```

### 4. 파일 구조 이해
프로젝트의 파일 구조를 이해하고 적절한 위치에 요청하세요:
```
agent/src/dr_kube/ 디렉토리 구조를 유지하면서
새로운 모듈을 추가해주세요.
```

### 5. 실제 사용 경험 팁

#### 신규 프로젝트 구성 시 주의사항
실제 프로젝트를 구성할 때 다음을 고려하세요:

1. **점진적 접근**
   - 처음부터 완벽한 구조를 만들려 하지 말고, 기본 구조를 먼저 만들고 점진적으로 개선
   - 예: "먼저 기본 디렉토리 구조와 핵심 모듈만 생성해주세요. 나중에 세부 기능을 추가하겠습니다."

2. **워크플로우 명시**
   - 복잡한 시스템의 경우 워크플로우를 명확히 정의
   - 예: "LangGraph 워크플로우는 다음 8단계로 구성됩니다: 로그 수집 → 에러 분류 → 원인 분석 → ..."

3. **환경 변수 구체화**
   - .env.example에 실제 사용할 환경 변수를 구체적으로 명시
   - 예: "GOOGLE_API_KEY, KUBECONFIG_PATH, LOKI_URL 등을 포함해주세요."

4. **기존 시스템과의 통합 고려**
   - 기존 인프라(ArgoCD, Loki 등)와의 통합 방법을 명시
   - 예: "ArgoCD를 통해 Git 변경사항이 자동으로 배포되므로, Git 커밋만 하면 됩니다."

5. **단계별 검증**
   - 각 단계를 완료한 후 결과를 확인하고 다음 단계로 진행
   - 예: "1단계 완료 후 생성된 파일 구조를 확인하고, 2단계로 진행해주세요."

#### 실제 사용 예시
```
❌ 처음 시도 (너무 모호함):
"Kubernetes 장애 분석 AI Agent 만들어줘"

✅ 개선된 버전 (구체적이고 단계적):
"Kubernetes 장애 분석 AI Agent 프로젝트를 구성해주세요.
1단계: 기본 디렉토리 구조와 설정 파일만 먼저 생성
2단계: 핵심 모듈의 기본 구조 정의
3단계: 각 모듈의 세부 구현

각 단계를 완료한 후 다음 단계로 진행해주세요."
```

---

## 마무리

Cursor AI와 함께 개발할 때는 **명확성, 구체성, 단계별 접근**이 핵심입니다.

### 기존 프로젝트 작업 시
- 복잡한 작업은 작은 단위로 나누고
- 충분한 컨텍스트를 제공하며
- 기존 코드 스타일과 패턴을 따르도록 요청하세요

### 신규 프로젝트 구성 시
- 프로젝트 목적과 기술 스택을 명확히 정의하고
- 아키텍처와 디렉토리 구조를 먼저 설계하며
- 단계별로 점진적으로 구축하세요
- 처음부터 완벽하게 만들려 하지 말고, 기본 구조를 먼저 만들고 점진적으로 개선하세요

좋은 프롬프트는 좋은 코드를 만듭니다! 🚀
