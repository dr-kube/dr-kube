# DR-Kube Agent Instructions

이 문서는 DR-Kube 저장소에서 작업하는 AI/자동화 에이전트를 위한 실행 지침입니다.

## 1) 프로젝트 목표
- Kubernetes 이슈 자동 감지 → 분석 → PR 생성 → GitOps 복구
- 목표 완료일: 2026-02-28

## 2) 절대 원칙 (GitOps)
- 클러스터 변경은 Git(PR)로만 수행
- 허용: `kubectl get`, `kubectl describe`, `kubectl logs`
- 금지: `kubectl apply`, `kubectl patch` 등 쓰기 명령
- 수정 대상은 기본적으로 `values/*.yaml`

## 3) 핵심 코드 경로
- `agent/dr_kube/graph.py`: LangGraph 워크플로우
- `agent/dr_kube/llm.py`: LLM 프로바이더
- `agent/dr_kube/prompts.py`: 프롬프트 템플릿
- `agent/dr_kube/state.py`: 상태 정의
- `agent/dr_kube/github.py`: GitHub PR 생성
- `agent/dr_kube/webhook.py`: Alertmanager 웹훅 서버
- `agent/dr_kube/converter.py`: Alert → Issue 변환

## 4) 현재/목표 워크플로우
- 현재: `load_issue -> analyze(LLM) -> generate_fix(LLM) -> create_pr`
- 목표(#1194): `load_issue -> analyze_and_fix(LLM 1회) -> validate -> create_pr`
- validate 실패 시 retry (최대 3회)

## 5) 완료 알림 정책
- 에이전트의 notify 노드는 제거 방향
- 완료 알림은 ArgoCD Notifications → Slack 이벤트 기반으로 처리

## 6) 작업 우선순위 (프로토타입)
1. `#1164` TASK-3: Converter 알림 타입 매핑 확장
2. `#1194` AGENT-1: 워크플로우 리팩토링(LLM 중복 제거 + validate 루프)
3. `#1172` MON-4: 서비스 레벨 알림 규칙 확장
4. `#1186` CHAOS: 복합 카오스 시나리오 확장
5. `#1175` MON-7: ArgoCD Notifications → Slack
6. `#1195` AGENT-2: PR 댓글 기반 재생성(HITL)
7. `#1196` MON-12: Grafana 대시보드 확장
8. `#1168` TASK-8: ArgoCD 이벤트 처리
9. `#1176` MON-8: ArgoCD Prometheus 메트릭
10. `#1167` TASK-6: E2E 통합 테스트

## 7) 개발 규칙
- Python 3.11+
- LangGraph 기반
- LLM: Gemini Flash 우선, Ollama 로컬 fallback
- 문서/주석은 한글 사용 가능
- 프롬프트/코드에서 kubectl 쓰기 명령 생성 금지

## 8) 로컬 운영 명령어
- 클러스터: `make setup`, `make teardown`, `make hosts`
- 시크릿: `make secrets-decrypt`, `make secrets-apply`
- 에이전트: `make agent-setup`, `make agent-run`, `make agent-fix`, `make agent-webhook`
- 카오스: `make chaos-memory`, `make chaos-stop`, `make help`

## 9) 환경 및 범위
- 로컬 K8S는 Kind 기반
- 지원 플랫폼: macOS, Windows+WSL2, Linux
- 프로토타입 범위: `load_issue -> analyze_and_fix -> validate -> create_pr`

## 10) 참고 문서
- `README.md`
- `docs/ROADMAP.md`
- `agent/README.md`
