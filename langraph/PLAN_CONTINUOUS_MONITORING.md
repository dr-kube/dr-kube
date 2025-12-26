# LangGraph 지속 실행 및 로그 모니터링 계획

## 1. 현재 상태 분석

### 현재 아키텍처
- ✅ CLI 기반 일회성 실행
- ✅ 로컬 파일 또는 직접 입력으로 로그 수집
- ✅ LangGraph 워크플로우 완성
- ❌ 지속적인 모니터링 불가
- ❌ 자동 트리거 불가
- ❌ 웹 인터페이스 없음

### 필요한 기능
1. **지속 실행**: 백그라운드에서 계속 실행
2. **로그 모니터링**: Loki/Prometheus에서 실시간 로그 수집
3. **이벤트 트리거**: 에러 발생 시 자동으로 워크플로우 시작
4. **상태 관리**: 여러 인시던트 동시 처리 (메모리 기반)
5. **API 서버**: 외부에서 트리거 및 상태 확인 가능
6. **Git 기반 추적**: DB 대신 Git commit 이력으로 인시던트 추적

## 2. 아키텍처 설계

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────┐
│                    LangGraph Service                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │ Log Monitor  │─────▶│  Event Queue │                │
│  │  (Loki API)  │      │   (Redis)    │                │
│  └──────────────┘      └──────────────┘                │
│                              │                          │
│                              ▼                          │
│  ┌──────────────────────────────────────┐              │
│  │     LangGraph Workflow Executor       │              │
│  │  (병렬 처리, 상태 관리)                │              │
│  └──────────────────────────────────────┘              │
│                              │                          │
│                              ▼                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │  Git History │      │  API Server  │                │
│  │   Tracker    │      │  (FastAPI)   │                │
│  └──────────────┘      └──────────────┘                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 2.2 컴포넌트별 역할

#### A. Log Monitor (로그 모니터)
- **기능**: Loki/Prometheus에서 지속적으로 로그 조회
- **주기**: 설정 가능한 간격 (예: 10초마다)
- **필터**: 에러 키워드 기반 필터링
- **출력**: 에러 발견 시 이벤트 큐에 추가

#### B. Event Queue (이벤트 큐)
- **기술**: Redis 또는 in-memory queue
- **역할**: 로그 이벤트 버퍼링 및 순서 보장
- **형식**: `{log_text, timestamp, source, metadata}`

#### C. Workflow Executor (워크플로우 실행기)
- **기능**: LangGraph 워크플로우 실행
- **병렬 처리**: 여러 인시던트 동시 처리
- **상태 관리**: 각 인시던트의 진행 상태 추적

#### D. Git History Tracker (Git 이력 추적기)
- **기술**: GitPython을 사용한 Git 히스토리 조회
- **기능**:
  - 인시던트별 커밋 조회
  - examples/ 폴더의 인시던트 정보 파싱
  - 커밋 메시지에서 인시던트 메타데이터 추출
  - 실시간 상태는 메모리에서 관리

#### E. API Server (API 서버)
- **기술**: FastAPI
- **엔드포인트**:
  - `GET /incidents`: 인시던트 목록 (Git 히스토리에서 조회)
  - `GET /incidents/{id}`: 인시던트 상세 (examples/{id}/ 폴더에서 조회)
  - `POST /incidents/trigger`: 수동 트리거
  - `POST /incidents/{id}/feedback`: 사용자 피드백 (실행 중인 워크플로우에만)
  - `GET /incidents/{id}/status`: 실시간 상태 조회 (메모리)
  - `GET /health`: 헬스 체크

## 3. 구현 단계

### Phase 1: 기본 서버 구조 (1-2주)

#### 1.1 FastAPI 서버 생성
- [ ] `services/api_server.py` 생성
- [ ] 기본 엔드포인트 구현
- [ ] 헬스 체크 및 상태 확인

#### 1.2 로그 모니터 서비스
- [ ] `services/log_monitor.py` 생성
- [ ] Loki API 클라이언트 구현
- [ ] 주기적 로그 조회 (백그라운드 태스크)
- [ ] 에러 필터링 로직

#### 1.3 이벤트 큐
- [ ] `services/event_queue.py` 생성
- [ ] in-memory queue 구현 (초기)
- [ ] 이벤트 형식 정의

#### 1.4 워크플로우 실행기
- [ ] `services/workflow_executor.py` 생성
- [ ] LangGraph 워크플로우 래핑
- [ ] 비동기 실행 지원
- [ ] 상태 추적

### Phase 2: Git 기반 추적 (1주)

#### 2.1 Git History Tracker
- [ ] `services/git_history_tracker.py` 생성
- [ ] 커밋 메시지에서 인시던트 ID 추출
- [ ] examples/ 폴더 스캔하여 인시던트 목록 생성
- [ ] 인시던트별 커밋 히스토리 조회

#### 2.2 인시던트 메타데이터 파싱
- [ ] examples/{incident_id}/summary.md 파싱
- [ ] diff 파일에서 변경 사항 추출
- [ ] 커밋 해시와 인시던트 매핑

### Phase 3: 통합 및 테스트 (1주)

#### 3.1 컴포넌트 통합
- [ ] Log Monitor → Event Queue 연결
- [ ] Event Queue → Workflow Executor 연결
- [ ] Workflow Executor → State Store 연결
- [ ] API Server와 모든 컴포넌트 연결

#### 3.2 사용자 피드백 처리
- [ ] API를 통한 피드백 수신
- [ ] 워크플로우 재개 로직
- [ ] 실시간 상태 업데이트 (메모리)
- [ ] 피드백을 Git 커밋 메시지에 포함

### Phase 4: 프로덕션 준비 (1주)

#### 4.1 Redis 통합 (선택)
- [ ] Redis로 이벤트 큐 교체 (선택사항)
- [ ] 분산 환경 지원 (선택사항)
- [ ] 인메모리 큐로도 충분히 동작 가능

#### 4.2 모니터링 및 로깅
- [ ] Prometheus 메트릭 수집
- [ ] 구조화된 로깅
- [ ] 알림 시스템 (Slack 등)

#### 4.3 Kubernetes 배포
- [ ] Dockerfile 작성
- [ ] Helm Chart 생성
- [ ] ConfigMap/Secret 관리
- [ ] Service/Deployment 정의

## 4. 기술 스택

### 핵심 라이브러리
- **FastAPI**: 웹 프레임워크
- **uvicorn**: ASGI 서버
- **GitPython**: Git 히스토리 조회 (이미 사용 중)
- **aioredis**: Redis 클라이언트 (선택, 인메모리 큐로 대체 가능)
- **httpx**: 비동기 HTTP 클라이언트 (Loki API)
- **asyncio**: 비동기 처리

### 데이터 저장
- **Git**: 인시던트 이력 및 메타데이터 (examples/ 폴더)
- **메모리**: 실행 중인 워크플로우 상태 (dict 또는 Redis 선택)

### 메시징 (선택)
- **인메모리 큐**: 기본 (asyncio.Queue)
- **Redis**: 분산 환경용 (선택)

## 5. 파일 구조

```
langraph/
├── services/
│   ├── api_server.py          # FastAPI 서버
│   ├── log_monitor.py          # 로그 모니터링 서비스
│   ├── event_queue.py          # 이벤트 큐 관리
│   ├── workflow_executor.py    # 워크플로우 실행기
│   ├── git_history_tracker.py  # Git 이력 추적기
│   ├── loki_client.py          # Loki API 클라이언트 (기존 확장)
│   └── prometheus_client.py    # Prometheus API 클라이언트
├── models/
│   ├── state.py                # 기존 State 모델
│   └── database.py             # 데이터베이스 모델
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── incidents.py        # 인시던트 관련 엔드포인트
│   │   └── health.py           # 헬스 체크
│   └── schemas.py              # Pydantic 스키마
├── db/
│   ├── __init__.py
│   ├── database.py             # DB 연결
│   └── migrations/             # 마이그레이션
├── main.py                     # 서버 진입점
└── config/
    └── settings.py             # 설정 (기존 확장)
```

## 6. 설정 예시

### 환경 변수
```bash
# 서버 설정
API_HOST=0.0.0.0
API_PORT=8000

# 로그 모니터링
LOG_MONITOR_INTERVAL=10  # 초
LOKI_URL=http://loki:3100
LOKI_QUERY_INTERVAL=5m   # 5분 전 로그 조회

# Git 설정
GIT_REPO_PATH=.
GIT_BRANCH=main

# Redis (선택, 인메모리 큐 사용 시 불필요)
REDIS_URL=redis://localhost:6379
```

## 7. 실행 방식

### 개발 환경
```bash
# 서버 실행
python -m langraph.main

# 또는 uvicorn 직접 실행
uvicorn langraph.main:app --reload --host 0.0.0.0 --port 8000
```

### 프로덕션 환경
```bash
# Docker
docker build -t langraph-service .
docker run -p 8000:8000 langraph-service

# Kubernetes
kubectl apply -f k8s/
```

## 8. API 사용 예시

### 인시던트 목록 조회 (Git 히스토리에서)
```bash
curl http://localhost:8000/api/incidents
# examples/ 폴더와 Git 커밋 히스토리를 기반으로 조회
```

### 수동 트리거
```bash
curl -X POST http://localhost:8000/api/incidents/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "log_text": "Error: Out of memory",
    "log_source": "manual"
  }'
```

### 사용자 피드백 제공 (실행 중인 워크플로우에만)
```bash
curl -X POST http://localhost:8000/api/incidents/{id}/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "user_recognition": "확인했습니다",
    "user_approved_action": "메모리 증가 승인"
  }'
# 피드백은 Git 커밋 메시지에 포함됨
```

### 인시던트 상세 조회 (Git에서)
```bash
curl http://localhost:8000/api/incidents/{id}
# examples/{id}/summary.md와 diff 파일을 기반으로 조회
```

## 9. 모니터링 및 알림

### 메트릭
- 처리된 인시던트 수 (Git 커밋 수로 계산)
- 워크플로우 실행 시간
- 에러 발생률
- 큐 대기 시간

### 알림
- 인시던트 발생 시 Slack 알림
- 워크플로우 실패 시 알림
- 사용자 피드백 대기 알림

### Git 기반 추적의 장점
- ✅ 버전 관리와 자동 통합
- ✅ 변경 이력 자동 추적
- ✅ 롤백 용이
- ✅ 감사(audit) 로그 자동 생성
- ✅ DB 없이 단순한 구조

## 10. 보안 고려사항

- API 인증 (JWT 또는 API Key)
- Rate Limiting
- 입력 검증
- 민감 정보 마스킹

## 11. 확장 가능성

- 다중 클러스터 지원
- 웹 대시보드 (Grafana 연동)
- 머신러닝 기반 에러 패턴 학습
- 자동 복구 정책 설정

