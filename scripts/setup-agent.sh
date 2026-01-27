#!/bin/bash
set -e

# 프로젝트 루트 디렉토리 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
AGENT_DIR="$PROJECT_ROOT/agent"

echo "=========================================="
echo "  DR-Kube Agent 설정"
echo "=========================================="

# OS 감지
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    elif [[ -f /etc/redhat-release ]]; then
        echo "redhat"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)

# make 설치 확인
if ! command -v make &> /dev/null; then
    echo "[1/5] make 설치 중..."
    case $OS in
        macos)
            xcode-select --install 2>/dev/null || true
            ;;
        debian)
            if sudo -n true 2>/dev/null; then
                sudo apt-get update && sudo apt-get install -y make
            else
                echo "⚠️  make 설치에 sudo 권한이 필요합니다:"
                echo "    sudo apt-get install -y make"
            fi
            ;;
        redhat)
            if sudo -n true 2>/dev/null; then
                sudo yum install -y make
            else
                echo "⚠️  make 설치에 sudo 권한이 필요합니다:"
                echo "    sudo yum install -y make"
            fi
            ;;
        *)
            echo "⚠️  make를 수동으로 설치해주세요"
            ;;
    esac
else
    echo "[1/5] make 이미 설치됨"
fi

# uv 설치 확인
if ! command -v uv &> /dev/null; then
    echo "[2/5] uv 설치 중..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.local/bin/env"
else
    echo "[2/5] uv 이미 설치됨"
fi

# agent 디렉토리로 이동
cd "$AGENT_DIR"

# 가상환경 생성
echo "[3/5] 가상환경 생성 중..."
uv venv

# 의존성 설치
echo "[4/5] 의존성 설치 중..."
source .venv/bin/activate
uv pip install -r requirements.txt

# .env 파일 생성
if [ ! -f .env ]; then
    echo "[5/5] .env 파일 생성 중..."
    cp .env.example .env
    echo ""
    echo "⚠️  agent/.env 파일을 편집하여 API 키를 설정하세요:"
    echo "    LLM_PROVIDER=gemini"
    echo "    GEMINI_API_KEY=your-api-key"
else
    echo "[5/5] .env 파일 이미 존재"
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
