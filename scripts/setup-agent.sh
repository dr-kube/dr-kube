#!/bin/bash
set -e

# 프로젝트 루트 디렉토리 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
AGENT_DIR="$PROJECT_ROOT/agent"

echo "=========================================="
echo "  DR-Kube Agent 설정"
echo "=========================================="

# Homebrew 설치 확인 (macOS, Linux, WSL)
if ! command -v brew &> /dev/null; then
    echo "[1/6] Homebrew 설치 중..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # brew PATH 설정
    if [[ "$OSTYPE" == "darwin"* ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || eval "$(/usr/local/bin/brew shellenv)"
    else
        eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
    fi
    echo "✅ Homebrew 설치 완료"
else
    echo "[1/6] Homebrew 이미 설치됨"
fi

# make 설치 확인
if ! command -v make &> /dev/null; then
    echo "[2/6] make 설치 중..."
    brew install make
else
    echo "[2/6] make 이미 설치됨"
fi

# uv 설치 확인
if ! command -v uv &> /dev/null; then
    echo "[3/6] uv 설치 중..."
    brew install uv
else
    echo "[3/6] uv 이미 설치됨"
fi

# agent 디렉토리로 이동
cd "$AGENT_DIR"

# 가상환경 생성
echo "[4/6] 가상환경 생성 중..."
uv venv

# 의존성 설치
echo "[5/6] 의존성 설치 중..."
source .venv/bin/activate
uv pip install -r requirements.txt

# .env 파일 생성
if [ ! -f .env ]; then
    echo "[6/6] .env 파일 생성 중..."
    cp .env.example .env
    echo ""
    echo "⚠️  agent/.env 파일을 편집하여 API 키를 설정하세요:"
    echo "    LLM_PROVIDER=gemini"
    echo "    GEMINI_API_KEY=your-api-key"
else
    echo "[6/6] .env 파일 이미 존재"
fi

echo ""
echo "=========================================="
echo "  설정 완료!"
echo "=========================================="
echo ""
echo "실행 방법 (프로젝트 루트에서):"
echo "  make agent-run           # 기본 이슈 분석"
echo "  make agent-oom           # OOM 이슈"
echo "  make help                # 전체 명령어"
echo ""
