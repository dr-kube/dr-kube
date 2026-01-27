.PHONY: help agent-setup agent-run agent-clean

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
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Agent 명령어
# =============================================================================

agent-setup: ## 에이전트 환경 설정
	@./scripts/setup-agent.sh

agent-run: ## 에이전트 실행 (ISSUE=파일경로)
	@cd $(AGENT_DIR) && .venv/bin/python -m cli analyze $(ISSUE)

agent-run-all: ## 모든 샘플 이슈 분석
	@cd $(AGENT_DIR) && for f in issues/*.json; do \
		echo "\n=== $$f ==="; \
		.venv/bin/python -m cli analyze $$f; \
	done

agent-clean: ## 에이전트 가상환경 삭제
	rm -rf $(AGENT_VENV)

agent-reinstall: agent-clean agent-setup ## 에이전트 재설치

# 샘플 이슈 단축 명령
agent-oom: ## OOM 이슈 분석
	@$(MAKE) agent-run ISSUE=issues/sample_oom.json

agent-cpu: ## CPU Throttle 이슈 분석
	@$(MAKE) agent-run ISSUE=issues/sample_cpu_throttle.json

agent-image: ## Image Pull 이슈 분석
	@$(MAKE) agent-run ISSUE=issues/sample_image_pull.json
