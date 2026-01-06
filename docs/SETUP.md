# 개발 환경 설정 가이드

DR-Kube 프로젝트의 개발 환경을 설정하는 방법을 설명합니다.

## 📋 요구사항

- **Python**: 3.11.14 (고정)
- **OS**: macOS, Linux, Windows (WSL2 권장)
- **Git**: 최신 버전
- **Kubernetes**: 클러스터 접근 가능

## 🚀 빠른 설정 (macOS)

### 1단계: Python 버전 관리 도구 설치

**pyenv 설치 (Homebrew 사용)**

```bash
brew install pyenv
```

**pyenv 초기화**

```bash
# ~/.zshrc 또는 ~/.bash_profile에 추가
eval "$(pyenv init -)"
```

셸을 재시작하거나 다음 명령어 실행:
```bash
exec zsh
```

### 2단계: Python 3.11.14 설치

```bash
pyenv install 3.11.14
```

**설치 시간**: 약 5-10분 (네트워크 속도에 따라 다름)

### 3단계: 프로젝트 Python 버전 설정

```bash
# 프로젝트 루트로 이동
cd /Users/jonghwabaek/dockerkube/dr-kube

# Python 버전 설정
pyenv local 3.11.14

# 확인
python --version
# Output: Python 3.11.14
```

이 명령어는 프로젝트 루트에 `.python-version` 파일을 생성합니다.

### 4단계: 가상환경 생성

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 가상환경 활성화 (Windows - PowerShell)
venv\Scripts\Activate.ps1

# 가상환경 활성화 (Windows - CMD)
venv\Scripts\activate.bat
```

**확인**:
```bash
which python
# Output: /Users/jonghwabaek/dockerkube/dr-kube/venv/bin/python
```

### 5단계: 의존성 설치

```bash
# pip 업그레이드
pip install --upgrade pip

# 의존성 설치
pip install -r langraph/requirements.txt
```

### 6단계: 환경 변수 설정

```bash
cd langraph

# .env.example을 .env로 복사
cp .env.example .env

# .env 파일 편집 (필요한 API 키 추가)
nano .env
```

## 📁 디렉토리 구조

```
dr-kube/
├── .python-version          # Python 3.11.14 (자동 생성)
├── venv/                    # 가상환경
├── langraph/
│   ├── requirements.txt     # Python 패키지 목록
│   ├── .env                 # 환경 변수 (Git 무시)
│   └── .env.example         # 환경 변수 예시
└── docs/
    └── SETUP.md            # 이 파일
```

## 🔄 가상환경 활성화/비활성화

**활성화**:
```bash
source venv/bin/activate
```

**비활성화**:
```bash
deactivate
```

**확인** (활성화 상태):
```bash
# 프롬프트에 (venv) 표시
(venv) user@machine dr-kube %
```

## 🧪 설정 확인

모든 설정이 완료되었는지 확인합니다.

```bash
# 1. Python 버전 확인
python --version
# Output: Python 3.11.14

# 2. 가상환경 확인
which python
# Output: .../venv/bin/python

# 3. 패키지 확인
pip list
# LangGraph, LangChain 등이 나열되어야 함

# 4. 프로젝트 루트에 .python-version 파일 확인
cat .python-version
# Output: 3.11.14
```

## 💡 문제 해결

### Python 버전이 변경되지 않음

```bash
# pyenv 초기화 다시 확인
eval "$(pyenv init -)"

# 셸 재시작
exec zsh
```

### "pyenv: command not found" 에러

```bash
# pyenv 설치 확인
brew install pyenv

# 초기화 파일에 추가되었는지 확인
cat ~/.zshrc | grep pyenv

# 없으면 추가
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# 적용
exec zsh
```

### 패키지 설치 실패

```bash
# pip 업그레이드
pip install --upgrade pip

# 캐시 삭제 후 재설치
pip install --no-cache-dir -r langraph/requirements.txt
```

### "No module named 'langraph'" 에러

```bash
# 가상환경 활성화 확인
source venv/bin/activate

# 현재 디렉토리 확인
pwd
# /Users/jonghwabaek/dockerkube/dr-kube 이어야 함

# 패키지 재설치
pip install -r langraph/requirements.txt
```

## 👥 팀 협업

### 새로운 팀원을 위한 체크리스트

- [ ] `pyenv install 3.11.14` 실행
- [ ] 프로젝트 폴더에서 `pyenv local 3.11.14` 실행
- [ ] `python -m venv venv` 실행
- [ ] `source venv/bin/activate` 실행
- [ ] `pip install -r langraph/requirements.txt` 실행
- [ ] `cd langraph && cp .env.example .env` 실행
- [ ] `.env` 파일의 API 키 설정
- [ ] `python --version`으로 Python 3.11.14 확인

### 버전 동기화

프로젝트는 다음 파일들로 Python 버전을 관리합니다:

| 파일 | 용도 | 자동 생성 |
|------|------|---------|
| `.python-version` | pyenv 설정 | ✅ `pyenv local 3.11.14` |
| `langraph/requirements.txt` | pip 패키지 목록 | - |
| `docs/SETUP.md` | 설정 가이드 | - |

새로운 패키지 추가 시:
```bash
pip install <package-name>
pip freeze > langraph/requirements.txt
git add langraph/requirements.txt
git commit -m "chore: update dependencies"
git push
```

## 🚀 다음 단계

설정이 완료되면 다음 작업을 진행합니다:

1. **LangGraph CLI 테스트**
   ```bash
   python -m langraph.cli.main --help
   ```

2. **예시 로그로 테스트**
   ```bash
   python -m langraph.cli.main --log-file langraph/examples/sample_log_oom.txt --dry-run
   ```

3. **서버 실행** (향후 구현)
   ```bash
   python -m langraph.main
   ```

## 📚 참고 자료

- [pyenv 공식 문서](https://github.com/pyenv/pyenv)
- [Python 가상환경 가이드](https://docs.python.org/3/library/venv.html)
- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)

## 💬 문의

설정 중 문제가 발생하면:
1. 이 문서의 **문제 해결** 섹션 확인
2. GitHub Issues 생성
3. 팀 Slack 채널에 질문

---

마지막 업데이트: 2026년 1월 2일
