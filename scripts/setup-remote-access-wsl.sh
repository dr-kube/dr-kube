#!/bin/bash
# =============================================================================
# K8s 원격 접근 설정 스크립트 (WSL / Linux)
# Tailscale + kubeconfig 설정
# =============================================================================

set -e

echo "🐳 K8s 원격 접근 설정 (WSL/Linux)..."
echo ""

# -----------------------------------------------------------------------------
# 1. Tailscale 설치
# -----------------------------------------------------------------------------
echo "📦 1단계: Tailscale 설치..."

if command -v tailscale &> /dev/null; then
    echo "✅ Tailscale 이미 설치됨"
else
    echo "⏳ Tailscale 설치 중..."
    curl -fsSL https://tailscale.com/install.sh | sh
fi

# -----------------------------------------------------------------------------
# 2. Tailscale 시작 & 로그인
# -----------------------------------------------------------------------------
echo ""
echo "🔐 2단계: Tailscale 시작..."

# WSL에서는 tailscaled를 수동으로 실행해야 함
if ! pgrep -x "tailscaled" > /dev/null; then
    echo "⏳ tailscaled 시작 중..."
    sudo tailscaled --state=/var/lib/tailscale/tailscaled.state &
    sleep 3
fi

# 로그인 상태 확인
if ! tailscale status &>/dev/null; then
    echo ""
    echo "🔗 Tailscale 로그인 필요:"
    echo ""
    sudo tailscale up
    echo ""
fi

echo "✅ Tailscale 연결됨"

# -----------------------------------------------------------------------------
# 3. Tailscale IP 확인
# -----------------------------------------------------------------------------
echo ""
echo "🌐 3단계: Tailscale IP 확인..."

TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")

if [ -z "$TAILSCALE_IP" ]; then
    echo "❌ Tailscale IP를 가져올 수 없습니다."
    exit 1
fi

echo "✅ Tailscale IP: $TAILSCALE_IP"

# -----------------------------------------------------------------------------
# 4. kubeconfig 설정 (원격에서 가져온 경우)
# -----------------------------------------------------------------------------
echo ""
echo "📄 4단계: kubeconfig 설정..."

KUBE_DIR="$HOME/.kube"
KUBECONFIG_REMOTE="$KUBE_DIR/config-remote"

mkdir -p "$KUBE_DIR"

if [ -f "$KUBECONFIG_REMOTE" ]; then
    echo "✅ 원격 kubeconfig 존재: $KUBECONFIG_REMOTE"
else
    echo ""
    echo "⚠️  원격 kubeconfig 파일이 필요합니다."
    echo ""
    echo "   K8s가 실행 중인 맥북에서:"
    echo "   1. ./scripts/setup-remote-access.sh 실행"
    echo "   2. ~/.kube/config-remote 파일을 이 PC로 복사"
    echo ""
    echo "   복사 명령어 (맥북에서 실행):"
    echo "   scp ~/.kube/config-remote user@windows-pc:~/.kube/"
    echo ""
fi

# -----------------------------------------------------------------------------
# 5. kubectl & k9s 설치 확인
# -----------------------------------------------------------------------------
echo ""
echo "🔧 5단계: kubectl & k9s 확인..."

if ! command -v kubectl &> /dev/null; then
    echo "⏳ kubectl 설치 중..."
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    rm kubectl
fi
echo "✅ kubectl: $(kubectl version --client --short 2>/dev/null || kubectl version --client | head -1)"

if ! command -v k9s &> /dev/null; then
    echo "⏳ k9s 설치 중..."
    curl -sS https://webinstall.dev/k9s | bash
    export PATH="$HOME/.local/bin:$PATH"
fi
echo "✅ k9s 설치됨"

# -----------------------------------------------------------------------------
# 6. 결과 출력
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "🎉 설정 완료!"
echo "=============================================="
echo ""
echo "📋 K8s 접근 방법:"
echo ""
echo "1. 맥북에서 config-remote 파일 복사:"
echo "   scp user@macbook:~/.kube/config-remote ~/.kube/"
echo ""
echo "2. K8s 접근:"
echo "   export KUBECONFIG=~/.kube/config-remote"
echo "   kubectl get nodes"
echo "   k9s"
echo ""
echo "3. 영구 설정 (~/.bashrc 또는 ~/.zshrc에 추가):"
echo '   echo "export KUBECONFIG=~/.kube/config-remote" >> ~/.bashrc'
echo ""
echo "🔗 이 PC의 Tailscale IP: $TAILSCALE_IP"
echo "=============================================="
