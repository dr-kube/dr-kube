# 로그 분석 에이전트

Gemini LLM을 사용하여 Kubernetes 환경의 로그를 분석하고, 에러의 근본 원인을 파악하여 자동으로 복구 조치를 생성하는 에이전트입니다.

## 기능

1. **로그 수집**: 로컬 파일 또는 Kubernetes Pod에서 로그 수집
2. **에러 분류**: 키워드 기반 에러 카테고리 분류
3. **근본 원인 분석**: Gemini LLM을 사용한 에러 카테고리 기반 원인 분석
4. **사용자 피드백**: 분석 결과를 사용자에게 표시 (Phase 1: 자동 승인)
5. **액션 생성**: Git 변경사항 생성
6. **Git 커밋**: 변경사항 커밋 (Phase 1: 시뮬레이션)
7. **복구 검증**: 복구 결과 확인 (Phase 1: 시뮬레이션)
8. **최종 피드백**: 사용자에게 최종 결과 보고

## 설치

### 1. 의존성 설치

```bash
cd ai-drkube
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 변수를 설정하세요:

```bash
GOOGLE_API_KEY=your-gemini-api-key-here
KUBECONFIG_PATH=/path/to/kubeconfig  # 선택사항
REPO_PATH=.  # Git 저장소 경로 (기본값: 현재 디렉토리)
SIMULATE=true  # 시뮬레이션 모드 (기본값: true)
AUTO_APPROVE=true  # 자동 승인 모드 (기본값: true)
```

## 사용 방법

### 기본 사용법

```bash
# 로컬 파일에서 로그 분석
python -m tools.log_analysis_agent error.log --type file

# Kubernetes Pod에서 로그 수집 및 분석
python -m tools.log_analysis_agent my-pod-name --type pod

# 라벨 셀렉터로 여러 Pod에서 로그 수집
python -m tools.log_analysis_agent "app=myapp" --type label

# 디렉토리에서 모든 로그 파일 분석
python -m tools.log_analysis_agent /path/to/logs --type directory
```

### 고급 옵션

```bash
# 시뮬레이션 모드 비활성화 (실제 파일 변경 및 커밋 수행)
python -m tools.log_analysis_agent error.log --type file --no-simulate

# 자동 승인 비활성화 (사용자 승인 요청)
python -m tools.log_analysis_agent error.log --type file --no-auto-approve

# 커스텀 Git 저장소 경로 지정
python -m tools.log_analysis_agent error.log --type file --repo-path /path/to/repo

# 커스텀 Kubernetes config 파일 지정
python -m tools.log_analysis_agent my-pod --type pod --kubeconfig /path/to/kubeconfig
```

### Python 코드에서 사용

```python
from tools.log_analysis_agent import LogAnalysisAgent

# 에이전트 생성
agent = LogAnalysisAgent()

# 로그 분석 실행
result = agent.run(
    log_source="error.log",
    source_type="file"
)

# 결과 확인
print(f"상태: {result['status']}")
print(f"분석된 카테고리: {len(result['analyses'])}")
print(f"생성된 액션: {len(result['actions'])}")
```

## 모듈 구조

### `log_collector.py`
- 로컬 파일, 디렉토리, Kubernetes Pod에서 로그 수집
- 지원 소스: 파일, 디렉토리, Pod, 라벨 셀렉터, 표준 입력

### `error_classifier.py`
- 키워드 기반 에러 카테고리 분류
- 10가지 에러 카테고리 지원 (네트워크, 인증, 리소스 부족 등)

### `root_cause_analyzer.py`
- Gemini LLM을 사용한 근본 원인 분석
- 에러 카테고리별 상세 분석 및 해결 방안 제시

### `git_action.py`
- 분석 결과를 바탕으로 Git 액션 생성
- Kubernetes 설정 파일, 패치 파일, 분석 리포트 생성
- Git 커밋 수행 (시뮬레이션 모드 지원)

### `log_analysis_agent.py`
- 전체 워크플로우 관리
- 8단계 프로세스 실행 및 결과 통합

## 에러 카테고리

에이전트는 다음 10가지 에러 카테고리를 지원합니다:

1. **네트워크 오류**: 연결 거부, 타임아웃, DNS 오류 등
2. **인증/인가 오류**: 인증 실패, 권한 거부 등
3. **리소스 부족**: 메모리 부족, CPU 스로틀링 등
4. **파일 시스템 오류**: 파일 없음, 권한 거부, 디스크 풀 등
5. **데이터베이스 오류**: SQL 오류, 연결 풀, 데드락 등
6. **애플리케이션 오류**: 예외, 패닉, 크래시 등
7. **컨테이너/Kubernetes 오류**: Pod 오류, 이미지 풀 실패 등
8. **서비스 의존성 오류**: 서비스 불가, 게이트웨이 오류 등
9. **설정 오류**: 설정 파일 파싱 오류 등
10. **기타 오류**: 분류되지 않은 기타 오류

## 출력 파일

에이전트는 다음 디렉토리에 파일을 생성합니다:

- `patches/`: Kubernetes 설정 파일 및 패치 파일
- `reports/`: 분석 리포트 파일

## 시뮬레이션 모드

기본적으로 에이전트는 시뮬레이션 모드로 실행됩니다:
- 실제 파일 변경 없이 액션 미리보기
- Git 커밋 시뮬레이션
- 복구 검증 시뮬레이션

실제 파일 변경 및 커밋을 수행하려면 `--no-simulate` 옵션을 사용하세요.

## 주의사항

1. **프로덕션 환경**: 프로덕션 환경에서는 시뮬레이션 모드를 사용하고, 생성된 파일을 검토한 후 수동으로 적용하는 것을 권장합니다.

2. **API 키 보안**: `GOOGLE_API_KEY`는 안전하게 관리하세요. `.env` 파일을 Git에 커밋하지 마세요.

3. **자동 승인**: `AUTO_APPROVE=false`로 설정하여 중요한 변경사항에 대해 사용자 승인을 받는 것을 권장합니다.

4. **Kubernetes 접근**: Kubernetes Pod에서 로그를 수집하려면 적절한 권한이 필요합니다.

## 트러블슈팅

### "GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다" 오류

`.env` 파일을 생성하고 `GOOGLE_API_KEY`를 설정하세요.

### Kubernetes Pod 로그 수집 실패

- `kubectl`이 설치되어 있고 클러스터에 접근 가능한지 확인
- `KUBECONFIG_PATH` 환경 변수가 올바르게 설정되었는지 확인
- Pod 이름과 네임스페이스가 올바른지 확인

### 분석 결과가 부정확한 경우

- 더 많은 로그를 제공하세요 (최대 20개 로그만 분석에 사용됨)
- `additional_context` 파라미터를 사용하여 추가 컨텍스트 제공
- 에러 카테고리 키워드를 `error_classifier.py`에서 조정

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

