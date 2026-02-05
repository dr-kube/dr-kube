.PHONY: help agent-setup agent-run agent-clean setup teardown port-forward port-forward-stop port-forward-boutique boutique-open chaos-memory chaos-cpu chaos-pod-kill chaos-network chaos-stop chaos-status

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
	@grep -E '^(setup|teardown|port-forward).*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  [Online Boutique]"
	@grep -E '^(port-forward-boutique|boutique-open).*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  [Chaos 실험]"
	@grep -E '^(chaos-memory|chaos-cpu|chaos-pod-kill|chaos-network|chaos-stop|chaos-status).*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
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