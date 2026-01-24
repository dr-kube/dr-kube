# AI DrKube - Windows 설정 가이드

Windows 환경에서 AI DrKube를 실행하기 위한 단계별 가이드입니다.

## 사전 요구사항

### 1. Python 3.10 이상 설치

Python이 설치되어 있지 않다면:
1. [Python 공식 사이트](https://www.python.org/downloads/)에서 Python 3.10 이상 다운로드
2. 설치 시 **"Add Python to PATH"** 옵션 체크 필수
3. 설치 확인:
   ```cmd
   python --version
   ```

### 2. Git 설치 (선택사항)

로그 분석 도구에서 Git 기능을 사용하려면:
- [Git for Windows](https://git-scm.com/download/win) 다운로드 및 설치

## 빠른 시작

### 1단계: 환경 설정

프로젝트 디렉토리에서 `setup.bat` 실행:

```cmd
setup.bat
```

이 스크립트는 다음을 수행합니다:
- Python 버전 확인
- 가상환경 생성 (`venv` 폴더)
- 필요한 Python 패키지 설치
- 환경 변수 파일 확인

### 2단계: 환경 변수 확인

`.env` 파일이 이미 생성되어 있고 Google Gemini API 키가 설정되어 있습니다:

```env
GOOGLE_API_KEY=your-api-key-here
```

> 💡 **참고**: API 키는 [Google AI Studio](https://makersuite.google.com/app/apikey)에서 발급받을 수 있습니다.

### 3단계: 실행

#### A. 샘플 이슈 분석 (K8S 없이 테스트)

```cmd
run.bat issues\sample_oom.json
```

사용 가능한 샘플 파일:
- `issues\sample_oom.json` - Out Of Memory 이슈
- `issues\sample_image_pull.json` - 이미지 Pull 실패
- `issues\sample_cpu_throttle.json` - CPU Throttle 이슈

#### B. 로그 분석 도구

```cmd
run_tools.bat log_analysis_agent.py tools\sample_error.log
```

사용 가능한 도구:
- `log_analysis_agent.py` - 로그 파일 분석 및 근본 원인 분석
- `error_classifier.py` - 에러 분류
- `root_cause_analyzer.py` - 근본 원인 분석
- `alert_webhook_server.py` - Alertmanager Webhook 서버

## 프로젝트 구조

```
agent/
├── setup.bat              # Windows 설정 스크립트
├── run.bat                # CLI 실행 스크립트
├── run_tools.bat          # 도구 실행 스크립트
├── .env                   # 환경 변수 (API 키 등)
├── venv/                  # Python 가상환경 (자동 생성)
├── src/                   # 소스 코드
│   ├── cli.py            # CLI 엔트리포인트
│   └── dr_kube/          # 메인 패키지
├── tools/                 # 분석 도구
└── issues/                # 샘플 이슈 파일
```

## Kubernetes 연동 (선택사항)

현재는 K8S 설정 없이 샘플 데이터로 테스트할 수 있습니다.

향후 K8S 클러스터와 연동하려면:

1. **kubectl 설치**
   - [Kubernetes Tools](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/) 참고

2. **kubeconfig 설정**
   - `.env` 파일에 경로 설정:
     ```env
     KUBECONFIG_PATH=C:\Users\YourName\.kube\config
     ```

3. **연결 확인**
   ```cmd
   kubectl get nodes
   ```

## 문제 해결

### Python을 찾을 수 없음
- Python이 PATH에 추가되었는지 확인
- 명령 프롬프트를 재시작

### 패키지 설치 실패
```cmd
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r src\requirements.txt
```

### 가상환경 수동 활성화
```cmd
venv\Scripts\activate.bat
```

### 가상환경 비활성화
```cmd
deactivate
```

## 주요 기능

### 1. 장애 분석 (CLI)
- Kubernetes 리소스 이슈 분석
- AI 기반 근본 원인 분석
- 해결 방안 제안

### 2. 로그 분석 도구
- 로그 파일에서 에러 패턴 추출
- 에러 분류 및 우선순위 결정
- 근본 원인 분석 및 해결책 제안
- Git을 통한 자동 문서화 (선택사항)

## 환경 설정 옵션

`.env` 파일에서 다음을 설정할 수 있습니다:

```env
# AI 모델
MODEL_NAME=gemini-3-flash-preview

# 시뮬레이션 모드 (파일 변경 없음)
SIMULATE=true

# 자동 승인
AUTO_APPROVE=true

# 상호작용 모드
INTERACTIVE_MODE=true

# 자동 조치 (주의: 프로덕션에서는 false 권장)
AUTO_REMEDIATION=false
```

## 다음 단계

1. 샘플 데이터로 기능 테스트
2. 실제 로그 파일로 분석 수행
3. Kubernetes 클러스터 연동 (선택)
4. Alertmanager Webhook 설정 (선택)

## 도움말

문제가 발생하면:
1. `.env` 파일에서 `LOG_LEVEL=DEBUG`로 설정
2. 로그 확인
3. [프로젝트 이슈](https://github.com/your-repo/issues) 등록
