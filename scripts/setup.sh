#!/bin/bash
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CLUSTER_NAME="dr-kube"

# 함수: 로그 출력
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# 함수: 명령어 존재 확인
check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

# 함수: 의존성 설치
install_dependencies() {
    log_info "의존성 확인 중..."

    # Docker 확인
    if ! check_command docker; then
        log_error "Docker가 설치되어 있지 않습니다."
        log_info "https://docs.docker.com/get-docker/ 에서 설치하세요."
        exit 1
    fi
    
    # Docker 실행 확인
    if ! docker info &> /dev/null; then
        log_error "Docker가 실행 중이 아닙니다. Docker를 시작하세요."
        exit 1
    fi
    log_success "Docker 확인됨"

    # Homebrew (macOS/Linux)
    if ! check_command brew; then
        log_info "Homebrew 설치 중..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        if [[ "$OSTYPE" == "darwin"* ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || eval "$(/usr/local/bin/brew shellenv)"
        else
            eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
        fi
    fi
    log_success "Homebrew 확인됨"

    # Kind
    if ! check_command kind; then
        log_info "Kind 설치 중..."
        brew install kind
    fi
    log_success "Kind 확인됨"

    # kubectl
    if ! check_command kubectl; then
        log_info "kubectl 설치 중..."
        brew install kubectl
    fi
    log_success "kubectl 확인됨"

    # Helm
    if ! check_command helm; then
        log_info "Helm 설치 중..."
        brew install helm
    fi
    log_success "Helm 확인됨"
}

# 함수: Kind 클러스터 생성
create_cluster() {
    log_info "Kind 클러스터 생성 중..."

    # 이미 존재하는지 확인
    if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        log_warn "클러스터 '${CLUSTER_NAME}'가 이미 존재합니다."
        read -p "삭제하고 다시 생성할까요? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kind delete cluster --name "$CLUSTER_NAME"
        else
            log_info "기존 클러스터 사용"
            return 0
        fi
    fi

    # Kind 설정 파일 생성
    cat > /tmp/kind-config.yaml <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: ${CLUSTER_NAME}
nodes:
  - role: control-plane
    extraPortMappings:
      # Ingress HTTP
      - containerPort: 80
        hostPort: 80
        protocol: TCP
      # Ingress HTTPS  
      - containerPort: 443
        hostPort: 443
        protocol: TCP
      # ArgoCD (NodePort)
      - containerPort: 30080
        hostPort: 30080
        protocol: TCP
      # Grafana (NodePort)
      - containerPort: 30081
        hostPort: 30081
        protocol: TCP
  - role: worker
  - role: worker
EOF

    kind create cluster --config /tmp/kind-config.yaml
    rm /tmp/kind-config.yaml
    
    log_success "Kind 클러스터 생성 완료"
}

# 함수: ArgoCD 설치
install_argocd() {
    log_info "ArgoCD 설치 중..."

    # 네임스페이스 생성
    kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

    # Helm repo 추가
    helm repo add argo https://argoproj.github.io/argo-helm
    helm repo update

    # ArgoCD 설치 (values 파일 사용)
    helm upgrade --install argocd argo/argo-cd \
        --namespace argocd \
        --values "$PROJECT_ROOT/values/argocd.yaml" \
        --wait --timeout 5m

    log_success "ArgoCD 설치 완료"
}

# 함수: ArgoCD 초기 비밀번호 출력
get_argocd_password() {
    log_info "ArgoCD 접속 정보 확인 중..."
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}ArgoCD 접속 정보${NC}"
    echo "=========================================="
    echo "URL: https://localhost:30080"
    echo "Username: admin"
    echo "Password: drkube"
    echo "=========================================="
    echo ""
    log_info "비밀번호는 values/argocd.yaml에서 변경 가능합니다."
}

# 함수: Root Application 배포
deploy_root_app() {
    log_info "Root Application 배포 중..."

    # ArgoCD가 준비될 때까지 대기
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd

    # Root Application 배포
    kubectl apply -f "$PROJECT_ROOT/manifests/application-root.yaml"

    log_success "Root Application 배포 완료"
    log_info "ArgoCD에서 앱들이 자동으로 동기화됩니다."
}

# 함수: 포트포워딩 시작
start_port_forward() {
    log_info "포트포워딩 시작 중..."

    # 기존 포트포워딩 프로세스 종료
    pkill -f "kubectl port-forward.*argocd-server" 2>/dev/null || true
    pkill -f "kubectl port-forward.*grafana" 2>/dev/null || true

    # ArgoCD 포트포워딩 (백그라운드)
    kubectl port-forward svc/argocd-server -n argocd 8080:80 &>/dev/null &
    log_success "ArgoCD: http://localhost:8080"

    # Grafana 포트포워딩 (백그라운드) - grafana가 배포된 경우
    if kubectl get svc grafana -n monitoring &>/dev/null; then
        kubectl port-forward svc/grafana -n monitoring 3000:80 &>/dev/null &
        log_success "Grafana: http://localhost:3000"
    fi

    echo ""
    log_info "포트포워딩이 백그라운드에서 실행 중입니다."
    log_info "종료하려면: make port-forward-stop"
}

# 함수: 포트포워딩 종료
stop_port_forward() {
    log_info "포트포워딩 종료 중..."
    pkill -f "kubectl port-forward.*argocd-server" 2>/dev/null || true
    pkill -f "kubectl port-forward.*grafana" 2>/dev/null || true
    log_success "포트포워딩 종료 완료"
}

# 함수: 전체 설치
install_all() {
    echo ""
    echo "=========================================="
    echo -e "${BLUE}  DR-Kube 로컬 환경 설정${NC}"
    echo "=========================================="
    echo ""

    install_dependencies
    create_cluster
    install_argocd
    get_argocd_password
    deploy_root_app

    echo ""
    echo "=========================================="
    echo -e "${GREEN}  설정 완료!${NC}"
    echo "=========================================="
    echo ""
    echo "다음 단계:"
    echo "  1. ArgoCD 접속: https://localhost:30080"
    echo "  2. 앱 동기화 확인 (자동)"
    echo "  3. make agent-run 으로 에이전트 실행"
    echo ""
    echo "삭제하려면: ./scripts/teardown.sh"
    echo ""
}

# 함수: 사용법 출력
usage() {
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  (없음)       전체 설치 (cluster + argocd + apps)"
    echo "  cluster      Kind 클러스터만 생성"
    echo "  argocd       ArgoCD만 설치"
    echo "  apps         Root Application만 배포"
    echo "  port-forward 포트포워딩 시작"
    echo "  port-stop    포트포워딩 종료"
    echo "  help         이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0              # 전체 설치"
    echo "  $0 cluster      # 클러스터만 생성"
    echo "  $0 port-forward # 포트포워딩 시작"
}

# 메인 로직
case "${1:-all}" in
    cluster)
        install_dependencies
        create_cluster
        ;;
    argocd)
        install_argocd
        get_argocd_password
        ;;
    apps)
        deploy_root_app
        ;;
    port-forward|pf)
        start_port_forward
        ;;
    port-stop|ps)
        stop_port_forward
        ;;
    all)
        install_all
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        log_error "알 수 없는 옵션: $1"
        usage
        exit 1
        ;;
esac
