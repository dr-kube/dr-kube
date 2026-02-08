#!/bin/bash
# =============================================================================
# K8s 원격 접근 설정 스크립트 (macOS)
# Tailscale + kubeconfig 설정
# =============================================================================

set -e

echo "🐳 K8s 원격 접근 설정 시작..."
echo ""

# -----------------------------------------------------------------------------
# 1. Tailscale 설치
# -----------------------------------------------------------------------------
echo "📦 1단계: Tailscale 설치 확인..."

if command -v tailscale &> /dev/null; then
    echo "✅ Tailscale 이미 설치됨"
else
    echo "⏳ Tailscale 설치 중..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - App Store 버전 권장이지만, brew cask로 설치
        if command -v brew &> /dev/null; then
            brew install --cask tailscale || {
                echo ""
                echo "⚠️  자동 설치 실패. 수동 설치 필요:"
                echo "   → App Store에서 'Tailscale' 검색 후 설치"
                echo "   → 또는 https://tailscale.com/download/mac"
                exit 1
            }
        else
            echo "❌ Homebrew 없음. 수동 설치 필요:"
            echo "   → App Store에서 'Tailscale' 검색 후 설치"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -fsSL https://tailscale.com/install.sh | sh
    fi
fi

# -----------------------------------------------------------------------------
# 2. Tailscale 실행 & 로그인
# -----------------------------------------------------------------------------
echo ""
echo "🔐 2단계: Tailscale 로그인..."

# macOS에서는 앱 실행 필요
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! pgrep -x "Tailscale" > /dev/null; then
        echo "⏳ Tailscale 앱 실행 중..."
        open -a Tailscale 2>/dev/null || {
            echo ""
            echo "⚠️  Tailscale 앱을 수동으로 실행해주세요:"
            echo "   → Spotlight (Cmd+Space) → 'Tailscale' 입력 → 실행"
            echo ""
            read -p "실행 후 Enter를 눌러주세요..."
        }
        sleep 3
    fi
fi

# 로그인 상태 확인
if tailscale status &>/dev/null; then
    echo "✅ Tailscale 로그인됨"
else
    echo ""
    echo "🔗 Tailscale 로그인이 필요합니다."
    echo "   → 메뉴바의 Tailscale 아이콘 클릭 → Log in"
    echo ""
    read -p "로그인 완료 후 Enter를 눌러주세요..."
fi

# -----------------------------------------------------------------------------
# 3. Tailscale IP 확인
# -----------------------------------------------------------------------------
echo ""
echo "🌐 3단계: Tailscale IP 확인..."

TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")

if [ -z "$TAILSCALE_IP" ]; then
    echo "❌ Tailscale IP를 가져올 수 없습니다."
    echo "   → Tailscale이 연결되어 있는지 확인해주세요."
    exit 1
fi

echo "✅ Tailscale IP: $TAILSCALE_IP"

# -----------------------------------------------------------------------------
# 4. kubeconfig 생성 (원격 접근용)
# -----------------------------------------------------------------------------
echo ""
echo "📄 4단계: 원격 접근용 kubeconfig 생성..."

KUBECONFIG_SRC="${KUBECONFIG:-$HOME/.kube/config}"
KUBECONFIG_REMOTE="$HOME/.kube/config-remote"

if [ ! -f "$KUBECONFIG_SRC" ]; then
    echo "❌ kubeconfig 파일을 찾을 수 없습니다: $KUBECONFIG_SRC"
    exit 1
fi

# 127.0.0.1 또는 localhost를 Tailscale IP로 변경
sed "s/127\.0\.0\.1/$TAILSCALE_IP/g; s/localhost/$TAILSCALE_IP/g" \
    "$KUBECONFIG_SRC" > "$KUBECONFIG_REMOTE"

echo "✅ 생성됨: $KUBECONFIG_REMOTE"

# -----------------------------------------------------------------------------
# 5. 결과 출력
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "🎉 설정 완료!"
echo "=============================================="
echo ""
echo "📋 다른 PC에서 접근하려면:"
echo ""
echo "1. 다른 PC에도 Tailscale 설치 & 같은 계정 로그인"
echo ""
echo "2. 이 파일을 다른 PC로 복사:"
echo "   $KUBECONFIG_REMOTE"
echo ""
echo "3. 다른 PC에서 실행:"
echo "   export KUBECONFIG=~/config-remote"
echo "   kubectl get nodes"
echo "   k9s"
echo ""
echo "🔗 Tailscale IP: $TAILSCALE_IP"
echo "=============================================="
