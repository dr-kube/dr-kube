# AI DrKube 빠른 시작 가이드 (Windows)

## 3단계로 시작하기

### 1단계: Python 설치 확인

Python 3.10 이상이 필요합니다.

1. Python 설치 여부 확인:
   - `cmd` 또는 `PowerShell` 열기
   - `python --version` 입력

2. Python이 없다면:
   - [Python 다운로드](https://www.python.org/downloads/)
   - 설치 시 **"Add Python to PATH"** 체크 필수!

### 2단계: 환경 설정

프로젝트 폴더에서 `setup.bat` 더블클릭 또는 명령창에서:

```cmd
setup.bat
```

이 과정은 처음 한 번만 하면 됩니다.

### 3단계: 실행

#### A. 장애 분석 테스트 (K8S 없이)

```cmd
run.bat issues\sample_oom.json
```

**다른 샘플 파일:**
- `run.bat issues\sample_image_pull.json` - 이미지 Pull 실패
- `run.bat issues\sample_cpu_throttle.json` - CPU Throttle 이슈

#### B. 로그 분석 테스트

```cmd
run_tools.bat log_analysis_agent.py tools\sample_error.log
```

## 환경 변수 설정

`.env` 파일은 이미 생성되어 있습니다. Google Gemini API 키가 필요합니다:

1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
2. API 키 생성
3. `.env` 파일 열기
4. `GOOGLE_API_KEY=your-api-key` 수정

## 주요 설정 (.env)

```env
# 필수: Google Gemini API 키
GOOGLE_API_KEY=your-api-key-here

# AI 모델 (gemini-pro, gemini-3-flash-preview 등)
MODEL_NAME=gemini-3-flash-preview

# 시뮬레이션 모드 (true: 파일 변경 안 함, false: 실제 변경)
SIMULATE=true

# 자동 승인 (true: 자동, false: 수동 승인)
AUTO_APPROVE=true

# 상호작용 모드 (true: UI 표시, false: 자동 분석)
INTERACTIVE_MODE=true
```

## 실행 예시

### 예시 1: OOM (메모리 부족) 이슈 분석

```cmd
run.bat issues\sample_oom.json
```

**예상 결과:**
```
이슈 분석 중: issues\sample_oom.json

==================================================
DR-Kube 분석 결과
==================================================
이슈: CrashLoopBackOff (api-server-7d4f8b9c5-xyz)
심각도: HIGH

근본 원인:
  컨테이너가 메모리 제한(512Mi)을 초과하여 OOMKilled 되었습니다.

해결책:
  1. 메모리 제한을 증가시킵니다 (예: 1Gi)
  2. 애플리케이션의 메모리 사용량을 최적화합니다
  3. 메모리 프로파일링을 수행합니다
==================================================

승인하시겠습니까? (y/n):
```

### 예시 2: 로그 분석

```cmd
run_tools.bat log_analysis_agent.py tools\sample_error.log
```

에러를 분류하고 근본 원인을 분석한 후 해결책을 제안합니다.

## 다음 단계

### Kubernetes 없이 사용하기 (현재)
- ✅ 샘플 이슈 파일로 테스트
- ✅ 로그 파일 분석
- ✅ AI 기반 근본 원인 분석 학습

### Kubernetes와 연동하기 (추후)
1. **kubectl 설치**
   ```cmd
   # Chocolatey로 설치
   choco install kubernetes-cli

   # 또는 수동 다운로드
   # https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/
   ```

2. **kubeconfig 설정**
   - `.env` 파일에 경로 추가:
     ```env
     KUBECONFIG_PATH=C:\Users\YourName\.kube\config
     ```

3. **연결 확인**
   ```cmd
   kubectl get nodes
   ```

4. **실시간 모니터링**
   - Alertmanager Webhook 서버 실행:
     ```cmd
     run_tools.bat alert_webhook_server.py
     ```

## 문제 해결

### "Python을 찾을 수 없습니다"
- Python PATH 설정 확인
- 명령 프롬프트 재시작

### "가상환경이 없습니다"
- `setup.bat` 다시 실행

### 패키지 설치 오류
```cmd
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r src\requirements.txt
```

### API 키 오류
- `.env` 파일에서 `GOOGLE_API_KEY` 확인
- Google AI Studio에서 API 키 재생성

## 도움말

- 상세 가이드: [WINDOWS_SETUP.md](./WINDOWS_SETUP.md)
- 전체 README: [README.md](./README.md)
- 도구 가이드: [tools/README.md](./tools/README.md)
