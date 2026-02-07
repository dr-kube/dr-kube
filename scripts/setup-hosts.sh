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

# DR-Kube 로컬 도메인 목록
DOMAINS=(
    "grafana.drkube.local"
    "prometheus.drkube.local"
    "alert.drkube.local"
    "argocd.drkube.local"
)

MARKER="# DR-Kube local domains"

# 플랫폼 감지 및 hosts 파일 경로 결정
detect_platform() {
    if grep -qi microsoft /proc/version 2>/dev/null; then
        PLATFORM="wsl"
        # WSL: 브라우저는 Windows에서 실행되므로 Windows hosts 파일 수정
        WIN_HOSTS="/mnt/c/Windows/System32/drivers/etc/hosts"
        HOSTS_FILE="$WIN_HOSTS"
        if [ ! -f "$HOSTS_FILE" ]; then
            log_error "Windows hosts 파일을 찾을 수 없습니다: $HOSTS_FILE"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        PLATFORM="macos"
        HOSTS_FILE="/etc/hosts"
    else
        PLATFORM="linux"
        HOSTS_FILE="/etc/hosts"
    fi
}

# 크로스 플랫폼 sed -i (macOS BSD sed vs GNU sed)
sed_inplace() {
    if [[ "$PLATFORM" == "macos" ]]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

add_hosts() {
    log_info "[$PLATFORM] $HOSTS_FILE 에 DR-Kube 도메인 추가 중..."

    # 이미 등록되어 있으면 스킵
    if grep -q "$MARKER" "$HOSTS_FILE" 2>/dev/null; then
        log_warn "이미 등록되어 있습니다. 갱신하려면: $0 update"
        return 0
    fi

    ENTRY="127.0.0.1 ${DOMAINS[*]} $MARKER"

    if [[ "$PLATFORM" == "wsl" ]]; then
        # WSL → Windows hosts: cmd.exe /C 로 관리자 권한 우회
        # tee -a 로 직접 쓰기 시도, 실패 시 안내
        if echo "$ENTRY" >> "$HOSTS_FILE" 2>/dev/null; then
            log_success "Windows hosts 파일 수정 완료"
        else
            log_error "권한 부족! 관리자 권한으로 PowerShell을 열고 아래 명령 실행:"
            echo ""
            echo "  Add-Content C:\\Windows\\System32\\drivers\\etc\\hosts '127.0.0.1 ${DOMAINS[*]} $MARKER'"
            echo ""
            return 1
        fi
    else
        # macOS / Linux
        if [ "$(id -u)" -ne 0 ]; then
            log_info "sudo 권한이 필요합니다."
            echo "$ENTRY" | sudo tee -a "$HOSTS_FILE" > /dev/null
        else
            echo "$ENTRY" >> "$HOSTS_FILE"
        fi
    fi

    log_success "등록 완료:"
    for d in "${DOMAINS[@]}"; do
        echo "  http://$d"
    done
}

remove_hosts() {
    log_info "[$PLATFORM] $HOSTS_FILE 에서 DR-Kube 도메인 제거 중..."

    if ! grep -q "$MARKER" "$HOSTS_FILE" 2>/dev/null; then
        log_warn "등록된 항목이 없습니다."
        return 0
    fi

    if [[ "$PLATFORM" == "wsl" ]]; then
        # WSL: grep -v 로 해당 줄 제외한 임시파일 생성 후 덮어쓰기
        TMPFILE=$(mktemp)
        grep -v "$MARKER" "$HOSTS_FILE" > "$TMPFILE" 2>/dev/null || true
        if cp "$TMPFILE" "$HOSTS_FILE" 2>/dev/null; then
            log_success "Windows hosts 파일에서 제거 완료"
        else
            log_error "권한 부족! 관리자 PowerShell에서 직접 제거하세요."
            return 1
        fi
        rm -f "$TMPFILE"
    elif [[ "$PLATFORM" == "macos" ]]; then
        if [ "$(id -u)" -ne 0 ]; then
            sudo sed -i '' "/$MARKER/d" "$HOSTS_FILE"
        else
            sed -i '' "/$MARKER/d" "$HOSTS_FILE"
        fi
    else
        if [ "$(id -u)" -ne 0 ]; then
            sudo sed -i "/$MARKER/d" "$HOSTS_FILE"
        else
            sed -i "/$MARKER/d" "$HOSTS_FILE"
        fi
    fi

    log_success "제거 완료"
}

update_hosts() {
    remove_hosts
    add_hosts
}

show_status() {
    echo ""
    echo "=========================================="
    echo -e "${BLUE}  DR-Kube 로컬 접속 주소${NC}"
    echo "=========================================="
    echo ""
    echo "  Grafana:      http://grafana.drkube.local      (admin / drkube)"
    echo "  Prometheus:   http://prometheus.drkube.local"
    echo "  Alertmanager: http://alert.drkube.local"
    echo "  ArgoCD:       http://argocd.drkube.local        (admin / drkube)"
    echo ""
    echo "=========================================="
    echo -e "  플랫폼:     ${YELLOW}$PLATFORM${NC}"
    echo -e "  hosts 파일: $HOSTS_FILE"

    if grep -q "$MARKER" "$HOSTS_FILE" 2>/dev/null; then
        echo -e "  등록 상태:  ${GREEN}등록됨${NC}"
    else
        echo -e "  등록 상태:  ${RED}미등록${NC}  →  $0 add"
    fi
    echo "=========================================="
    echo ""
}

usage() {
    echo "사용법: $0 [add|remove|update|status]"
    echo ""
    echo "  add      hosts 파일에 도메인 추가 (기본)"
    echo "  remove   hosts 파일에서 도메인 제거"
    echo "  update   도메인 갱신 (제거 후 추가)"
    echo "  status   접속 주소 및 등록 상태 확인"
    echo ""
    echo "지원 플랫폼: macOS, Linux, Windows (WSL2)"
}

# 플랫폼 감지 먼저 실행
detect_platform

case "${1:-add}" in
    add)       add_hosts; show_status ;;
    remove)    remove_hosts ;;
    update)    update_hosts; show_status ;;
    status)    show_status ;;
    help|-h)   usage ;;
    *)         log_error "알 수 없는 옵션: $1"; usage; exit 1 ;;
esac
