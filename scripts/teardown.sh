#!/bin/bash
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CLUSTER_NAME="dr-kube"

# 함수: 로그 출력
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

echo ""
echo "=========================================="
echo -e "${YELLOW}  DR-Kube 환경 삭제${NC}"
echo "=========================================="
echo ""

# 클러스터 존재 확인
if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    log_warn "클러스터 '${CLUSTER_NAME}'가 존재하지 않습니다."
    exit 0
fi

# 확인
read -p "정말로 클러스터 '${CLUSTER_NAME}'를 삭제하시겠습니까? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "삭제 취소됨"
    exit 0
fi

# 클러스터 삭제
log_info "Kind 클러스터 삭제 중..."
kind delete cluster --name "$CLUSTER_NAME"

log_success "클러스터 삭제 완료"

echo ""
echo "=========================================="
echo -e "${GREEN}  정리 완료!${NC}"
echo "=========================================="
echo ""
echo "다시 설치하려면: ./scripts/setup.sh"
echo ""
