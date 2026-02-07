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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SECRETS_PLAIN="$PROJECT_ROOT/secrets/secrets.yaml"
NAMESPACE="cloudflare"
SECRET_NAME="cloudflare-tunnel-token"
TUNNEL_NAME="dr-kube"
INGRESS_SVC="nginx-ingress-ingress-nginx-controller.ingress-nginx.svc.cluster.local"
DOMAIN_SUFFIX="-drkube.huik.site"
ZONE_NAME="huik.site"

# 서비스 도메인 목록
SERVICES=(
    "argocd"
    "grafana"
    "prometheus"
    "alert"
    "boutique"
    "chaos"
    "jaeger"
)

# secrets.yaml 에서 값 읽기
get_secret() {
    grep "^$1:" "$SECRETS_PLAIN" 2>/dev/null | sed "s/^$1: *//" | tr -d '"' | tr -d "'"
}

# secrets.yaml 에 값 저장
set_secret() {
    local KEY="$1" VALUE="$2"
    if [ -f "$SECRETS_PLAIN" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^${KEY}:.*|${KEY}: \"${VALUE}\"|" "$SECRETS_PLAIN"
        else
            sed -i "s|^${KEY}:.*|${KEY}: \"${VALUE}\"|" "$SECRETS_PLAIN"
        fi
    fi
}

# Cloudflare API 호출 헬퍼
cf_api() {
    local METHOD="$1" ENDPOINT="$2" DATA="${3:-}"
    local ARGS=(-s -X "$METHOD" -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json")
    if [ -n "$DATA" ]; then
        ARGS+=(-d "$DATA")
    fi
    curl "${ARGS[@]}" "https://api.cloudflare.com/client/v4${ENDPOINT}"
}

# JSON에서 값 추출 (jq 없이)
json_value() {
    python3 -c "import json,sys; d=json.load(sys.stdin); print($1)" 2>/dev/null
}

setup_tunnel() {
    echo ""
    echo "=========================================="
    echo -e "${BLUE}  Cloudflare Tunnel 자동 설정${NC}"
    echo "=========================================="
    echo ""

    # 1. API 토큰 로드
    if [ ! -f "$SECRETS_PLAIN" ]; then
        log_error "secrets/secrets.yaml 파일이 없습니다. make secrets-decrypt 를 먼저 실행하세요."
        exit 1
    fi

    CF_API_TOKEN=$(get_secret cloudflare_api_token)
    if [ -z "$CF_API_TOKEN" ]; then
        log_error "cloudflare_api_token 이 secrets.yaml에 설정되어 있지 않습니다."
        exit 1
    fi
    log_info "Cloudflare API 토큰 로드 완료"

    # 2. API 토큰 검증 및 Account ID 조회
    log_info "API 토큰 검증 중..."
    local ACCOUNT_RESP
    ACCOUNT_RESP=$(cf_api GET "/accounts?page=1&per_page=1")
    local ACCOUNT_ID
    ACCOUNT_ID=$(echo "$ACCOUNT_RESP" | json_value "d['result'][0]['id']")

    if [ -z "$ACCOUNT_ID" ] || [ "$ACCOUNT_ID" = "None" ]; then
        log_error "Account ID를 가져올 수 없습니다. API 토큰 권한을 확인하세요."
        echo "$ACCOUNT_RESP" | python3 -m json.tool 2>/dev/null || echo "$ACCOUNT_RESP"
        exit 1
    fi
    log_success "Account ID: $ACCOUNT_ID"

    # 3. 기존 터널 확인
    log_info "기존 터널 확인 중..."
    local TUNNELS_RESP TUNNEL_ID
    TUNNELS_RESP=$(cf_api GET "/accounts/${ACCOUNT_ID}/cfd_tunnel?name=${TUNNEL_NAME}&is_deleted=false")
    TUNNEL_ID=$(echo "$TUNNELS_RESP" | json_value "d['result'][0]['id'] if d['result'] else ''")

    if [ -n "$TUNNEL_ID" ] && [ "$TUNNEL_ID" != "None" ] && [ "$TUNNEL_ID" != "" ]; then
        log_info "기존 터널 발견: $TUNNEL_NAME ($TUNNEL_ID)"
    else
        # 4. 새 터널 생성
        log_info "터널 생성 중: $TUNNEL_NAME"
        local CREATE_RESP
        CREATE_RESP=$(cf_api POST "/accounts/${ACCOUNT_ID}/cfd_tunnel" \
            "{\"name\":\"${TUNNEL_NAME}\",\"tunnel_secret\":\"$(openssl rand -base64 32)\"}")
        TUNNEL_ID=$(echo "$CREATE_RESP" | json_value "d['result']['id']")

        if [ -z "$TUNNEL_ID" ] || [ "$TUNNEL_ID" = "None" ]; then
            log_error "터널 생성 실패"
            echo "$CREATE_RESP" | python3 -m json.tool 2>/dev/null || echo "$CREATE_RESP"
            exit 1
        fi
        log_success "터널 생성 완료: $TUNNEL_NAME ($TUNNEL_ID)"
    fi

    # 5. 터널 토큰 조회
    log_info "터널 토큰 조회 중..."
    local TOKEN_RESP TUNNEL_TOKEN
    TOKEN_RESP=$(cf_api GET "/accounts/${ACCOUNT_ID}/cfd_tunnel/${TUNNEL_ID}/token")
    TUNNEL_TOKEN=$(echo "$TOKEN_RESP" | json_value "d['result']")

    if [ -z "$TUNNEL_TOKEN" ] || [ "$TUNNEL_TOKEN" = "None" ]; then
        log_error "터널 토큰 조회 실패"
        echo "$TOKEN_RESP" | python3 -m json.tool 2>/dev/null || echo "$TOKEN_RESP"
        exit 1
    fi
    log_success "터널 토큰 조회 완료"

    # 6. 터널 설정 (ingress 규칙)
    log_info "터널 ingress 규칙 설정 중..."
    local INGRESS_RULES=""
    for svc in "${SERVICES[@]}"; do
        INGRESS_RULES+="{\"hostname\":\"${svc}${DOMAIN_SUFFIX}\",\"service\":\"http://${INGRESS_SVC}:80\"},"
    done
    # catch-all 규칙 추가
    INGRESS_RULES+="{\"service\":\"http_status:404\"}"

    local CONFIG_PAYLOAD="{\"config\":{\"ingress\":[${INGRESS_RULES}]}}"
    local CONFIG_RESP
    CONFIG_RESP=$(cf_api PUT "/accounts/${ACCOUNT_ID}/cfd_tunnel/${TUNNEL_ID}/configurations" "$CONFIG_PAYLOAD")
    local CONFIG_OK
    CONFIG_OK=$(echo "$CONFIG_RESP" | json_value "d['success']")

    if [ "$CONFIG_OK" = "True" ]; then
        log_success "터널 ingress 규칙 설정 완료"
    else
        log_warn "터널 ingress 설정 확인 필요"
        echo "$CONFIG_RESP" | python3 -m json.tool 2>/dev/null || echo "$CONFIG_RESP"
    fi

    # 7. DNS CNAME 레코드 생성
    log_info "DNS 레코드 설정 중..."
    local ZONE_RESP ZONE_ID
    ZONE_RESP=$(cf_api GET "/zones?name=${ZONE_NAME}")
    ZONE_ID=$(echo "$ZONE_RESP" | json_value "d['result'][0]['id']")

    if [ -z "$ZONE_ID" ] || [ "$ZONE_ID" = "None" ]; then
        log_warn "Zone ID를 가져올 수 없습니다. DNS 레코드를 수동으로 설정해주세요."
    else
        local TUNNEL_CNAME="${TUNNEL_ID}.cfargotunnel.com"
        for svc in "${SERVICES[@]}"; do
            local FQDN="${svc}${DOMAIN_SUFFIX}"
            # 기존 레코드 확인
            local EXISTING
            EXISTING=$(cf_api GET "/zones/${ZONE_ID}/dns_records?name=${FQDN}&type=CNAME")
            local EXISTING_ID
            EXISTING_ID=$(echo "$EXISTING" | json_value "d['result'][0]['id'] if d['result'] else ''")

            if [ -n "$EXISTING_ID" ] && [ "$EXISTING_ID" != "None" ] && [ "$EXISTING_ID" != "" ]; then
                # 기존 레코드 업데이트
                cf_api PUT "/zones/${ZONE_ID}/dns_records/${EXISTING_ID}" \
                    "{\"type\":\"CNAME\",\"name\":\"${FQDN}\",\"content\":\"${TUNNEL_CNAME}\",\"proxied\":true}" > /dev/null
            else
                # 새 레코드 생성
                cf_api POST "/zones/${ZONE_ID}/dns_records" \
                    "{\"type\":\"CNAME\",\"name\":\"${FQDN}\",\"content\":\"${TUNNEL_CNAME}\",\"proxied\":true}" > /dev/null
            fi
            echo "  ${FQDN} → ${TUNNEL_CNAME}"
        done
        log_success "DNS 레코드 설정 완료"
    fi

    # 8. secrets.yaml 에 터널 토큰 저장
    set_secret "cloudflare_tunnel_token" "$TUNNEL_TOKEN"
    log_success "secrets/secrets.yaml 에 터널 토큰 저장됨"

    # 9. K8s Secret 생성
    log_info "K8s Secret 생성 중..."
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null
    kubectl create secret generic "$SECRET_NAME" \
        --namespace "$NAMESPACE" \
        --from-literal=token="$TUNNEL_TOKEN" \
        --dry-run=client -o yaml | kubectl apply -f -
    log_success "Secret 생성 완료: $NAMESPACE/$SECRET_NAME"

    # 10. Deployment 적용
    log_info "cloudflared Deployment 적용 중..."
    kubectl apply -f "$PROJECT_ROOT/manifests/cloudflare-tunnel/"

    # 11. Pod 대기
    log_info "cloudflared Pod 시작 대기 중..."
    kubectl rollout status deployment/cloudflared -n "$NAMESPACE" --timeout=90s 2>/dev/null || true

    echo ""
    log_success "Cloudflare Tunnel 설정 완료!"
    echo ""
    echo "  서비스 접속 URL:"
    for svc in "${SERVICES[@]}"; do
        echo "    https://${svc}${DOMAIN_SUFFIX}"
    done
    echo ""
    log_warn "make secrets-encrypt 로 토큰을 암호화하세요"
    echo ""
}

show_status() {
    echo ""
    echo "=========================================="
    echo -e "${BLUE}  Cloudflare Tunnel 상태${NC}"
    echo "=========================================="

    # Pod 상태
    if kubectl get deployment cloudflared -n "$NAMESPACE" &>/dev/null; then
        POD_STATUS=$(kubectl get pods -n "$NAMESPACE" -l app=cloudflared -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "없음")
        echo -e "  Pod:    ${GREEN}${POD_STATUS}${NC}"
    else
        echo -e "  Pod:    ${RED}미배포${NC}"
    fi

    # Secret 상태
    if kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" &>/dev/null; then
        echo -e "  Secret: ${GREEN}등록됨${NC}"
    else
        echo -e "  Secret: ${RED}미등록${NC}  →  make tunnel"
    fi

    # SOPS 상태
    if [ -f "$SECRETS_PLAIN" ]; then
        local TOKEN
        TOKEN=$(get_secret cloudflare_tunnel_token)
        if [ -n "$TOKEN" ]; then
            echo -e "  Token:  ${GREEN}저장됨${NC}"
        else
            echo -e "  Token:  ${YELLOW}미설정${NC}"
        fi
    fi

    # Cloudflare API 상태 (토큰이 있으면)
    local CF_TOKEN
    CF_TOKEN=$(get_secret cloudflare_api_token)
    if [ -n "$CF_TOKEN" ]; then
        CF_API_TOKEN="$CF_TOKEN"
        local ACCOUNT_RESP ACCOUNT_ID
        ACCOUNT_RESP=$(cf_api GET "/accounts?page=1&per_page=1" 2>/dev/null)
        ACCOUNT_ID=$(echo "$ACCOUNT_RESP" | json_value "d['result'][0]['id']" 2>/dev/null)
        if [ -n "$ACCOUNT_ID" ] && [ "$ACCOUNT_ID" != "None" ]; then
            local TUNNELS_RESP TUNNEL_STATUS
            TUNNELS_RESP=$(cf_api GET "/accounts/${ACCOUNT_ID}/cfd_tunnel?name=${TUNNEL_NAME}&is_deleted=false" 2>/dev/null)
            TUNNEL_STATUS=$(echo "$TUNNELS_RESP" | json_value "d['result'][0]['status'] if d['result'] else 'not found'" 2>/dev/null)
            local TUNNEL_ID
            TUNNEL_ID=$(echo "$TUNNELS_RESP" | json_value "d['result'][0]['id'] if d['result'] else ''" 2>/dev/null)
            if [ -n "$TUNNEL_ID" ] && [ "$TUNNEL_ID" != "None" ] && [ "$TUNNEL_ID" != "" ]; then
                echo -e "  Tunnel: ${GREEN}${TUNNEL_STATUS}${NC} (${TUNNEL_ID})"
            else
                echo -e "  Tunnel: ${RED}미생성${NC}  →  make tunnel"
            fi
        fi
    fi

    echo ""
    echo "  서비스 URL:"
    for svc in "${SERVICES[@]}"; do
        echo "    https://${svc}${DOMAIN_SUFFIX}"
    done
    echo "=========================================="
    echo ""
}

teardown_tunnel() {
    log_info "Cloudflare Tunnel 제거 중..."

    # K8s 리소스 제거
    kubectl delete -f "$PROJECT_ROOT/manifests/cloudflare-tunnel/" --ignore-not-found
    kubectl delete secret "$SECRET_NAME" -n "$NAMESPACE" --ignore-not-found

    # Cloudflare API로 터널 삭제
    if [ -f "$SECRETS_PLAIN" ]; then
        local CF_TOKEN
        CF_TOKEN=$(get_secret cloudflare_api_token)
        if [ -n "$CF_TOKEN" ]; then
            CF_API_TOKEN="$CF_TOKEN"
            local ACCOUNT_RESP ACCOUNT_ID
            ACCOUNT_RESP=$(cf_api GET "/accounts?page=1&per_page=1" 2>/dev/null)
            ACCOUNT_ID=$(echo "$ACCOUNT_RESP" | json_value "d['result'][0]['id']" 2>/dev/null)
            if [ -n "$ACCOUNT_ID" ] && [ "$ACCOUNT_ID" != "None" ]; then
                local TUNNELS_RESP TUNNEL_ID
                TUNNELS_RESP=$(cf_api GET "/accounts/${ACCOUNT_ID}/cfd_tunnel?name=${TUNNEL_NAME}&is_deleted=false" 2>/dev/null)
                TUNNEL_ID=$(echo "$TUNNELS_RESP" | json_value "d['result'][0]['id'] if d['result'] else ''" 2>/dev/null)
                if [ -n "$TUNNEL_ID" ] && [ "$TUNNEL_ID" != "None" ] && [ "$TUNNEL_ID" != "" ]; then
                    log_info "Cloudflare 터널 삭제 중: $TUNNEL_ID"
                    # 터널 연결 해제 후 삭제
                    cf_api DELETE "/accounts/${ACCOUNT_ID}/cfd_tunnel/${TUNNEL_ID}" > /dev/null 2>&1 || true
                fi
            fi
        fi

        # secrets.yaml 에서 토큰 제거
        set_secret "cloudflare_tunnel_token" ""
    fi

    log_success "제거 완료"
}

usage() {
    echo "사용법: $0 [setup|status|teardown]"
    echo ""
    echo "  setup      Cloudflare API로 터널 자동 생성 + K8s 배포"
    echo "  status     터널 상태 확인"
    echo "  teardown   터널 제거 (Cloudflare + K8s)"
    echo ""
    echo "필요 조건: secrets/secrets.yaml 에 cloudflare_api_token 설정"
}

case "${1:-setup}" in
    setup)     setup_tunnel ;;
    status)    show_status ;;
    teardown)  teardown_tunnel ;;
    help|-h)   usage ;;
    *)         log_error "알 수 없는 옵션: $1"; usage; exit 1 ;;
esac
