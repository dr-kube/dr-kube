.PHONY: help agent-setup agent-run agent-clean setup teardown port-forward port-forward-stop port-forward-boutique boutique-open chaos-memory chaos-cpu chaos-pod-kill chaos-network chaos-stop chaos-status hosts hosts-remove hosts-status tls tls-status tunnel tunnel-status tunnel-teardown ssh-setup ssh-connect ssh-tunnel ssh-tunnel-stop secrets-init secrets-import secrets-encrypt secrets-decrypt secrets-apply secrets-status

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
	@grep -E '^(chaos-memory|chaos-cpu|chaos-pod-kill|chaos-network|chaos-stop|chaos-status).*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
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

agent-run: ## 에이전트 실행 (ISSUE=파일경로)
	@cd $(AGENT_DIR) && .venv/bin/python -m cli analyze $(ISSUE)

agent-fix: ## 이슈 분석 + PR 생성 (ISSUE=파일경로)
	@cd $(AGENT_DIR) && .venv/bin/python -m cli fix $(ISSUE)

agent-run-all: ## 모든 샘플 이슈 분석
	@cd $(AGENT_DIR) && for f in issues/*.json; do \
		echo "\n=== $$f ==="; \
		.venv/bin/python -m cli analyze $$f; \
	done

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

agent-webhook-check: ## 웹훅 URL 도달 여부 확인 (로컬 + 클러스터)
	@echo "1. 로컬 (이 기기에서 에이전트):"
	@curl -sf http://localhost:8080/health >/dev/null && echo "   OK - 에이전트 수신 가능" || echo "   실패 - make agent-webhook 실행 후 다시 시도"
	@echo ""
	@echo "2. 클러스터 → host.docker.internal:8080 (ArgoCD가 쓰는 주소):"
	@code=$$(kubectl run curl-webhook-check --rm -i --restart=Never --image=curlimages/curl -- curl -sf -o /dev/null -w "%{http_code}" http://host.docker.internal:8080/health 2>/dev/null | tr -d '\r\n'); \
	if [ "$$code" = "200" ]; then echo "   OK (HTTP $$code) - 클러스터에서 웹훅 도달 가능"; else echo "   실패 (HTTP $${code:-none}) - WSL 사용 시 values/argocd.yaml url을 WSL IP로 변경 (agent/README.md 참고)"; fi
	@echo ""

agent-clean: ## 에이전트 가상환경 삭제
	rm -rf $(AGENT_VENV)

agent-reinstall: agent-clean agent-setup ## 에이전트 재설치

# 샘플 이슈 단축 명령
agent-oom: ## OOM 이슈 분석
	@$(MAKE) agent-run ISSUE=issues/sample_oom.json

agent-oom-fix: ## OOM 이슈 분석 + PR 생성
	@$(MAKE) agent-fix ISSUE=issues/sample_oom.json

agent-cpu: ## CPU Throttle 이슈 분석
	@$(MAKE) agent-run ISSUE=issues/sample_cpu_throttle.json

agent-image: ## Image Pull 이슈 분석
	@$(MAKE) agent-run ISSUE=issues/sample_image_pull.json
# =============================================================================
# Chaos Mesh 실험 (Online Boutique)
# =============================================================================

chaos-memory: ## Frontend OOM 실험
	@echo "🔥 Frontend OOM 실험 시작..."
	@kubectl apply -f chaos/boutique-memory-stress.yaml
	@echo "✓ 3분 동안 실행 (OOMKilled 유발)"

chaos-cpu: ## CartService CPU 스트레스 실험
	@echo "🔥 CartService CPU 스트레스 실험 시작..."
	@kubectl apply -f chaos/boutique-cpu-stress.yaml
	@echo "✓ 3분 동안 실행"

chaos-pod-kill: ## CheckoutService Pod 강제 종료 실험
	@echo "🔥 CheckoutService Pod 강제 종료 실험 시작..."
	@kubectl apply -f chaos/boutique-pod-kill.yaml
	@echo "✓ 1분 동안 실행"

chaos-network: ## ProductCatalog 네트워크 지연 실험
	@echo "🔥 ProductCatalog 네트워크 지연 실험 시작..."
	@kubectl apply -f chaos/boutique-network-delay.yaml
	@echo "✓ 3분 동안 실행 (500ms 지연)"

chaos-stop: ## 모든 Chaos 실험 중지
	@echo "⏹️  모든 Chaos 실험 중지..."
	@kubectl delete -n chaos-mesh stresschaos,podchaos,networkchaos --all 2>/dev/null || true
	@echo "✓ 완료"

chaos-status: ## Chaos 실험 상태 확인
	@echo "📊 Chaos 실험 상태:"
	@kubectl get stresschaos,podchaos,networkchaos -n chaos-mesh -o wide || echo "실험 없음"
	@echo ""
	@echo "📊 영향받는 Pod 상태:"
	@kubectl get pods -n online-boutique -l "app in (frontend,cartservice,checkoutservice,productcatalogservice)" -o wide