# AI DrKube - Kubernetes 장애 분석/조치 AI Agent

Kubernetes 환경의 장애를 자동으로 분석하고 조치하는 AI Agent입니다.

## 기술 스택

- **LLM**: Google Gemini
- **프레임워크**: LangGraph
- **언어**: Python 3.10+

## 빠른 시작

### 1. 환경 설정

```bash
# pyenv로 Python 3.10+ 설치 (이미 설치되어 있다면 생략)
pyenv install 3.11.0  # 또는 원하는 버전

# 프로젝트 디렉토리에서 Python 버전 설정
cd ai-drkube
pyenv local 3.11.0

# pyenv-virtualenv로 가상환경 생성
pyenv virtualenv 3.11.0 ai-drkube
pyenv activate ai-drkube

# 또는 pyenv-virtualenv가 없다면
# pyenv virtualenv 3.11.0 ai-drkube
# pyenv local ai-drkube

# 패키지 설치
pip install -r requirements.txt

# 환경 변수 설정
cp env.example .env
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

```bash
python main.py
```

## 프로젝트 구조

```
ai-drkube/
├── requirements.txt          # Python 패키지 의존성
├── .env.example              # 환경 변수 예시
├── requirements.md           # 상세 구축 가이드
├── config/                  # 설정 파일
├── agents/                   # Agent 구현
├── tools/                    # Kubernetes 도구
├── knowledge/                # 지식 베이스
└── main.py                   # 메인 실행 파일
```

## 주요 기능

1. **장애 감지**: Kubernetes 리소스 상태 모니터링
2. **장애 분석**: LLM을 통한 원인 분석
3. **조치 제안**: 자동 해결 방안 생성
4. **조치 실행**: (선택적) 자동 조치 수행

## 보안 주의사항

⚠️ **프로덕션 환경에서는 자동 조치를 비활성화하세요!**

- `.env` 파일의 `AUTO_REMEDIATION=false` 설정 권장
- 모든 조치는 수동 승인 후 실행
- 최소 권한 원칙 적용

## 상세 가이드

자세한 구축 가이드는 [requirements.md](./requirements.md)를 참고하세요.

