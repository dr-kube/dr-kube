#!/bin/bash
set -e

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
SECRETS_DIR="$PROJECT_ROOT/secrets"
SECRETS_PLAIN="$SECRETS_DIR/secrets.yaml"
SECRETS_ENC="$SECRETS_DIR/secrets.enc.yaml"
SOPS_CONFIG="$PROJECT_ROOT/.sops.yaml"
AGE_KEY_FILE="$SECRETS_DIR/age.key"

# age, sops 설치 확인
check_deps() {
    for cmd in age sops; do
        if ! command -v "$cmd" &>/dev/null; then
            log_info "$cmd 설치 중..."
            if command -v brew &>/dev/null; then
                brew install "$cmd"
            else
                log_error "$cmd 가 없습니다. brew install $cmd 또는 수동 설치하세요."
                exit 1
            fi
        fi
    done
}

# 키 생성 (최초 1회, 팀 리더가 실행)
init_key() {
    log_info "age 키페어 생성 중..."

    if [ -f "$AGE_KEY_FILE" ]; then
        log_warn "키가 이미 존재합니다: $AGE_KEY_FILE"
        read -p "새로 생성할까요? (y/N): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && return 0
    fi

    check_deps

    # 키 생성
    age-keygen -o "$AGE_KEY_FILE" 2>&1
    chmod 600 "$AGE_KEY_FILE"

    # 공개키 추출
    PUBLIC_KEY=$(grep "public key:" "$AGE_KEY_FILE" | awk '{print $NF}')

    # .sops.yaml 에 공개키 설정
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|age: .*|age: \"$PUBLIC_KEY\"|" "$SOPS_CONFIG"
    else
        sed -i "s|age: .*|age: \"$PUBLIC_KEY\"|" "$SOPS_CONFIG"
    fi

    echo ""
    echo "=========================================="
    echo -e "${GREEN}  키 생성 완료${NC}"
    echo "=========================================="
    echo ""
    echo "  키 파일:  $AGE_KEY_FILE"
    echo "  공개키:   $PUBLIC_KEY"
    echo ""
    echo -e "  ${YELLOW}팀원에게 키 파일을 공유하세요:${NC}"
    echo "  슬랙 DM으로 $AGE_KEY_FILE 전송"
    echo "  팀원은 받은 파일을 secrets/age.key 에 저장"
    echo ""
    echo "  다음 단계:"
    echo "  1. secrets/secrets.yaml 에 값 입력"
    echo "  2. make secrets-encrypt"
    echo "  3. git add secrets/secrets.enc.yaml .sops.yaml && git push"
    echo "=========================================="
}

# 팀원이 키 파일 받았을 때
import_key() {
    local KEY_PATH="$1"

    if [ -z "$KEY_PATH" ]; then
        log_error "키 파일 경로를 지정하세요: $0 import <path/to/age.key>"
        exit 1
    fi

    if [ ! -f "$KEY_PATH" ]; then
        log_error "파일을 찾을 수 없습니다: $KEY_PATH"
        exit 1
    fi

    cp "$KEY_PATH" "$AGE_KEY_FILE"
    chmod 600 "$AGE_KEY_FILE"
    log_success "키 가져오기 완료: $AGE_KEY_FILE"
}

# 암호화: secrets.yaml → secrets.enc.yaml
encrypt() {
    check_deps

    if [ ! -f "$AGE_KEY_FILE" ]; then
        log_error "키가 없습니다. make secrets-init 또는 make secrets-import 실행하세요."
        exit 1
    fi

    if [ ! -f "$SECRETS_PLAIN" ]; then
        log_error "평문 파일이 없습니다: $SECRETS_PLAIN"
        exit 1
    fi

    export SOPS_AGE_KEY_FILE="$AGE_KEY_FILE"
    sops --encrypt "$SECRETS_PLAIN" > "$SECRETS_ENC"

    log_success "암호화 완료: $SECRETS_ENC"
    log_info "이 파일은 Git에 커밋해도 안전합니다."
}

# 복호화: secrets.enc.yaml → secrets.yaml
decrypt() {
    check_deps

    if [ ! -f "$AGE_KEY_FILE" ]; then
        log_error "키가 없습니다. 팀 리더에게 age.key 파일을 받아 secrets/age.key 에 저장하세요."
        exit 1
    fi

    if [ ! -f "$SECRETS_ENC" ]; then
        log_error "암호화된 파일이 없습니다: $SECRETS_ENC"
        log_info "팀 리더가 make secrets-encrypt && git push 를 먼저 실행해야 합니다."
        exit 1
    fi

    export SOPS_AGE_KEY_FILE="$AGE_KEY_FILE"
    sops --decrypt "$SECRETS_ENC" > "$SECRETS_PLAIN"

    log_success "복호화 완료: $SECRETS_PLAIN"
}

# 값 읽기 헬퍼 (YAML에서 key: value 파싱)
get_value() {
    grep "^$1:" "$SECRETS_PLAIN" 2>/dev/null | sed "s/^$1: *//" | tr -d '"' | tr -d "'"
}

# K8s Secret 생성
apply() {
    if [ ! -f "$SECRETS_PLAIN" ]; then
        log_error "평문 파일이 없습니다. make secrets-decrypt 먼저 실행하세요."
        exit 1
    fi

    local SLACK_URL CLOUDFLARE_TOKEN GEMINI_KEY
    SLACK_URL=$(get_value slack_webhook_url)
    CLOUDFLARE_TOKEN=$(get_value cloudflare_api_token)
    GEMINI_KEY=$(get_value gemini_api_key)

    # Slack Webhook → monitoring 네임스페이스
    if [ -n "$SLACK_URL" ]; then
        kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null
        kubectl create secret generic alertmanager-slack \
            --namespace monitoring \
            --from-literal=webhook-url="$SLACK_URL" \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "Secret 생성: monitoring/alertmanager-slack"
    fi

    # Cloudflare Token → cert-manager 네임스페이스
    if [ -n "$CLOUDFLARE_TOKEN" ]; then
        kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null
        kubectl create secret generic cloudflare-api-token \
            --namespace cert-manager \
            --from-literal=api-token="$CLOUDFLARE_TOKEN" \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "Secret 생성: cert-manager/cloudflare-api-token"
    fi

    # Gemini API Key → agent .env 에 동기화
    if [ -n "$GEMINI_KEY" ]; then
        local AGENT_ENV="$PROJECT_ROOT/agent/.env"
        if [ -f "$AGENT_ENV" ]; then
            if grep -q "^GEMINI_API_KEY=" "$AGENT_ENV"; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$GEMINI_KEY|" "$AGENT_ENV"
                else
                    sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$GEMINI_KEY|" "$AGENT_ENV"
                fi
            else
                echo "GEMINI_API_KEY=$GEMINI_KEY" >> "$AGENT_ENV"
            fi
        fi
        log_success "agent/.env 에 GEMINI_API_KEY 동기화"
    fi

    echo ""
    log_success "시크릿 적용 완료"
}

show_status() {
    echo ""
    echo "=========================================="
    echo -e "${BLUE}  DR-Kube 시크릿 상태${NC}"
    echo "=========================================="

    # age 키
    if [ -f "$AGE_KEY_FILE" ]; then
        echo -e "  age 키:       ${GREEN}있음${NC}"
    else
        echo -e "  age 키:       ${RED}없음${NC} → make secrets-init (리더) 또는 make secrets-import (팀원)"
    fi

    # 암호화된 파일
    if [ -f "$SECRETS_ENC" ]; then
        echo -e "  암호화 파일:  ${GREEN}있음${NC} (Git 커밋 가능)"
    else
        echo -e "  암호화 파일:  ${RED}없음${NC} → make secrets-encrypt"
    fi

    # 평문 파일
    if [ -f "$SECRETS_PLAIN" ]; then
        echo -e "  평문 파일:    ${GREEN}있음${NC} (Git 커밋 금지)"

        local SLACK_URL CLOUDFLARE_TOKEN GEMINI_KEY
        SLACK_URL=$(get_value slack_webhook_url)
        CLOUDFLARE_TOKEN=$(get_value cloudflare_api_token)
        GEMINI_KEY=$(get_value gemini_api_key)

        echo ""
        [ -n "$SLACK_URL" ] && echo -e "  Slack:        ${GREEN}설정됨${NC}" || echo -e "  Slack:        ${YELLOW}미설정${NC}"
        [ -n "$CLOUDFLARE_TOKEN" ] && echo -e "  Cloudflare:   ${GREEN}설정됨${NC}" || echo -e "  Cloudflare:   ${YELLOW}미설정${NC}"
        [ -n "$GEMINI_KEY" ] && echo -e "  Gemini:       ${GREEN}설정됨${NC}" || echo -e "  Gemini:       ${YELLOW}미설정${NC}"
    else
        echo -e "  평문 파일:    ${RED}없음${NC} → make secrets-decrypt"
    fi

    echo "=========================================="
    echo ""
}

usage() {
    echo "사용법: $0 <command> [args]"
    echo ""
    echo "  init             age 키 생성 (팀 리더, 최초 1회)"
    echo "  import <file>    age 키 가져오기 (팀원)"
    echo "  encrypt          secrets.yaml 암호화 → Git 커밋 가능"
    echo "  decrypt          secrets.enc.yaml 복호화"
    echo "  apply            K8s Secret 생성 + agent/.env 동기화"
    echo "  status           현재 상태 확인"
    echo ""
    echo "  [팀 리더 플로우]"
    echo "  $0 init → 값 입력 → $0 encrypt → git push → 키 공유"
    echo ""
    echo "  [팀원 플로우]"
    echo "  키 받기 → $0 import <key> → git pull → $0 decrypt → $0 apply"
}

case "${1:-status}" in
    init)       init_key ;;
    import)     import_key "$2" ;;
    encrypt|enc) encrypt ;;
    decrypt|dec) decrypt ;;
    apply)      apply ;;
    status)     show_status ;;
    help|-h)    usage ;;
    *)          log_error "알 수 없는 명령: $1"; usage; exit 1 ;;
esac
