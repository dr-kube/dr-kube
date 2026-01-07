# AI DrKube Agent 코드 개선 제안

## ✅ 완료된 개선 사항

### 1. `.gitignore` 파일 개선
- Python 표준 패턴 추가 (`.pyc`, `__pycache__/`, `*.egg-info` 등)
- 환경 변수 파일 무시 (`.env`, `*.env`)
- IDE 파일 무시 (`.vscode/`, `.idea/`)
- 생성된 파일 무시 (`reports/`, `patches/`)
- 백업 디렉토리 무시 (`_backup/`)

### 2. `__pycache__` 디렉토리 정리
- 모든 `__pycache__/` 디렉토리 삭제 완료
- `.pyc` 파일들은 Git에 추적되지 않도록 설정

### 3. `requirements.txt` 수정
- 파일 끝부분의 중복된 주석 제거 (27-42줄)
- 깔끔한 패키지 목록으로 정리

### 4. `.env` 파일 보안 처리
- `.env` 파일을 Git 추적에서 제거
- `env.sample` 파일은 유지 (템플릿으로 사용)

---

## 🔧 추가 개선 제안

### 1. 에러 핸들링 강화

#### 문제점
- 여러 함수에서 일반적인 `except Exception as e:` 사용
- 특정 예외 타입을 처리하지 않아 디버깅이 어려움

#### 개선 방안
```python
# 현재
try:
    result = self.llm.invoke(prompt)
except Exception as e:
    logger.error(f"근본 원인 분석 중 오류 발생: {e}")

# 개선
from langchain_core.exceptions import LangChainException

try:
    result = self.llm.invoke(prompt)
except LangChainException as e:
    logger.error(f"LLM 호출 오류: {e}")
    raise
except TimeoutError as e:
    logger.error(f"LLM 응답 시간 초과: {e}")
    raise
except Exception as e:
    logger.error(f"예상치 못한 오류: {e}", exc_info=True)
    raise
```

---

### 2. 타입 힌트 추가

#### 문제점
- 일부 함수에만 타입 힌트가 있음
- 반환 타입이 명확하지 않은 함수들 존재

#### 개선 방안
```python
# log_collector.py
from typing import Dict, List, Optional

def get_pod_metadata(
    self,
    pod_name: str,
    namespace: str = "default"
) -> Optional[Dict[str, Any]]:
    """Pod의 메타데이터 수집"""
    ...
```

---

### 3. 설정 관리 개선

#### 문제점
- 환경 변수와 설정이 여러 곳에 분산
- 기본값이 코드에 하드코딩됨

#### 개선 방안
새 파일: `config/settings.py`
```python
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """애플리케이션 설정"""

    # Google Gemini
    google_api_key: str = Field(..., env="GOOGLE_API_KEY")
    model_name: str = Field("gemini-2.5-flash", env="MODEL_NAME")

    # Kubernetes
    kubeconfig_path: Optional[str] = Field(None, env="KUBECONFIG_PATH")
    kubernetes_namespace: str = Field("default", env="KUBERNETES_NAMESPACE")

    # Agent
    simulate: bool = Field(True, env="SIMULATE")
    auto_approve: bool = Field(True, env="AUTO_APPROVE")
    interactive_mode: bool = Field(True, env="INTERACTIVE_MODE")
    repo_path: str = Field(".", env="REPO_PATH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 사용
settings = Settings()
```

---

### 4. 로깅 표준화

#### 문제점
- `print()` 문과 `logger` 혼용
- 로그 레벨이 일관되지 않음

#### 개선 방안
```python
# 모든 print()를 logger로 변경
# print("\n" + "="*80)
logger.info("="*80)

# 로그 레벨 명확화
logger.debug("디버그 정보")      # 개발 시에만
logger.info("일반 정보")         # 정상 동작
logger.warning("경고")          # 문제 가능성
logger.error("오류")            # 오류 발생
logger.critical("치명적 오류")   # 시스템 중단
```

---

### 5. 테스트 코드 추가

#### 현재 상태
- 테스트 코드가 전혀 없음

#### 개선 방안
```
tests/
├── __init__.py
├── test_log_collector.py
├── test_error_classifier.py
├── test_root_cause_analyzer.py
├── test_git_action.py
└── fixtures/
    ├── sample_logs.txt
    └── mock_k8s_responses.json
```

예시 테스트:
```python
# tests/test_error_classifier.py
import pytest
from tools.error_classifier import ErrorClassifier

def test_classify_oom_error():
    classifier = ErrorClassifier()
    log = "container killed: out of memory (OOM)"

    category = classifier.classify_error(log)

    assert category.name == "리소스 부족"
    assert category.severity == "critical"
```

---

### 6. Docker 지원 추가

#### 제안
새 파일: `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 웹훅 서버 실행
CMD ["python", "-m", "tools.alert_webhook_server"]
```

`docker-compose.yml`:
```yaml
version: '3.8'

services:
  ai-drkube:
    build: .
    ports:
      - "8080:8080"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - KUBECONFIG_PATH=/kubeconfig
    volumes:
      - ~/.kube/config:/kubeconfig:ro
      - ./reports:/app/reports
      - ./patches:/app/patches
    restart: unless-stopped
```

---

### 7. CI/CD 파이프라인 추가

#### 제안
새 파일: `.github/workflows/ci.yml`
```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: pytest --cov=tools tests/

    - name: Lint with flake8
      run: |
        pip install flake8
        flake8 tools/ --count --max-line-length=127
```

---

### 8. 문서화 개선

#### 제안 문서 구조
```
docs/
├── architecture.md       # 시스템 아키텍처
├── api.md               # API 문서
├── deployment.md        # 배포 가이드
├── troubleshooting.md   # 트러블슈팅
└── development.md       # 개발 가이드
```

---

### 9. 보안 강화

#### 개선 사항
1. **API 키 검증**
```python
def validate_api_key(api_key: str) -> bool:
    """API 키 형식 검증"""
    if not api_key or len(api_key) < 20:
        raise ValueError("유효하지 않은 API 키")
    return True
```

2. **Kubernetes RBAC 설정**
```yaml
# k8s/rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ai-drkube
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ai-drkube-role
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ai-drkube-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: ai-drkube-role
subjects:
- kind: ServiceAccount
  name: ai-drkube
```

3. **민감 정보 마스킹**
```python
def mask_sensitive_data(log: str) -> str:
    """로그에서 민감 정보 마스킹"""
    # 토큰, 비밀번호 등 마스킹
    log = re.sub(r'token[=:]\s*[^\s]+', 'token=***', log, flags=re.IGNORECASE)
    log = re.sub(r'password[=:]\s*[^\s]+', 'password=***', log, flags=re.IGNORECASE)
    return log
```

---

### 10. 성능 최적화

#### 개선 방안
1. **로그 수집 최적화**
```python
# 비동기 로그 수집
import asyncio
from kubernetes_asyncio import client, config

async def collect_logs_async(pods: List[str]) -> Dict[str, List[str]]:
    """비동기로 여러 Pod의 로그를 동시에 수집"""
    tasks = [collect_pod_log_async(pod) for pod in pods]
    results = await asyncio.gather(*tasks)
    return dict(zip(pods, results))
```

2. **LLM 응답 캐싱**
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def analyze_category_cached(category: str, logs_hash: str) -> RootCauseAnalysis:
    """동일한 에러 패턴에 대한 분석 결과 캐싱"""
    ...
```

---

## 📊 우선순위

### High Priority (즉시 적용 권장)
- ✅ `.gitignore` 개선
- ✅ `.env` 파일 보안 처리
- ✅ `requirements.txt` 정리
- 🔲 에러 핸들링 강화
- 🔲 설정 관리 개선 (pydantic Settings)

### Medium Priority (단기 적용)
- 🔲 타입 힌트 추가
- 🔲 로깅 표준화
- 🔲 Docker 지원
- 🔲 보안 강화

### Low Priority (장기 개선)
- 🔲 테스트 코드 추가
- 🔲 CI/CD 파이프라인
- 🔲 문서화 개선
- 🔲 성능 최적화

---

## 🎯 다음 단계

1. 이 개선 제안을 팀과 검토
2. 우선순위에 따라 작업 항목 선정
3. GitHub Issues로 변환하여 추적
4. PR 단위로 점진적 개선 적용

---

생성일: 2026-01-07
작성자: Claude AI
