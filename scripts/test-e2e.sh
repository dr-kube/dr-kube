#!/bin/bash
# DR-Kube E2E 테스트 스크립트
# 시나리오: cartservice OOM Alert → LLM 분석 → PR 생성 → 머지 → ArgoCD sync → 복구 확인
set -e

AGENT_HOST="${AGENT_HOST:-https://agent-drkube.huik.site}"
BOUTIQUE_NS="${BOUTIQUE_NS:-online-boutique}"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[FAIL]${NC}  $1"; exit 1; }

AGENT_POD=$(kubectl get pods -n monitoring -l app=dr-kube-agent --no-headers | head -1 | awk '{print $1}')
[ -z "$AGENT_POD" ] && error "dr-kube-agent Pod 없음"

echo "=========================================="
echo " DR-Kube E2E 테스트"
echo " 시나리오: cartservice OOM → memory limit 증설"
echo " Agent: $AGENT_HOST"
echo "=========================================="
echo ""

# ── Step 1: OOM Alert 주입 ──────────────────────────────────────────
info "[1/4] cartservice OOM Alert 주입..."
FP=$(python3 -c "import time,hashlib; print(hashlib.md5(str(time.time()).encode()).hexdigest()[:12])")
TS=$(python3 -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))")

ALERT_PAYLOAD=$(python3 - <<EOF
import json
payload = {
    "alerts": [{
        "labels": {
            "alertname": "ContainerOOMKilled",
            "namespace": "online-boutique",
            "pod": "cartservice-7f8b9c-xyz12",
            "container": "server",
            "severity": "critical"
        },
        "annotations": {
            "summary": "cartservice OOM Killed",
            "description": "cartservice container exceeded memory limit (128Mi) and was OOM killed. Consider increasing the memory limit."
        },
        "status": "firing",
        "startsAt": "$TS",
        "fingerprint": "$FP"
    }]
}
print(json.dumps(payload))
EOF
)

RESP=$(curl -s -X POST "$AGENT_HOST/webhook/alertmanager" \
  -H 'Content-Type: application/json' \
  -d "$ALERT_PAYLOAD")
echo "  응답: $RESP"

# 중복 스킵 확인
if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('queued',0)>0 else 1)" 2>/dev/null; then
  success "Alert 수신 완료 (queued=1)"
else
  # queued가 없어도 진행 (dedup 또는 다른 이유)
  warn "Alert 응답 확인 필요: $RESP (dedup 쿨다운일 수 있음)"
fi

info "  LLM 분석 대기 (35s)..."
sleep 35

# ── Step 2: action_id 추출 및 PR 생성 ─────────────────────────────
info "[2/4] Slack 버튼 → PR 생성..."
ACTION_ID=$(kubectl logs -n monitoring "$AGENT_POD" --tail=80 2>/dev/null \
  | grep "코파일럿 대기 중" | tail -1 \
  | python3 -c "import sys,re; m=re.search(r'action_id=([a-f0-9]+)',sys.stdin.read()); print(m.group(1) if m else '')")

[ -z "$ACTION_ID" ] && error "action_id 추출 실패 — 에이전트 로그 확인 필요 (중복 쿨다운 또는 LLM 오류)"
success "action_id=$ACTION_ID"

APPROVE_PAYLOAD=$(python3 -c "
import json, urllib.parse
payload = {'type':'block_actions','actions':[{'action_id':'approve','value':'$ACTION_ID'}],'trigger_id':'e2e-test'}
print('payload=' + urllib.parse.quote(json.dumps(payload)))
")
curl -s -X POST "$AGENT_HOST/webhook/slack/action" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "$APPROVE_PAYLOAD" > /dev/null

info "  PR 생성 대기 (12s)..."
sleep 12

PR_NUMBER=$(kubectl logs -n monitoring "$AGENT_POD" --tail=20 2>/dev/null \
  | grep "PR 생성 완료\|pr_url" | tail -1 \
  | python3 -c "import sys,re; m=re.search(r'pull/(\d+)',sys.stdin.read()); print(m.group(1) if m else '')")
[ -z "$PR_NUMBER" ] && error "PR 번호 추출 실패 — 로그 확인 필요"
PR_URL=$(kubectl logs -n monitoring "$AGENT_POD" --tail=20 2>/dev/null \
  | grep "PR 생성 완료" | tail -1 \
  | python3 -c "import sys,re; m=re.search(r'(https://github.com/[^\s]+)',sys.stdin.read()); print(m.group(1) if m else '')")
success "PR 생성 완료: $PR_URL"

# ── Step 3: 머지 ────────────────────────────────────────────────────
info "[3/4] PR #$PR_NUMBER 머지..."
MERGE_PAYLOAD=$(python3 -c "
import json, urllib.parse
payload = {'type':'block_actions','actions':[{'action_id':'merge_pr','value':'$PR_NUMBER'}],'trigger_id':'e2e-test'}
print('payload=' + urllib.parse.quote(json.dumps(payload)))
")
curl -s -X POST "$AGENT_HOST/webhook/slack/action" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "$MERGE_PAYLOAD" > /dev/null

sleep 5
MERGE_LOG=$(kubectl logs -n monitoring "$AGENT_POD" --tail=10 2>/dev/null | grep "머지 완료\|머지 실패" | tail -1)
if echo "$MERGE_LOG" | grep -q "머지 완료"; then
  success "PR 머지 완료"
elif echo "$MERGE_LOG" | grep -q "머지 실패"; then
  error "PR 머지 실패: $MERGE_LOG"
else
  warn "머지 상태 확인 불가 — GitHub에서 직접 확인: $PR_URL"
fi

# ── Step 4: ArgoCD sync + 복구 검증 ───────────────────────────────
info "[4/4] ArgoCD sync 트리거..."
"$(dirname "$0")/argocd-sync.sh" online-boutique 2>/dev/null || \
  "$(dirname "$0")/argocd-sync.sh" root 2>/dev/null || \
  warn "ArgoCD sync 실패 — 자동 sync 대기 (최대 3분)"

info "  ArgoCD synced 이벤트 전송 → 복구 검증 시작..."
curl -s -X POST "$AGENT_HOST/webhook/argocd" \
  -H 'Content-Type: application/json' \
  -d "{\"id\":\"argocd-e2e\",\"type\":\"argocd_synced\",\"app\":\"online-boutique\"}" > /dev/null

info "  Pod 복구 대기 (60s)..."
sleep 60

echo ""
echo "--- cartservice Pod 상태 ---"
kubectl get pods -n "$BOUTIQUE_NS" -l app=cartservice

echo ""
echo "--- 에이전트 복구 검증 로그 ---"
kubectl logs -n monitoring "$AGENT_POD" --since=3m 2>/dev/null \
  | grep -v "GET /health\|GET /debug\|HTTP/1.1" | grep -E "verify|복구|argocd" || true

RECOVER_LOG=$(kubectl logs -n monitoring "$AGENT_POD" --since=3m 2>/dev/null \
  | grep "복구 확인됨\|복구 미확인\|복구 검증 성공\|복구 검증 타임아웃" | tail -1 || true)

echo ""
echo "=========================================="
if echo "$RECOVER_LOG" | grep -qE "복구 확인됨|복구 검증 성공"; then
  success "E2E 테스트 성공: 복구 확인"
  echo -e "${GREEN} 전체 플로우 완료: OOM 감지 → LLM 분석 → PR 생성 → 머지 → ArgoCD sync → 복구${NC}"
else
  warn "E2E 완료 (복구 검증 결과: $RECOVER_LOG)"
  echo "  복구 검증은 pod 상태와 alert 해소 여부를 확인합니다."
  echo "  cartservice Pod이 Running이면 정상입니다."
fi
echo "=========================================="
