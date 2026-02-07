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
    "boutique.drkube.local"
    "grafana.drkube.huik.site"
    "prometheus.drkube.huik.site"
    "alert.drkube.huik.site"
    "argocd.drkube.huik.site"
    "boutique.drkube.huik.site"
)

MARKER="# DR-Kube local domains"

# 플랫폼 감지 및 hosts 파일 경로 결정
detect_platform() {
    if grep -qi microsoft /proc/version 2>/dev/null; then
        PLATFORM="wsl"
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

# WSL: 임시 .ps1 파일을 만들어 관리자 권한으로 실행
wsl_run_elevated() {
    local PS_SCRIPT="$1"
    local TMPPS="/mnt/c/Users/$(/mnt/c/Windows/System32/cmd.exe /C 'echo %USERNAME%' 2>/dev/null | tr -d '\r')/drkube-hosts.ps1"

    echo "$PS_SCRIPT" > "$TMPPS"

    # WSL 경로 → Windows 경로 변환
    local WIN_SCRIPT
    WIN_SCRIPT=$(wslpath -w "$TMPPS")

    log_info "Windows 관리자 권한 요청 중 (UAC 팝업 허용하세요)..."
    powershell.exe -Command "Start-Process powershell -Verb RunAs -Wait -ArgumentList '-ExecutionPolicy Bypass -File \"$WIN_SCRIPT\"'" 2>/dev/null

    rm -f "$TMPPS"
}

add_hosts() {
    log_info "[$PLATFORM] $HOSTS_FILE 에 DR-Kube 도메인 추가 중..."

    if grep -q "$MARKER" "$HOSTS_FILE" 2>/dev/null; then
        log_warn "이미 등록되어 있습니다. 갱신하려면: $0 update"
        return 0
    fi

    ENTRY="127.0.0.1 ${DOMAINS[*]} $MARKER"

    if [[ "$PLATFORM" == "wsl" ]]; then
        wsl_run_elevated "Add-Content -Path 'C:\Windows\System32\drivers\etc\hosts' -Value '${ENTRY}' -Encoding ASCII"

        if grep -q "$MARKER" "$HOSTS_FILE" 2>/dev/null; then
            log_success "Windows hosts 파일 수정 완료"
        else
            log_error "등록 실패. 관리자 PowerShell에서 직접 실행하세요:"
            echo ""
            echo "  Add-Content 'C:\Windows\System32\drivers\etc\hosts' '${ENTRY}'"
            echo ""
            return 1
        fi
    else
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
        wsl_run_elevated '
$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$content = Get-Content $hostsPath | Where-Object { $_ -notmatch "DR-Kube local domains" }
Set-Content -Path $hostsPath -Value $content -Encoding ASCII
'
        if grep -q "$MARKER" "$HOSTS_FILE" 2>/dev/null; then
            log_error "제거 실패. 관리자 PowerShell에서 직접 제거하세요."
            return 1
        fi
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
    echo "  [*.drkube.local]"
    echo "  Grafana:      http://grafana.drkube.local        (admin / drkube)"
    echo "  Prometheus:   http://prometheus.drkube.local"
    echo "  Alertmanager: http://alert.drkube.local"
    echo "  ArgoCD:       http://argocd.drkube.local          (admin / drkube)"
    echo "  Boutique:     http://boutique.drkube.local"
    echo ""
    echo "  [*.drkube.huik.site]"
    echo "  Grafana:      http://grafana.drkube.huik.site    (admin / drkube)"
    echo "  Prometheus:   http://prometheus.drkube.huik.site"
    echo "  Alertmanager: http://alert.drkube.huik.site"
    echo "  ArgoCD:       http://argocd.drkube.huik.site      (admin / drkube)"
    echo "  Boutique:     http://boutique.drkube.huik.site"
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
