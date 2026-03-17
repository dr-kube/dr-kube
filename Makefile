.PHONY: help agent-setup agent-webhook agent-clean setup teardown port-forward port-forward-stop port-forward-boutique boutique-open chaos-memory chaos-track-checkout-cascade chaos-track-catalog-break chaos-track-platform-brownout chaos-stop chaos-status hosts hosts-remove hosts-status tls tls-status tunnel tunnel-status tunnel-teardown ssh-setup ssh-connect ssh-tunnel ssh-tunnel-stop secrets-init secrets-import secrets-encrypt secrets-decrypt secrets-apply secrets-status services-build services-load services-deploy service-rebuild services-status

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
	@grep -E '^(setup|teardown|hosts|tls|tunnel|secrets|port-forward).*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  [Online Boutique]"
	@grep -E '^(port-forward-boutique|boutique-open).*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  [Chaos 실험]"
	@grep -E '^(chaos-memory|chaos-track-checkout-cascade|chaos-track-catalog-break|chaos-track-platform-brownout|chaos-stop|chaos-status).*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-32s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  [원격 접속]"
	@grep -E '^ssh-.*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  [에이전트]"
	@grep -E '^agent-.*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

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


agent-webhook: ## 웹훅 서버 시작 (Alertmanager 수신)
	@echo ""
	@echo "⚠️  경고: 이 서버는 LLM API를 호출하여 토큰 비용이 발생합니다!"
	@echo "⚠️  사용하지 않을 때는 반드시 Ctrl+C로 종료하세요!"
	@echo ""
	@cd $(AGENT_DIR) && .venv/bin/python -m dr_kube.webhook

agent-webhook-pr: ## 웹훅 서버 (자동 PR 생성 모드)
	@echo ""
	@echo "⚠️  경고: 이 서버는 LLM API를 호출하여 토큰 비용이 발생합니다!"
	@echo "⚠️  사용하지 않을 때는 반드시 Ctrl+C로 종료하세요!"
	@echo ""
	@cd $(AGENT_DIR) && AUTO_PR=true .venv/bin/python -m dr_kube.webhook

agent-webhook-check: ## 웹훅 URL 도달 여부 확인 (로컬 + 클러스터). WSL IP 테스트: make agent-webhook-check WEBHOOK_URL=http://172.25.69.176:8080
	@echo "1. 로컬 (이 기기에서 에이전트):"
	@curl -sf http://localhost:8080/health >/dev/null && echo "   OK - 에이전트 수신 가능" || echo "   실패 - make agent-webhook 실행 후 다시 시도"
	@echo ""
	@url=$${WEBHOOK_URL:-http://host.docker.internal:8080}; \
	echo "2. 클러스터 → $$url (ArgoCD가 쓰는 주소):"; \
	code=$$(kubectl run curl-webhook-check --rm -i --restart=Never --image=curlimages/curl -- curl -sf -o /dev/null -w "%{http_code}" "$$url/health" 2>/dev/null | head -1 | tr -d '\r\n' | grep -oE '[0-9]+' || true); \
	if [ "$$code" = "200" ]; then echo "   OK (HTTP $$code) - 클러스터에서 웹훅 도달 가능"; else echo "   실패 (HTTP $${code:-none}) - WSL 사용 시: make agent-webhook-check WEBHOOK_URL=http://<WSL_IP>:8080"; fi
	@echo ""

agent-clean: ## 에이전트 가상환경 삭제
	rm -rf $(AGENT_VENV)

agent-reinstall: agent-clean agent-setup ## 에이전트 재설치
# =============================================================================
# Chaos Mesh 실험 (Online Boutique)
# =============================================================================

chaos-memory: ## MSA 트래픽 급증 + 연쇄 OOM (loadgen→frontend→checkout→payment/redis/email/shipping, 10분)
	@echo "🔥 MSA 트래픽 급증 + 연쇄 OOM 시나리오 시작..."
	@kubectl apply -f chaos/track-memory-oom.yaml
	@echo "✓ 적용 완료 (권장 관측 10분)"
	@echo "  - loadgenerator: CPU 과부하 (트래픽 폭증)"
	@echo "  - frontend: OOMKill + CrashLoopBackOff (150M > 128Mi)"
	@echo "  - productcatalog: 1200ms 지연 (캐시 미스)"
	@echo "  - paymentservice: 2500ms 지연 (결제 API 타임아웃)"
	@echo "  - checkoutservice: 메모리+CPU 과부하"
	@echo "  - cartservice: 메모리 압박 (세션 폭증)"
	@echo "  - redis-cart: 30% 패킷 손실 (세션 소실)"
	@echo "  - emailservice: 40% 패킷 손실 (알림 실패)"
	@echo "  - shippingservice: 900ms 지연 (물류 API 지연)"

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
# DR-Kube 커스텀 서비스 (services/)
# =============================================================================
KIND_CLUSTER ?= dr-kube
SERVICES := inventory-service recommendation-proxy order-validator

services-build: ## 커스텀 서비스 Docker 이미지 빌드
	@for svc in $(SERVICES); do \
		echo "Building dr-kube/$$svc:latest ..."; \
		docker build -t dr-kube/$$svc:latest services/$$svc; \
	done
	@echo "Build complete"

services-load: ## Kind 클러스터에 이미지 로드
	@for svc in $(SERVICES); do \
		echo "Loading dr-kube/$$svc:latest → kind-$(KIND_CLUSTER)"; \
		kind load docker-image dr-kube/$$svc:latest --name $(KIND_CLUSTER); \
	done
	@echo "All images loaded"

services-deploy: services-build services-load ## 빌드 + Kind 로드 + ArgoCD 배포
	@kubectl apply -f applications/dr-kube-services.yaml
	@echo "ArgoCD Application 등록 완료. 동기화 대기 중..."
	@kubectl -n argocd wait --for=condition=available deployment/argocd-server --timeout=30s 2>/dev/null || true
	@argocd app sync dr-kube-services --grpc-web 2>/dev/null || echo "argocd CLI 없으면 UI에서 수동 Sync"

# 단일 서비스 재빌드 + 재배포. 사용: make service-rebuild SVC=inventory-service
service-rebuild: ## 단일 서비스 재빌드 + Kind 로드 + rollout restart (SVC=서비스명)
	@if [ -z "$(SVC)" ]; then echo "SVC=서비스명 필요. 예: make service-rebuild SVC=inventory-service"; exit 1; fi
	docker build -t dr-kube/$(SVC):latest services/$(SVC)
	kind load docker-image dr-kube/$(SVC):latest --name $(KIND_CLUSTER)
	kubectl rollout restart deployment/$(SVC) -n dr-kube-services
	kubectl rollout status deployment/$(SVC) -n dr-kube-services

services-status: ## 커스텀 서비스 Pod/Service 상태
	@kubectl get pods,svc -n dr-kube-services -o wide 2>/dev/null || echo "dr-kube-services 네임스페이스 없음 (make services-deploy 먼저 실행)"
