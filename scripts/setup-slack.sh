#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

NAMESPACE="monitoring"
SECRET_NAME="alertmanager-slack-webhook"

# Webhook URL 입력
if [ -z "$SLACK_WEBHOOK_URL" ]; then
    echo -n "Slack Webhook URL: "
    read -r SLACK_WEBHOOK_URL
fi

if [ -z "$SLACK_WEBHOOK_URL" ]; then
    log_error "URL이 비어있습니다."
    exit 1
fi

# 기존 Secret 삭제 후 재생성
log_info "Secret '$SECRET_NAME' 생성 중..."
kubectl delete secret "$SECRET_NAME" -n "$NAMESPACE" 2>/dev/null || true
kubectl create secret generic "$SECRET_NAME" \
    --from-literal=url="$SLACK_WEBHOOK_URL" \
    -n "$NAMESPACE"

log_success "Secret 생성 완료"
log_info "Alertmanager가 자동으로 재시작됩니다."
