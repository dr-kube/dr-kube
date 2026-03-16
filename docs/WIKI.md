## 📑 [Dr.Kube] Official Wiki
> **KR:** 이 페이지는 **Dr.Kube**의 비전, 기술적 방향성, 그리고 협업 방식을 정의하는 통합 문서입니다. 팀원과 외부 기여자들이 조화롭게 협업할 수 있도록 돕는 공식 가이드라인입니다.
>
> **EN:** This page serves as the comprehensive documentation defining the vision, technical direction, and collaboration methods for **Dr.Kube**. It is an official guideline to ensure seamless collaboration between the team and external contributors.

### 1. 프로젝트 개요 (Project Overview)
* **Purpose:** 클러스터의 '다잉 메시지'을 분석해 스스로 장애를 진단하고 해결 가이드까지 제공하는 지능형 AI 에이전트 ; An autonomous AI agent that analyzes 'dying messages' from failing clusters to diagnose root causes and deliver actionable remediation guidelines.
* **Background / Introduction (KR):**
  * Kubernetes의 고질적인 문제인 장애 발생 시 MTTR(평균 복구 시간)을 단축하는 것을 목표로 합니다.
  * LangGraph 기반 추론 루프를 통해 근본 원인을 탐색하고, Slack 등 메신저로 운영자에게 즉각적인 조치 가이드라인을 제공합니다.
  * 운영자의 승인 하에 명령을 수행하여 안전성을 확보하는 Safe AI Ops 생태계를 만듭니다.

* **Background / Introduction (EN):**
  * Our objective is to minimize **Mean Time to Recovery (MTTR)**, a persistent challenge in Kubernetes environments during system failures. By leveraging **LangGraph-based reasoning loops**, the system identifies root causes and delivers immediate remediation guidelines to operators via messaging platforms like **Slack**. We are building a **'Safe AIOps' ecosystem** that ensures operational integrity by executing commands only upon explicit human-in-the-loop approval.
* **Core Values:**
  * Safe AIOps (안전한 AI 운영) — Human-in-the-Loop 승인 기반의 안전한 자동 복구 / Safe automated recovery based on human-in-the-loop approval
  * GitOps First (GitOps 우선) — 모든 변경은 Git을 통해서만, 클러스터 직접 수정 금지 / All changes through Git only, no direct cluster modifications
  * Observability (관측 가능성) — 4가지 시그널(Metrics, Logs, Traces, Profiles) 기반 근본 원인 분석 / Root cause analysis based on 4 signals (Metrics, Logs, Traces, Profiles)

### 2. 팀 구성 (The Team)

Roles and responsibilities for the member team.

|이름 (Name)|ID|역할 (Role)|SNS|주요 책임 (Responsibilities - KR/EN)|
| --- | --- | --- | --- | --- |
|**백종화**|`@jonghwa`|**Team Leader**|[LinkedIn](https://www.linkedin.com/in/jonghwa95/)|로드맵 및 최종 의사결정 / Roadmap & Final decision-making|
|**김태빈**|`@taebin`|**Member**|[Link](#)|멤버 / Member|
|**박승규**|`@seunggyu`|**Member**|[Link](#)|멤버 / Member|
|**유진승**|`@jinseung`|**Member**|[Link](#)|멤버 / Member|
|**임재훈**|`@jaehoon`|**Member**|[LinkedIn](https://www.linkedin.com/in/%EC%9E%AC%ED%9B%88-%EC%9E%84-597470261/)|멤버 / Member|

### 3. 기술 스택 (Tech Stack)

* **Language:** Python 3.11+
* **Framework:** LangGraph, FastAPI
* **LLM:** Google Gemini Flash, Ollama (local fallback)
* **Infra:** Kubernetes (Kind), ArgoCD, Docker, Helm, Chaos Mesh
* **Observability:** Prometheus, Grafana, Loki, Tempo, Pyroscope, Alloy
* **Security:** SOPS + age, cert-manager (Let's Encrypt)
* **Communication:** Slack, GitHub Issues, Discord

### 4. 로드맵 (Roadmap)

* **Phase 1:** 관측성 스택 구축 및 알림 체계 완성 (Observability Stack & Alert System) ✅
* **Phase 2:** LangGraph 에이전트 워크플로우 개발 및 카오스 테스트 (Agent Workflow Dev & Chaos Testing) ⏳
* **Phase 3:** Human-in-the-Loop 피드백 루프 및 E2E 통합 테스트 (HITL Feedback & E2E Integration Test)

### 5. 참여 방법 (How to Contribute)

* **Branch Strategy / 브랜치 전략:**
  * `main` 브랜치가 기본이며, ArgoCD가 자동 동기화합니다. / `main` branch is the default; ArgoCD auto-syncs from it.
  * 작업 시 feature 브랜치를 생성하고 PR을 통해 병합합니다. / Create feature branches for work and merge via PR.
* **Issues:** 버그나 기능 제안은 [GitHub Issues](https://github.com/dr-kube/dr-kube/issues)를 활용하세요. / Please use GitHub Issues for bug reports or feature requests.
* **PRs:** 모든 Pull Request는 리더(`@b100to`)의 리뷰 후 병합됩니다. / All PRs require review by the Team Leader (`@b100to`) before merging.
* **GitOps 원칙 / GitOps Principles:**
  * `kubectl apply/patch` 등 클러스터 직접 수정 금지 — 변경은 오직 Git을 통해서만 수행 / No direct cluster modifications — all changes through Git only
  * `values/*.yaml` 수정 → PR 생성 → ArgoCD Sync / Edit `values/*.yaml` → Create PR → ArgoCD Sync
* **Guide:** [CONTRIBUTING.md](https://github.com/dr-kube/dr-kube/blob/main/CONTRIBUTING.md) 파일을 참고하세요. / Please refer to the CONTRIBUTING.md file.
* **Discord (Official):** [[Dr.Kube Invite Link]](https://discord.gg/kE7hcHJX3W)
  * *KR: 실시간 소통 및 기술 지원을 위한 채널입니다.*
  * *EN: Official channel for real-time communication and technical support.*

### 6. 리소스 및 링크 (Resources & Links)

* **GitHub Repository:** [dr-kube/dr-kube](https://github.com/dr-kube/dr-kube)
* **Docs:** [Architecture](https://github.com/dr-kube/dr-kube/blob/main/docs/ARCHITECTURE.md) / [Roadmap](https://github.com/dr-kube/dr-kube/blob/main/docs/ROADMAP.md) / [Changelog](https://github.com/dr-kube/dr-kube/blob/main/docs/CHANGELOG.md)


> | This is a space where knowledge is not merely consumed, but respected, sovereign, and connected—shared together with cloud industry professionals (Bros).|
> | 지식이 소비되지 않고 존중·주권보장·연결되는 공간으로 클라우드 현업 전문가(Bro)와 함께  공유하고 있습니다. |
