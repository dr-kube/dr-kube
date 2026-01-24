# AI DrKube - Kubernetes 장애 분석/조치 AI Agent

Kubernetes 환경의 장애를 자동으로 분석하고 조치하는 AI Agent입니다.

## 기술 스택

- **LLM**: Google Gemini
- **프레임워크**: LangGraph
- **언어**: Python 3.10+

## 빠른 시작

### Windows 사용자

**간편 설정 (권장)**

1. `setup.bat` 실행 (가상환경 생성 및 패키지 설치)
2. `.env` 파일 확인 (이미 설정되어 있음)
3. 샘플 데이터로 테스트:
   ```cmd
   run.bat issues\sample_oom.json
   ```

자세한 내용은 [WINDOWS_SETUP.md](./WINDOWS_SETUP.md)를 참고하세요.

### Linux/macOS 사용자

```bash
# pyenv로 Python 3.10+ 설치 (이미 설치되어 있다면 생략)
pyenv install 3.11.14  # 또는 원하는 버전

# 프로젝트 디렉토리에서 Python 버전 설정
cd ai-drkube
pyenv local 3.11.14

# pyenv-virtualenv로 가상환경 생성
pyenv virtualenv 3.11.14 ai-drkube
pyenv activate ai-drkube

# 패키지 설치
pip install -r src/requirements.txt

# 환경 변수 설정
cp env.sample .env
# .env 파일을 열어서 GOOGLE_API_KEY를 설정하세요
```

### 2. Gemini API 키 발급

1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
2. API 키 생성
3. `.env` 파일에 `GOOGLE_API_KEY` 설정

### 3. Kubernetes 접근 설정

```bash
# kubectl이 설치되어 있고 kubeconfig가 설정되어 있는지 확인
kubectl get nodes

# 필요시 kubeconfig 경로를 .env에 설정
# KUBECONFIG_PATH=/path/to/kubeconfig
```

### 4. 실행

**Windows:**
```cmd
run.bat issues\sample_oom.json
```

**Linux/macOS:**
```bash
cd src
python -m cli analyze ../issues/sample_oom.json
```

## 프로젝트 구조

```
agent/
├── setup.bat                 # Windows 설정 스크립트
├── run.bat                   # Windows 실행 스크립트
├── run_tools.bat             # Windows 도구 실행 스크립트
├── requirements.txt          # Python 패키지 의존성
├── .env                      # 환경 변수 (API 키 등)
├── env.sample                # 환경 변수 예시
├── WINDOWS_SETUP.md          # Windows 설정 가이드
├── src/                      # 소스 코드
│   ├── cli.py               # CLI 엔트리포인트
│   ├── requirements.txt     # 실제 패키지 의존성
│   └── dr_kube/             # 메인 패키지
│       ├── graph.py         # LangGraph 구현
│       ├── llm.py           # LLM 설정
│       ├── prompts.py       # 프롬프트 템플릿
│       └── state.py         # 상태 관리
├── tools/                    # 분석 도구
│   ├── log_analysis_agent.py
│   ├── error_classifier.py
│   ├── root_cause_analyzer.py
│   └── alert_webhook_server.py
└── issues/                   # 샘플 이슈 파일
    ├── sample_oom.json
    ├── sample_image_pull.json
    └── sample_cpu_throttle.json
```

## 작동 방식

```
이슈 파일 (JSON)
      ↓
 [1. 이슈 로드]
      ↓
 [2. AI 분석]  ← Google Gemini
      ↓
 [3. 결과 출력]
      ↓
   📋 결과
```

**3단계 워크플로우**:
1. **Load**: JSON 파일에서 K8s 이슈 읽기
2. **Analyze**: Gemini AI로 근본 원인 및 해결책 분석
3. **Suggest**: 간결하고 실행 가능한 결과 출력

자세한 내용은 [ARCHITECTURE.md](./ARCHITECTURE.md)를 참고하세요.

## 주요 기능

1. **장애 감지**: Kubernetes 리소스 상태 모니터링
2. **장애 분석**: LLM을 통한 근본 원인 분석
3. **조치 제안**: 3단계 해결책 제시 (즉시/근본/모니터링)
4. **⚡ 실행 계획**: 즉시 적용 가능한 kubectl 명령어 생성
5. **📝 YAML Diff**: 변경이 필요한 설정을 diff 형식으로 표시
6. **조치 실행**: (선택적) 자동 조치 수행

### ✨ 새로운 기능 (v1.1.0)

#### ⚡ 실행 계획
```bash
# 즉시 실행 가능한 kubectl 명령어
kubectl patch deployment api-server -n production \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value":"1Gi"}]'
```

#### 📝 YAML 수정 (Diff)
```yaml
spec:
  resources:
    limits:
❌ -     memory: 512Mi  # Before
✅ +     memory: 1Gi     # After
```

## 보안 주의사항

⚠️ **프로덕션 환경에서는 자동 조치를 비활성화하세요!**

- `.env` 파일의 `AUTO_REMEDIATION=false` 설정 권장
- 모든 조치는 수동 승인 후 실행
- 최소 권한 원칙 적용

## 📚 문서

- **[QUICKSTART_KR.md](./QUICKSTART_KR.md)** - 빠른 시작 가이드 (한글)
- **[WINDOWS_SETUP.md](./WINDOWS_SETUP.md)** - Windows 상세 설정
- **[USAGE.md](./USAGE.md)** - 사용 방법 및 예제
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - 아키텍처 및 작동 원리
- **[CHANGELOG.md](./CHANGELOG.md)** - 변경 이력
- **[SUMMARY.md](./SUMMARY.md)** - 전체 요약

