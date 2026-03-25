#!/bin/bash
# ArgoCD 강제 sync 스크립트
# 사용법: ./scripts/argocd-sync.sh [app-name]
# app-name 생략 시 root (전체) sync

set -e

APP="${1:-root}"
ARGOCD_PORT=18090
ARGOCD_USER="${ARGOCD_USER:-admin}"
ARGOCD_PASS="${ARGOCD_PASS:-drkube}"

# 기존 포트포워드 정리
cleanup() {
    if [[ -n "$PF_PID" ]]; then
        kill "$PF_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ArgoCD 포트포워드 시작
kubectl port-forward svc/argocd-server -n argocd "${ARGOCD_PORT}:80" &>/dev/null &
PF_PID=$!
sleep 2

# 로그인 + sync
argocd login "127.0.0.1:${ARGOCD_PORT}" \
    --username "$ARGOCD_USER" \
    --password "$ARGOCD_PASS" \
    --insecure --plaintext &>/dev/null

echo "🔄 ArgoCD sync: $APP ..."
argocd app sync "$APP" \
    --server "127.0.0.1:${ARGOCD_PORT}" \
    --insecure --plaintext \
    --force 2>&1 | grep -E "(Synced|OutOfSync|Health|Error|created|configured|MESSAGE)" || true

# app이 root면 하위 앱들 health 대기
if [[ "$APP" == "root" ]]; then
    echo "⏳ delivery-app sync 대기..."
    argocd app wait delivery-app \
        --server "127.0.0.1:${ARGOCD_PORT}" \
        --insecure --plaintext \
        --health --sync --timeout 60 2>&1 | tail -3 || true
fi

echo "✅ 완료"
