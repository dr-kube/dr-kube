#!/bin/bash
set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

NAMESPACE="cert-manager"
SECRET_NAME="cloudflare-api-token"
ISSUER_NAME="letsencrypt-prod"

create_secret() {
    local TOKEN="$1"

    if [ -z "$TOKEN" ]; then
        echo ""
        read -rp "Cloudflare API 토큰 입력: " TOKEN
        echo ""
    fi

    if [ -z "$TOKEN" ]; then
        log_error "토큰이 비어있습니다."
        exit 1
    fi

    # cert-manager 네임스페이스 확인
    if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
        log_info "cert-manager 네임스페이스 생성 중..."
        kubectl create namespace "$NAMESPACE"
    fi

    # 기존 시크릿 삭제 후 재생성
    kubectl delete secret "$SECRET_NAME" -n "$NAMESPACE" 2>/dev/null || true
    kubectl create secret generic "$SECRET_NAME" \
        --from-literal=api-token="$TOKEN" \
        -n "$NAMESPACE"

    log_success "Cloudflare API 토큰 시크릿 생성 완료 ($NAMESPACE/$SECRET_NAME)"
}

create_issuer() {
    log_info "ClusterIssuer 생성 중..."

    # cert-manager CRD 대기
    log_info "cert-manager CRD 준비 대기 중..."
    for i in $(seq 1 30); do
        if kubectl get crd clusterissuers.cert-manager.io &>/dev/null; then
            break
        fi
        if [ "$i" -eq 30 ]; then
            log_error "cert-manager CRD가 준비되지 않았습니다. cert-manager가 설치되었는지 확인하세요."
            exit 1
        fi
        sleep 5
    done

    # cert-manager pod 대기
    kubectl wait --for=condition=available --timeout=120s deployment/cert-manager -n "$NAMESPACE" 2>/dev/null || true
    kubectl wait --for=condition=available --timeout=120s deployment/cert-manager-webhook -n "$NAMESPACE" 2>/dev/null || true
    sleep 5

    kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: $ISSUER_NAME
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: drkube@huik.site
    privateKeySecretRef:
      name: letsencrypt-prod-account-key
    solvers:
      - dns01:
          cloudflare:
            apiTokenSecretRef:
              name: $SECRET_NAME
              key: api-token
        selector:
          dnsZones:
            - "huik.site"
EOF

    log_success "ClusterIssuer '$ISSUER_NAME' 생성 완료"
}

show_status() {
    echo ""
    echo "=========================================="
    echo -e "${BLUE}  TLS 설정 상태${NC}"
    echo "=========================================="

    if kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" &>/dev/null; then
        echo -e "  Cloudflare 시크릿: ${GREEN}생성됨${NC}"
    else
        echo -e "  Cloudflare 시크릿: ${RED}없음${NC}"
    fi

    if kubectl get clusterissuer "$ISSUER_NAME" &>/dev/null; then
        local READY
        READY=$(kubectl get clusterissuer "$ISSUER_NAME" -o jsonpath='{.status.conditions[0].status}' 2>/dev/null)
        if [ "$READY" = "True" ]; then
            echo -e "  ClusterIssuer:     ${GREEN}Ready${NC}"
        else
            echo -e "  ClusterIssuer:     ${YELLOW}Not Ready${NC}"
        fi
    else
        echo -e "  ClusterIssuer:     ${RED}없음${NC}"
    fi

    # 인증서 상태
    echo ""
    echo "  [인증서]"
    kubectl get certificate -A --no-headers 2>/dev/null | while read -r ns name ready secret age; do
        if [ "$ready" = "True" ]; then
            echo -e "  ${GREEN}✓${NC} $ns/$name"
        else
            echo -e "  ${RED}✗${NC} $ns/$name"
        fi
    done || echo "  (없음)"

    echo "=========================================="
    echo ""
}

usage() {
    echo "사용법: $0 [setup|status]"
    echo ""
    echo "  setup    Cloudflare 시크릿 + ClusterIssuer 생성"
    echo "  status   TLS 설정 상태 확인"
    echo ""
    echo "환경변수:"
    echo "  CF_API_TOKEN    Cloudflare API 토큰 (미설정 시 입력 프롬프트)"
    echo ""
    echo "예시:"
    echo "  $0 setup                              # 대화형 입력"
    echo "  CF_API_TOKEN=xxx $0 setup             # 환경변수로 전달"
}

case "${1:-setup}" in
    setup)
        create_secret "${CF_API_TOKEN:-}"
        create_issuer
        show_status
        ;;
    status)
        show_status
        ;;
    help|-h)
        usage
        ;;
    *)
        log_error "알 수 없는 옵션: $1"
        usage
        exit 1
        ;;
esac
