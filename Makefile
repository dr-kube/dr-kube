.PHONY: help agent-setup agent-run agent-clean agent-webhook agent-oom agent-cpu setup teardown port-forward port-forward-stop port-forward-boutique boutique-open chaos-track-checkout-cascade chaos-track-catalog-break chaos-track-platform-brownout chaos-stop chaos-status hosts hosts-remove hosts-status tls tls-status tunnel tunnel-status tunnel-teardown ssh-setup ssh-connect ssh-tunnel ssh-tunnel-stop secrets-init secrets-import secrets-encrypt secrets-decrypt secrets-apply secrets-status delivery-build delivery-load delivery-deploy delivery-status delivery-logs argocd-sync demo-break demo-break-partial demo-scale-zero demo-reset demo-status test-watcher test-watcher-reset test-approve test-merge test-recover test-e2e

# bash 사용 (source 명령 지원)
SHELL := /bin/bash

# 기본 타겟
.DEFAULT_GOAL := help

# 변수
AGENT_DIR := agent
AGENT_VENV := $(AGENT_DIR)/.venv
AGENT_PYTHON := $(AGENT_VENV)/bin/python
ISSUE ?= issues/sample_oom.json

help: ## 도움말 표시
	@echo "DR-Kube 명령어"
	@echo ""
	@echo "  [클러스터]"
	@grep -E '^(setup|teardown|hosts|tls|tunnel|secrets|port-forward|argocd).*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  [Online Boutique]"
	@grep -E '^(port-forward-boutique|boutique-open).*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  [Chaos 실험]"
	@grep -E '^(chaos-track-checkout-cascade|chaos-track-catalog-break|chaos-track-platform-brownout|chaos-stop|chaos-status).*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-32s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  [원격 접속]"
	@grep -E '^ssh-.*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  [에이전트]"
	@grep -E '^agent-.*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  [Delivery App (테스트 MSA)]"
	@grep -E '^delivery-.*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# 클러스터 명령어
# =============================================================================

setup: ## Kind 클러스터 + ArgoCD 설치
	@./scripts/setup.sh

teardown: ## 클러스터 삭제
	@./scripts/teardown.sh

hosts: ## /etc/hosts에 로컬 도메인 등록
	@./scripts/setup-hosts.sh add

hosts-remove: ## /etc/hosts에서 로컬 도메인 제거
	@./scripts/setup-hosts.sh remove

hosts-status: ## 로컬 접속 주소 확인
	@./scripts/setup-hosts.sh status

tls: ## Let's Encrypt TLS 설정 (Cloudflare 토큰 필요)
	@./scripts/setup-tls.sh setup

tls-status: ## TLS 인증서 상태 확인
	@./scripts/setup-tls.sh status

argocd-sync: ## ArgoCD 강제 sync (APP=delivery-app 으로 특정 앱만 가능)
	@./scripts/argocd-sync.sh $${APP:-root}

tunnel: ## Cloudflare Tunnel 설정 (API 자동)
	@./scripts/setup-tunnel.sh setup

tunnel-status: ## Cloudflare Tunnel 상태 확인
	@./scripts/setup-tunnel.sh status

tunnel-teardown: ## Cloudflare Tunnel 제거
	@./scripts/setup-tunnel.sh teardown

# =============================================================================
# 원격 SSH 접속 (Cloudflare Tunnel)
# =============================================================================

SSH_HOST ?= ssh-drkube.huik.site
SSH_USER ?= moltbot

ssh-setup: ## cloudflared 설치 (WSL/Linux)
	@echo "📦 cloudflared 설치 중..."
	@if command -v cloudflared >/dev/null 2>&1; then \
		echo "✓ cloudflared 이미 설치됨: $$(cloudflared --version)"; \
	else \
		curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared && \
		chmod +x /tmp/cloudflared && \
		sudo mv /tmp/cloudflared /usr/local/bin/ && \
		echo "✓ cloudflared 설치 완료"; \
	fi
	@echo ""
	@echo "📝 SSH config 설정 중..."
	@mkdir -p ~/.ssh
	@if grep -q "Host mac-k9s" ~/.ssh/config 2>/dev/null; then \
		echo "✓ SSH config 이미 설정됨"; \
	else \
		echo "" >> ~/.ssh/config && \
		echo "Host mac-k9s" >> ~/.ssh/config && \
		echo "  HostName $(SSH_HOST)" >> ~/.ssh/config && \
		echo "  User $(SSH_USER)" >> ~/.ssh/config && \
		echo '  ProxyCommand cloudflared access ssh --hostname %h' >> ~/.ssh/config && \
		echo "✓ SSH config 추가 완료"; \
	fi
	@echo ""
	@echo "🎉 설정 완료! 'make ssh-connect'로 접속하세요"

ssh-connect: ## Mac에 SSH 접속 (k9s 사용 가능)
	@echo "🔗 $(SSH_HOST)에 접속 중..."
	@ssh mac-k9s

ssh-tunnel: ## Mac에서 SSH 터널 시작 (호스트용)
	@echo "🚇 SSH 터널 시작..."
	@if pgrep -f "cloudflared.*mac-ssh" >/dev/null; then \
		echo "✓ 터널 이미 실행 중"; \
	else \
		nohup cloudflared tunnel --config ~/.cloudflared/config-mac-ssh.yml run mac-ssh > ~/.cloudflared/mac-ssh.log 2>&1 & \
		sleep 2 && \
		echo "✓ 터널 시작됨 (PID: $$(pgrep -f 'cloudflared.*mac-ssh'))"; \
	fi
	@echo "   접속 주소: $(SSH_HOST)"

ssh-tunnel-stop: ## SSH 터널 중지 (호스트용)
	@echo "⏹️  SSH 터널 중지..."
	@pkill -f "cloudflared.*mac-ssh" 2>/dev/null && echo "✓ 터널 중지됨" || echo "터널이 실행 중이 아님"

secrets-init: ## 시크릿 키 생성 (팀 리더, 최초 1회)
	@./scripts/setup-secrets.sh init

secrets-import: ## 시크릿 키 가져오기 (팀원, KEY=파일경로)
	@./scripts/setup-secrets.sh import $(KEY)

secrets-encrypt: ## 시크릿 암호화 (Git 커밋 가능)
	@./scripts/setup-secrets.sh encrypt

secrets-decrypt: ## 시크릿 복호화
	@./scripts/setup-secrets.sh decrypt

secrets-apply: ## K8s Secret 생성 + agent/.env 동기화
	@./scripts/setup-secrets.sh apply

secrets-status: ## 시크릿 상태 확인
	@./scripts/setup-secrets.sh status

port-forward: ## 포트포워딩 시작 (ArgoCD, Grafana)
	@./scripts/setup.sh port-forward

port-forward-stop: ## 포트포워딩 종료
	@./scripts/setup.sh port-stop

# =============================================================================
# Online Boutique 데모 앱
# =============================================================================

port-forward-boutique: ## Online Boutique 포트포워딩 (8081)
	@echo "📦 Online Boutique 포트포워딩 시작..."
	@echo "   Frontend: http://localhost:8081"
	@echo ""
	@echo "   Ctrl+C로 종료"
	@kubectl port-forward -n online-boutique svc/frontend 8081:80

boutique-open: ## Online Boutique 브라우저 열기
	@open http://localhost:8081 || echo "직접 http://localhost:8081 접속하세요"

# =============================================================================

agent-setup: ## 에이전트 환경 설정
	@./scripts/setup-agent.sh

agent-run: ## 에이전트 실행 (ISSUE=파일경로)
	@cd $(AGENT_DIR) && .venv/bin/python -m cli analyze $(ISSUE)

agent-webhook: ## 웹훅 서버 시작 (Alertmanager 수신 + K8s 리소스 감시)
	@echo ""
	@echo "⚠️  경고: 이 서버는 LLM API를 호출하여 토큰 비용이 발생합니다!"
	@echo "⚠️  사용하지 않을 때는 반드시 Ctrl+C로 종료하세요!"
	@echo ""
	@echo "📡 K8s 워처 감시 대상: $${WATCH_NAMESPACES:-online-boutique}"
	@echo "   변경 감지 시 Slack [♻️ 복구] 버튼 전송"
	@echo ""
	@cd $(AGENT_DIR) && .venv/bin/python -m dr_kube.webhook

agent-clean: ## 에이전트 가상환경 삭제
	rm -rf $(AGENT_VENV)

# 샘플 이슈 단축 명령
agent-oom: ## OOM 이슈 분석
	@$(MAKE) agent-run ISSUE=issues/sample_oom.json

agent-cpu: ## CPU Throttle 이슈 분석
	@$(MAKE) agent-run ISSUE=issues/sample_cpu_throttle.json
# =============================================================================
# Chaos Mesh 실험 (Online Boutique)
# =============================================================================

chaos-track-checkout-cascade: ## checkout 경로 복합 장애 (redis/payment/checkout)
	@echo "🔥 복합 트랙: checkout-cascade 시작..."
	@kubectl apply -f chaos/track-checkout-cascade.yaml
	@echo "✓ 적용 완료 (권장 관측 6분)"

chaos-track-catalog-break: ## catalog 장애 + frontend/cart 과부하 복합 실험
	@echo "🔥 복합 트랙: catalog-break 시작..."
	@kubectl apply -f chaos/track-catalog-break.yaml
	@echo "✓ 적용 완료 (권장 관측 5분)"

chaos-track-platform-brownout: ## 플랫폼 전반 성능 저하 복합 실험
	@echo "🔥 복합 트랙: platform-brownout 시작..."
	@kubectl apply -f chaos/track-platform-brownout.yaml
	@echo "✓ 적용 완료 (권장 관측 7분)"

chaos-stop: ## 모든 Chaos 실험 중지
	@echo "⏹️  모든 Chaos 실험 중지..."
	@kubectl delete -n chaos-mesh stresschaos,podchaos,networkchaos,dnschaos,schedules --all 2>/dev/null || true
	@echo "✓ 완료"

chaos-status: ## Chaos 실험 상태 확인
	@echo "📊 Chaos 실험 상태:"
	@kubectl get stresschaos,podchaos,networkchaos,dnschaos,schedules -n chaos-mesh -o wide || echo "실험 없음"
	@echo ""
	@echo "📊 영향받는 Pod 상태:"
	@kubectl get pods -n online-boutique -l "app in (frontend,cartservice,checkoutservice,productcatalogservice,paymentservice,redis-cart)" -o wide

# =============================================================================
# Delivery App (테스트용 MSA 배달 앱)
# =============================================================================

KIND_CLUSTER ?= dr-kube
DELIVERY_APP_DIR := delivery-app

delivery-build: ## 배달 앱 Docker 이미지 빌드 (3개 서비스)
	@echo "🔨 Delivery App 이미지 빌드 중..."
	@docker build -t delivery-app/menu-service:local $(DELIVERY_APP_DIR)/menu-service
	@docker build -t delivery-app/order-service:local $(DELIVERY_APP_DIR)/order-service
	@docker build -t delivery-app/delivery-service:local $(DELIVERY_APP_DIR)/delivery-service
	@echo "✓ 빌드 완료"

delivery-load: ## Kind 클러스터에 이미지 로드
	@echo "📦 Kind 클러스터에 이미지 로드 중..."
	@kind load docker-image delivery-app/menu-service:local --name $(KIND_CLUSTER)
	@kind load docker-image delivery-app/order-service:local --name $(KIND_CLUSTER)
	@kind load docker-image delivery-app/delivery-service:local --name $(KIND_CLUSTER)
	@echo "✓ 이미지 로드 완료"

delivery-deploy: delivery-build delivery-load ## 빌드 + 로드 + K8s 배포 (ArgoCD 없이 직접)
	@echo "🚀 Delivery App 배포 중..."
	@kubectl apply -k manifests/delivery-app/
	@echo "⏳ Pod 시작 대기 중..."
	@kubectl rollout status deployment/menu-service -n delivery-app --timeout=60s
	@kubectl rollout status deployment/order-service -n delivery-app --timeout=60s
	@kubectl rollout status deployment/delivery-service -n delivery-app --timeout=60s
	@echo "✓ 배포 완료"
	@$(MAKE) delivery-status

delivery-status: ## Delivery App Pod 상태 확인
	@echo "📊 Delivery App 상태:"
	@kubectl get pods,svc,ingress -n delivery-app -o wide

delivery-logs: ## Delivery App 로그 확인 (SERVICE=order-service|menu-service|delivery-service)
	@SERVICE=$${SERVICE:-order-service}; \
	echo "📋 $$SERVICE 로그:"; \
	kubectl logs -n delivery-app -l app=$$SERVICE --tail=50 -f

# ============================================================
# Demo 시나리오
# ============================================================

demo-break: ## [데모] menu-service 에러 100% 주입 → order-service 연쇄 장애
	@echo "💥 menu-service 에러율 100% 주입 중..."
	@kubectl run demo-inject --rm -i --restart=Never --image=curlimages/curl --namespace=delivery-app \
		-- curl -sf -X POST "http://menu-service:8001/simulate/error?rate=1.0"
	@echo ""
	@echo "⚠️  연쇄 장애 시작 — 30초 후 Alertmanager → 에이전트 자동 처리"
	@echo "📊 Grafana: https://grafana-drkube.huik.site"
	@echo "🔔 Slack 채널에서 에이전트 알림 확인"

demo-break-partial: ## [데모] menu-service 에러 50% 주입 (간헐적 장애)
	@echo "💥 menu-service 에러율 50% 주입 중..."
	@kubectl run demo-inject --rm -i --restart=Never --image=curlimages/curl --namespace=delivery-app \
		-- curl -sf -X POST "http://menu-service:8001/simulate/error?rate=0.5"
	@echo ""
	@echo "⚠️  간헐적 장애 시작"

demo-scale-zero: ## [데모] order-service replicas=0 → watcher 즉시 감지
	@echo "💥 order-service replicas → 0..."
	@kubectl scale deployment/order-service -n delivery-app --replicas=0
	@echo "🔍 watcher가 즉시 감지 → 에이전트 자동 PR 생성"

demo-reset: ## [데모] delivery-app 전체 정상화
	@echo "✅ delivery-app 초기화 중..."
	@kubectl run demo-reset --rm -i --restart=Never --image=curlimages/curl --namespace=delivery-app \
		-- curl -sf -X POST "http://menu-service:8001/simulate/reset"
	@echo ""
	@kubectl scale deployment/order-service -n delivery-app --replicas=1 2>/dev/null || true
	@echo "✅ 정상화 완료"

demo-status: ## [데모] 현재 장애 상태 확인
	@echo "📊 delivery-app Pod 상태:"
	@kubectl get pods -n delivery-app
	@echo ""
	@echo "📈 최근 에러 로그 (order-service):"
	@kubectl logs -n delivery-app -l app=order-service --tail=10 2>/dev/null || true

# ── watcher e2e 테스트 ─────────────────────────────────────────────────────────

AGENT_HOST ?= https://agent-drkube.huik.site
BOUTIQUE_NS ?= online-boutique
TEST_DEPLOY ?= frontend

test-watcher: ## [테스트] frontend scale=0 → watcher 감지 → Slack 버튼 전송까지 확인
	@echo "=== watcher e2e 테스트 시작 ==="
	@echo "1. frontend 정상화 (replicas=1)..."
	@kubectl scale deployment/$(TEST_DEPLOY) -n $(BOUTIQUE_NS) --replicas=1
	@echo "   Pod 준비 대기 (15s)..."
	@sleep 15
	@echo "2. frontend 강제 다운 (replicas=0) — watcher 감지 트리거..."
	@kubectl scale deployment/$(TEST_DEPLOY) -n $(BOUTIQUE_NS) --replicas=0
	@echo "   LLM 분석 대기 (30s)..."
	@sleep 30
	@echo "3. 에이전트 로그 확인..."
	@POD=$$(kubectl get pods -n monitoring -l app=dr-kube-agent --no-headers | head -1 | awk '{print $$1}'); \
	  kubectl logs -n monitoring $$POD --tail=20 | grep -v "GET /health\|GET /debug\|HTTP/1.1"
	@echo ""
	@echo "=== Slack 채널에서 [PR 생성] 버튼 확인 후 make test-approve ACTION_ID=<id> 실행 ==="
	@echo "=== 또는 로그에서 action_id 확인 후 make test-approve ACTION_ID=<id> ==="

test-approve: ## [테스트] approve 버튼 클릭 시뮬레이션 (ACTION_ID 필수)
	@if [ -z "$(ACTION_ID)" ]; then \
	  echo "사용법: make test-approve ACTION_ID=<action_id>"; \
	  echo "action_id는 에이전트 로그의 '코파일럿 대기 중: action_id=...' 에서 확인"; \
	  exit 1; \
	fi
	@echo "=== approve 시뮬레이션: action_id=$(ACTION_ID) ==="
	@PAYLOAD=$$(python3 -c "import json,urllib.parse; print('payload='+urllib.parse.quote(json.dumps({'type':'block_actions','actions':[{'action_id':'approve','value':'$(ACTION_ID)'}],'trigger_id':'test'})))"); \
	  curl -s -X POST $(AGENT_HOST)/webhook/slack/action \
	    -H 'Content-Type: application/x-www-form-urlencoded' \
	    -d "$$PAYLOAD"
	@echo ""
	@echo "PR 생성 결과 확인 중 (10s)..."
	@sleep 10
	@POD=$$(kubectl get pods -n monitoring -l app=dr-kube-agent --no-headers | head -1 | awk '{print $$1}'); \
	  kubectl logs -n monitoring $$POD --tail=10 | grep -v "GET /health\|GET /debug\|HTTP/1.1"

test-merge: ## [테스트] 머지 버튼 클릭 시뮬레이션 (PR_NUMBER 필수)
	@if [ -z "$(PR_NUMBER)" ]; then \
	  echo "사용법: make test-merge PR_NUMBER=<pr_number>"; \
	  echo "PR 번호는 test-approve 실행 후 로그의 'pr_url=.../pull/<number>' 에서 확인"; \
	  exit 1; \
	fi
	@echo "=== 머지 시뮬레이션: pr_number=$(PR_NUMBER) ==="
	@PAYLOAD=$$(python3 -c "import json,urllib.parse; print('payload='+urllib.parse.quote(json.dumps({'type':'block_actions','actions':[{'action_id':'merge_pr','value':'$(PR_NUMBER)'}],'trigger_id':'test'})))"); \
	  curl -s -X POST $(AGENT_HOST)/webhook/slack/action \
	    -H 'Content-Type: application/x-www-form-urlencoded' \
	    -d "$$PAYLOAD"
	@echo ""
	@echo "머지 결과 확인 중 (5s)..."
	@sleep 5
	@POD=$$(kubectl get pods -n monitoring -l app=dr-kube-agent --no-headers | head -1 | awk '{print $$1}'); \
	  kubectl logs -n monitoring $$POD --tail=10 | grep -v "GET /health\|GET /debug\|HTTP/1.1"
	@echo ""
	@echo "=== 다음: ArgoCD sync 대기 후 make test-recover 실행 (또는 자동 완료) ==="

test-recover: ## [테스트] ArgoCD sync 트리거 + 복구 검증 webhook 시뮬레이션
	@echo "=== ArgoCD sync 트리거 ==="
	@./scripts/argocd-sync.sh online-boutique 2>/dev/null || ./scripts/argocd-sync.sh root
	@echo ""
	@echo "=== ArgoCD synced 이벤트 시뮬레이션 → 에이전트 복구 검증 ==="
	@curl -s -X POST $(AGENT_HOST)/webhook/argocd \
	  -H 'Content-Type: application/json' \
	  -d '{"id":"argocd-test","type":"argocd_synced","app":"online-boutique"}'
	@echo ""
	@echo "복구 검증 대기 중 (60s) — Pod 상태 확인..."
	@sleep 60
	@echo "--- frontend Pod 상태 ---"
	@kubectl get pods -n $(BOUTIQUE_NS) -l app=$(TEST_DEPLOY)
	@echo ""
	@echo "--- 에이전트 복구 검증 로그 ---"
	@POD=$$(kubectl get pods -n monitoring -l app=dr-kube-agent --no-headers | head -1 | awk '{print $$1}'); \
	  kubectl logs -n monitoring $$POD --tail=20 | grep -v "GET /health\|GET /debug\|HTTP/1.1"

test-e2e: ## [테스트] 전체 e2e 자동화 (OOM Alert → PR 생성 → 머지 → ArgoCD sync → 복구 확인)
	@AGENT_HOST=$(AGENT_HOST) BOUTIQUE_NS=$(BOUTIQUE_NS) ./scripts/test-e2e.sh

test-watcher-reset: ## [테스트] frontend 정상화
	@kubectl scale deployment/$(TEST_DEPLOY) -n $(BOUTIQUE_NS) --replicas=1
	@echo "frontend replicas=1 복구 완료"
