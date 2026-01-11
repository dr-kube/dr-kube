.PHONY: help build up down shell logs clean test analyze k8s-status argocd-status

# 기본 타겟 (help 출력)
help:
	@echo "DR-Kube 개발 환경 명령어"
	@echo ""
	@echo "사용 가능한 명령어:"
	@echo "  make build          - Docker 이미지 빌드"
	@echo "  make up             - 컨테이너 시작 (백그라운드)"
	@echo "  make down           - 컨테이너 중지 및 삭제"
	@echo "  make shell          - agent 컨테이너 셸 접속"
	@echo "  make logs           - 컨테이너 로그 확인"
	@echo "  make clean          - 볼륨 포함 전체 삭제"
	@echo "  make test           - pytest 실행"
	@echo "  make analyze        - 샘플 이슈 분석 (OOM 예제)"
	@echo "  make k8s-status     - K8s 클러스터 상태 확인"
	@echo "  make argocd-status  - ArgoCD 상태 확인"
	@echo "  make ollama-pull    - Ollama 모델 다운로드"

# Docker 이미지 빌드
build:
	docker-compose build

# 컨테이너 시작
up:
	docker-compose up -d
	@echo "컨테이너가 시작되었습니다."
	@echo "agent 컨테이너 접속: make shell"

# 컨테이너 중지
down:
	docker-compose down

# agent 컨테이너 셸 접속
shell:
	docker-compose exec agent bash

# 로그 확인
logs:
	docker-compose logs -f

# 전체 삭제 (볼륨 포함)
clean:
	docker-compose down -v
	@echo "모든 컨테이너와 볼륨이 삭제되었습니다."

# pytest 실행
test:
	docker-compose exec agent bash -c "cd agent && pytest"

# 샘플 이슈 분석 (OOM)
analyze:
	docker-compose exec agent bash -c "cd agent && python -m cli analyze issues/sample_oom.json"

# K8s 클러스터 상태 확인
k8s-status:
	docker-compose exec agent kubectl get pods -A

# ArgoCD 상태 확인
argocd-status:
	docker-compose exec agent argocd app list

# Ollama 모델 다운로드
ollama-pull:
	docker-compose exec ollama ollama pull qwen2.5:14b
	@echo "모델 다운로드 완료. .env 파일의 OLLAMA_MODEL과 일치하는지 확인하세요."
