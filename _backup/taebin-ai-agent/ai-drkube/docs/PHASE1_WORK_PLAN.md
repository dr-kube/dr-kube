# Phase 1: HTTP 웹서버 구현 작업 계획

## 목표
- 기본 HTTP 웹서버 구축
- 로그 분석 API 엔드포인트 제공
- 동기 실행 (간단한 요청 처리)
- 헬스 체크 기능

---

## 작업 단계별 상세 계획

### 작업 1: `log_analysis_server.py` 파일 생성

**파일**: `dr-kube/_backup/taebin-ai-agent/ai-drkube/tools/log_analysis_server.py` (신규)

**작업 내용**:
1. Flask 앱 초기화
2. LogAnalysisAgent 통합
3. 기본 라우트 구조 작성
4. CORS 설정

**예상 구조**:
```python
class LogAnalysisServer:
    - __init__()
    - _register_routes()
    - _analyze_logs()  # 분석 요청 처리
    - run()  # 서버 실행
```

**예상 소요 시간**: 30분

---

### 작업 2: 기본 API 엔드포인트 구현

**파일**: `log_analysis_server.py` (작업 1과 동일)

**구현할 엔드포인트**:

#### 2-1. `GET /health`
- **목적**: 서버 상태 확인
- **응답**: `{"status": "healthy", "timestamp": "..."}`

#### 2-2. `POST /api/v1/analyze`
- **목적**: 로그 분석 요청
- **요청 형식**:
```json
{
  "log_source": "my-pod-name",
  "source_type": "pod",
  "namespace": "default",
  "selected_categories": ["네트워크 오류", "리소스 부족"],
  "selected_resource_types": ["pod", "deployment"],
  "additional_context": {}
}
```
- **응답 형식**:
```json
{
  "status": "success",
  "result": {
    "analyses": [...],
    "actions": [...],
    "summary": {...}
  }
}
```

**예상 소요 시간**: 45분

---

### 작업 3: API 요청/응답 스키마 정의

**파일**: `log_analysis_server.py` 내부 또는 별도 `api_schemas.py` (선택)

**작업 내용**:
1. 요청 데이터 검증
2. 필수/선택 필드 정의
3. 에러 응답 포맷 통일

**검증 항목**:
- `log_source`: 필수, 문자열
- `source_type`: 필수, enum (file, pod, label, directory, stdin)
- `namespace`: 선택, 기본값 "default"
- `selected_categories`: 선택, 리스트
- `selected_resource_types`: 선택, 리스트

**예상 소요 시간**: 20분

---

### 작업 4: LogAnalysisAgent 통합

**파일**: `log_analysis_server.py`

**작업 내용**:
1. LogAnalysisAgent 인스턴스 생성
2. 비상호작용 모드로 실행 (`interactive_mode=False`)
3. API 요청 파라미터를 Agent에 전달
4. 결과를 API 응답 형식으로 변환

**주의사항**:
- `interactive_mode=False` 설정
- `auto_approve=True` 설정 (웹서버에서는 자동 승인)
- 상호작용 메서드 호출 방지

**예상 소요 시간**: 30분

---

### 작업 5: 에러 처리 및 로깅

**파일**: `log_analysis_server.py`

**작업 내용**:
1. 전역 에러 핸들러 추가
2. HTTP 상태 코드 매핑
3. 에러 응답 포맷 통일
4. 로깅 설정

**에러 응답 형식**:
```json
{
  "error": "에러 메시지",
  "error_type": "ValidationError",
  "status_code": 400
}
```

**예상 소요 시간**: 25분

---

### 작업 6: `run_server.py` 실행 스크립트 생성

**파일**: `dr-kube/_backup/taebin-ai-agent/ai-drkube/tools/run_server.py` (신규)

**작업 내용**:
1. 명령줄 인자 파싱 (host, port, debug)
2. 서버 인스턴스 생성 및 실행
3. 환경 변수 로드

**사용 예**:
```bash
python -m tools.run_server --host 0.0.0.0 --port 8080
```

**예상 소요 시간**: 15분

---

### 작업 7: `requirements.txt` 확인 및 의존성 추가

**파일**: `dr-kube/_backup/taebin-ai-agent/ai-drkube/requirements.txt`

**작업 내용**:
1. Flask 확인 (이미 있음)
2. flask-cors 추가 (CORS 지원)
3. 필요 시 기타 의존성 추가

**추가할 항목**:
```txt
flask-cors>=4.0.0  # CORS 지원
```

**예상 소요 시간**: 5분

---

### 작업 8: 기본 테스트 및 문서화

**작업 내용**:
1. 서버 실행 테스트
2. API 엔드포인트 테스트 (curl 또는 Postman)
3. README 업데이트 (선택)

**테스트 시나리오**:
1. `GET /health` 호출
2. `POST /api/v1/analyze` 호출 (파일 소스)
3. `POST /api/v1/analyze` 호출 (Pod 소스)
4. 잘못된 요청 처리 확인

**예상 소요 시간**: 30분

---

## 전체 작업 일정

| 작업 | 파일 | 예상 시간 | 우선순위 |
|------|------|----------|----------|
| 1. 서버 클래스 생성 | `log_analysis_server.py` | 30분 | 높음 |
| 2. API 엔드포인트 | `log_analysis_server.py` | 45분 | 높음 |
| 3. 스키마 정의 | `log_analysis_server.py` | 20분 | 중간 |
| 4. Agent 통합 | `log_analysis_server.py` | 30분 | 높음 |
| 5. 에러 처리 | `log_analysis_server.py` | 25분 | 중간 |
| 6. 실행 스크립트 | `run_server.py` | 15분 | 높음 |
| 7. 의존성 추가 | `requirements.txt` | 5분 | 높음 |
| 8. 테스트 | - | 30분 | 중간 |

**총 예상 시간**: 약 3시간

---

## 구현 순서 (권장)

1. ✅ 작업 7: 의존성 추가 (빠른 작업)
2. ✅ 작업 1: 서버 클래스 기본 구조
3. ✅ 작업 2: `/health` 엔드포인트만 먼저 구현
4. ✅ 작업 4: Agent 통합 (기본 연결)
5. ✅ 작업 2: `/api/v1/analyze` 엔드포인트 구현
6. ✅ 작업 3: 요청 검증 추가
7. ✅ 작업 5: 에러 처리 강화
8. ✅ 작업 6: 실행 스크립트
9. ✅ 작업 8: 테스트

---

## 주의사항

1. **기존 코드 보존**
   - `log_analysis_agent.py`는 수정하지 않음
   - `alert_webhook_server.py`는 별도 유지
   - 새 파일만 생성

2. **설정 관리**
   - 환경 변수 사용
   - `.env` 파일 지원 유지

3. **로깅**
   - 기존 loguru 사용
   - API 요청/응답 로깅

4. **에러 처리**
   - 사용자 친화적 메시지
   - 상세 로그는 서버 측에만 기록

---

## API 스펙 (최종)

### `GET /health`
**요청**: 없음

**응답** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0"
}
```

---

### `POST /api/v1/analyze`
**요청 헤더**:
```
Content-Type: application/json
```

**요청 본문**:
```json
{
  "log_source": "my-pod-name",           // 필수
  "source_type": "pod",                   // 필수: file, pod, label, directory, stdin
  "namespace": "default",                 // 선택 (기본값: "default")
  "selected_categories": ["네트워크 오류"], // 선택 (기본값: 모든 카테고리)
  "selected_resource_types": ["pod"],     // 선택 (기본값: ["all"])
  "additional_context": {}                // 선택
}
```

**응답** (200 OK):
```json
{
  "status": "success",
  "result": {
    "analyses": [
      {
        "category": "네트워크 오류",
        "root_cause": "...",
        "explanation": "...",
        "suggested_actions": [...],
        "confidence": 0.95,
        "severity": "high"
      }
    ],
    "actions": [
      {
        "type": "create",
        "file_path": "patches/...",
        "description": "..."
      }
    ],
    "summary": {
      "total_errors": 10,
      "categories_analyzed": 2,
      "actions_generated": 3
    }
  }
}
```

**에러 응답** (400 Bad Request):
```json
{
  "error": "log_source는 필수 필드입니다",
  "error_type": "ValidationError",
  "status_code": 400
}
```

**에러 응답** (500 Internal Server Error):
```json
{
  "error": "로그 분석 중 오류가 발생했습니다",
  "error_type": "InternalError",
  "status_code": 500
}
```

---

## 진행 상황

- [x] 작업 1: 서버 클래스 생성 (`dr_kube.py`)
- [x] 작업 2: API 엔드포인트 구현
- [x] 작업 3: 스키마 정의
- [x] 작업 4: Agent 통합
- [x] 작업 5: 에러 처리
- [x] 작업 6: 실행 스크립트 (통합됨)
- [x] 작업 7: 의존성 추가
- [x] 작업 8: 테스트

---

## 실행 방법

### 기본 실행
```bash
# 방법 1: 직접 실행
python tools/dr_kube.py

# 방법 2: 모듈로 실행
python -m tools.dr_kube

# 방법 3: 커스텀 포트/호스트
python tools/dr_kube.py --host 0.0.0.0 --port 8080

# 방법 4: 디버그 모드
python tools/dr_kube.py --debug
```

### 환경 변수 설정
`.env` 파일에 다음 변수를 설정하세요:
```bash
GOOGLE_API_KEY=your-gemini-api-key-here
KUBECONFIG_PATH=/path/to/kubeconfig  # 선택사항
REPO_PATH=.  # Git 저장소 경로 (기본값: 현재 디렉토리)
SIMULATE=true  # 시뮬레이션 모드 (기본값: true)
AUTO_APPROVE=true  # 자동 승인 모드 (기본값: true)
```

### API 테스트

#### 헬스 체크
```bash
curl http://localhost:8080/health
```

#### 로그 분석 요청 (파일)
```bash
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "log_source": "sample_error.log",
    "source_type": "file"
  }'
```

#### 로그 분석 요청 (Pod)
```bash
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "log_source": "my-pod-name",
    "source_type": "pod",
    "namespace": "default"
  }'
```

---

## 참고 자료

- 기존 코드: `alert_webhook_server.py` (Flask 서버 구조 참고)
- Agent 클래스: `log_analysis_agent.py`
- 로그 수집: `log_collector.py`

