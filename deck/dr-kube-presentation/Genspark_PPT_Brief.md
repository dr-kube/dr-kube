# DR-Kube Genspark PPT Brief

이 문서는 Genspark 같은 외부 PPT 생성기에 그대로 넣거나, 약간 다듬어 붙여넣기 위한 발표자료 생성 브리프다.

목표:
- DR-Kube 프로젝트 발표용 PPT 생성
- 기능 소개 수준을 넘어서 문제 정의, 아키텍처, 기술적 난점, LLM 정확도 확보 전략, 로드맵까지 설득력 있게 보여주기
- 발표 시간 기준은 7~10분

중요한 전제:
- 이 프로젝트를 "완전 자율 복구 시스템"이라고 과장하지 말 것
- 핵심 메시지는 "LLM이 똑똑해서 자동복구한다"가 아니라 "잘못된 복구를 줄이기 위해 관측성, 정책 제약, validate, retry, GitOps, 복구 후 검증을 결합한 시스템"이라는 점
- 클러스터 직접 변경은 금지하고 Git PR 기반 변경만 허용하는 GitOps 원칙을 반드시 강조할 것

## 1. 발표의 한 문장 메시지

DR-Kube는 Kubernetes 장애 대응을 수작업 운영에서 관측성 기반 AI 판단과 GitOps 기반 안전한 복구 루프로 전환하려는 프로젝트다.

짧은 대체 문장:
- 관측성이 근거를 만들고, AI가 수정안을 만들고, GitOps가 안전하게 반영한다.
- DR-Kube의 핵심은 "감지 → 판단 → Git 변경 → 복구 검증"의 폐루프다.

## 2. 청중과 톤

청중:
- 소프트웨어/클라우드/DevOps 수업 발표 청중
- Kubernetes를 조금 알거나, AI 에이전트 프로젝트에 관심 있는 교수/학생

톤:
- 너무 마케팅스럽지 않게
- 기술적으로 정확하되 발표용으로 간결하게
- "우리가 뭘 만들었는가"보다 "왜 이 구조가 필요한가"가 먼저 보이게

## 3. 슬라이드 스타일 가이드

전체 스타일 방향:
- "dashboard" 느낌보다 "editorial technical keynote" 느낌
- 배경은 밝고 깨끗하게
- 기본색은 navy / fog / slate
- 강조색은 cyan 중심
- 빨강, 초록, 주황은 상태 비교나 정책/위험 설명에만 제한적으로 사용

디자인 원칙:
- 카드 남용 금지
- 한 슬라이드에 핵심 메시지 1개, 보조 포인트 2~3개 정도만 보이게
- 제목은 크게, 본문은 짧게
- 기술 슬라이드는 박스 나열보다 흐름과 레이어가 먼저 읽히게

폰트 톤:
- 한국어 현대적 기술 발표 느낌
- 가능하면 Pretendard 또는 SUIT 계열 느낌
- 너무 딱딱한 문서 템플릿처럼 보이지 않게

## 4. 추천 슬라이드 구성

총 10장 내외로 구성할 것.

### Slide 1. 표지

제목:
- DR-Kube

부제:
- Kubernetes 장애 분석 및 GitOps 복구 제안을 위한 AI + GitOps 시스템

강조 문장:
- Prometheus Alert → LangGraph Agent → GitHub PR → ArgoCD Sync

핵심 포인트:
- 왜 필요한가
- 핵심 아이디어
- GitOps 기반 복구 원칙

시각 방향:
- 임팩트 있는 표지
- 너무 많은 텍스트 금지

### Slide 2. 문제 정의와 해결 아이디어

왼쪽:
- 기존 장애 대응의 비효율
- 장애 탐지, 원인 분석, YAML 수정, PR 생성, 배포 확인까지 도구가 분절돼 있고 MTTR이 길어진다

오른쪽:
- DR-Kube가 자동화하는 복구 루프
- 감지 → 수집 → 분석 → 변경 → 복구

반드시 들어갈 문장:
- 핵심은 장애 대응의 분절된 수작업 흐름을 검증 가능한 복구 루프로 바꾸는 것이다.

### Slide 3. 시스템 아키텍처

이 슬라이드는 가장 중요하다.
단순 컴포넌트 나열이 아니라 역할 기반 4개 존으로 보여줄 것.

슬라이드 제목:
- DR-Kube 시스템 아키텍처

부제:
- 관측성으로 장애를 감지하고, 에이전트가 수정안을 만들고, GitOps가 안전하게 복구를 반영합니다.

핵심 구조:
1. 장애 감지 / 근거 수집
2. AI 복구 판단
3. GitOps 반영
4. 복구 검증 / 알림

아키텍처에 포함할 요소:
- Kubernetes Cluster
- Prometheus Alert Rules
- Alertmanager
- Converter
- LangGraph Agent
- LLM
- GitHub PR
- values/*.yaml 변경
- ArgoCD Sync
- 후속 복구 검증 경로
- Slack / Notifications

하단 레이어:
- Observability Evidence Layer
- Metrics / Logs / Traces / Profiles

별도 실험 계층:
- Chaos / Fault Injection Layer
- Chaos Mesh

핵심 화살표:
- K8s Cluster → Prometheus → Alertmanager → Converter → LangGraph Agent → GitHub PR → ArgoCD Sync
- ArgoCD Sync 이후에는 후속 복구 검증 경로가 Pod 상태와 Alert 해소 여부를 다시 확인

보조 설명:
- 관측성 스택이 판단 근거를 만든다
- LangGraph 에이전트가 수정안을 생성하고 validate 한다
- GitOps가 변경을 안전하게 반영한다
- 후속 복구 검증 경로가 복구 성공 여부를 다시 확인한다

핵심 문장:
- 이 아키텍처의 핵심은 "관측성 → 판단 → Git 변경 → 복구 검증"이 하나의 폐루프로 연결된다는 점이다.

### Slide 4. 핵심 워크플로우

비교 구조:
- 현재
- 목표

반드시 강조할 대비:
- LLM 호출 2회 → 1회
- 사람 확인 중심 → validate retry loop 중심
- 분석과 수정 생성 분리 → analyze_and_fix 통합

팩트:
- 문서상 현재: load_issue → analyze → generate_fix → create_pr
- 목표 #1194: load_issue → analyze_and_fix → validate → create_pr
- 현재 코드 기준 PR 포함 흐름: load_issue → analyze_and_fix → validate → create_pr
- validate 실패 시 최대 3회 재시도

핵심 문장:
- 핵심 개선은 LLM 호출 수를 줄인 것보다, 결과를 다시 검증하는 제어 루프를 넣은 것이다.

### Slide 5. 데모 시나리오

추천 시나리오:
- OOMKilled 복구 데모

흐름:
1. 장애 발생
2. Alert 발화
3. Agent 분석
4. GitHub PR 생성
5. ArgoCD Sync
6. 후속 복구 검증 및 완료 알림

반드시 들어갈 예시:
- memory 512Mi → 1Gi

발표 포인트:
- 과정보다 "실제로 무엇을 바꿔 복구했는지"가 잘 보이게

### Slide 6. 왜 안전한가: GitOps 원칙

핵심 메시지:
- DR-Kube는 클러스터를 직접 고치지 않고, 검토 가능한 변경만 제안한다

반드시 포함:
- 클러스터 변경은 Git(PR)로만 수행
- kubectl apply, kubectl patch 같은 쓰기 명령 금지
- 수정 대상은 기본적으로 values/*.yaml
- PR에는 issue 정보, root cause, target file, diff가 포함됨
- 완료 알림은 notify 노드보다 ArgoCD Notifications → Slack 방향

핵심 문장:
- 자동화의 속도보다 변경의 안전성과 추적 가능성을 우선한 구조다.

### Slide 7. 개발하면서 어려웠던 부분

이 슬라이드는 기능 자랑보다 개발의 현실성을 보여주는 슬라이드다.

반드시 넣을 내용:
- Alert 품질과 노이즈 제어
- PR spam 방지, cooldown, 그룹화 등 운영 제어 필요
- 단일 alert가 아니라 composite incident 처리가 필요해짐
- crash/error 계열에서 위험한 자동 리소스 상향을 막아야 했음
- LLM provider 연동이 반복적으로 흔들렸음
- 실행 환경 제약 때문에 in-pod kubectl 의존을 줄여야 했음

발표용 문장:
- 가장 어려운 문제는 LLM 호출 자체보다, 어떤 incident를 어떤 제약 아래 자동화할지 정하는 것이었습니다.
- 이 프로젝트는 모델 정확도뿐 아니라 운영 노이즈, 비용, 위험한 수정, 실행 환경 제약을 동시에 다뤄야 했습니다.

참고 커밋 예시를 작게 넣어도 좋음:
- 4dbad0d
- 6d01c37
- d328c4a
- a1c6752
- a8f4e14
- 4654531
- d3025c0

### Slide 8. LLM 판단 정확도를 위해 한 것

이 슬라이드는 매우 중요하다.
핵심은 "모델 성능"보다 "구조적 안전장치"다.

반드시 포함:
- 입력 정규화
  - converter.py가 Alertmanager payload를 내부 issue 형태로 정규화
  - resource, namespace, values_file 추론
  - 현재 values YAML 전체를 프롬프트에 포함
- 출력 형식 강제
  - prompts.py에서 근본 원인, 심각도, 해결책 2개, 전체 YAML, 변경 설명 형식을 고정
- 정책 기반 제약
  - pod_crash, service_error, upstream_error, service_down 계열은 memory/cpu/resources 변경 금지
  - replicas, PDB, timeout/retry/backoff/circuit-breaker 계열 우선
- 규칙 기반 우선 처리
  - 일부 장애는 _rule_based_fix()로 최소 replica patch 우선
- validate + retry
  - YAML 문법 검사
  - 원본과 실제 차이 존재 여부
  - dict 형식 여부
  - 장애 타입별 정책 위반 검사
  - 최대 3회 재시도
- 사후 검증
  - 후속 복구 검증 경로에서 verifier.py가 Pod Running/Ready와 Alert 해소 여부 확인

발표용 핵심 문장:
- 정확도는 모델 성능 하나로 확보하지 않았습니다. 입력 정규화, 출력 형식 강제, 정책 제약, validate, retry, 복구 후 검증의 합으로 만들었습니다.
- DR-Kube는 "LLM이 맞힌다"가 아니라 "LLM이 틀려도 위험한 답은 통과시키지 않게 한다"에 더 가깝습니다.

가능하면 작은 코드 경로 표기:
- agent/dr_kube/graph.py
- agent/dr_kube/prompts.py
- agent/dr_kube/converter.py
- agent/dr_kube/verifier.py

### Slide 9. 로드맵

숫자 바 차트보다 세 단계 구조가 더 좋다.

구성:
- 현재 집중
- 다음 확장
- 제품형으로 가는 단계

우선순위 근거:
- #1164 Converter 알림 타입 매핑 확장
- #1194 analyze_and_fix + validate loop
- #1172 서비스 레벨 알림 규칙
- #1186 복합 chaos 시나리오
- #1175 ArgoCD Notifications → Slack
- #1195 PR 댓글 기반 재생성(HITL)
- #1196 Grafana 대시보드 확장
- #1167 E2E 통합 테스트

주의:
- 목표 완료일은 문서상 2026-02-28이지만, 현재 시점이 그 이후이므로 "목표 완료"처럼 말하지 말 것
- "프로토타입 범위를 확장 중" 정도로 표현할 것

### Slide 10. 기대 효과와 마무리

세 가지 효과:
- 운영 효율
- 안전한 자동화
- 확장성

마무리 한 문장:
- DR-Kube는 장애 대응을 수작업 운영에서 검증 가능한 GitOps 복구 루프로 전환하는 프로젝트입니다.

추가 요소:
- 발표가 데모 중심이면 오른쪽에 demo checklist를 넣어도 좋다

## 5. 반드시 포함해야 할 기술 팩트

- 프로젝트는 AI 기반 Kubernetes 장애 대응 자동화 및 GitOps 복구 제안 시스템이다
- Prometheus Alert → Alertmanager → Agent Webhook → LangGraph → GitHub PR → ArgoCD Sync 흐름이 핵심이며, 이후 후속 복구 검증 경로가 붙는다
- 관측성 스택은 Prometheus, Alertmanager, Grafana, Loki, Tempo, Pyroscope, Alloy다
- Chaos Mesh는 관측성 도구가 아니라 장애 재현/실험 계층이다
- GitOps 원칙 때문에 직접 kubectl 쓰기 명령은 금지한다
- 수정 대상은 기본적으로 values/*.yaml 이다
- 현재 코드상 analyze_and_fix와 validate retry loop 구조가 존재한다
- validate 실패 시 최대 3회 재시도한다
- 일부 incident는 규칙 기반 수정이 LLM보다 우선한다
- 복구는 PR 생성으로 끝나지 않고, 확장된 후속 검증 경로에서 verifier가 Pod 상태와 Alert 해소 여부를 다시 확인할 수 있다
- 완료 알림은 ArgoCD Notifications → Slack 방향으로 이동 중이다

## 6. 반드시 피해야 할 과장

다음 표현은 피할 것:
- 완전 자율 복구 시스템
- LLM이 항상 올바른 수정안을 만든다
- Gemini만 사용한다
- notify 노드가 이미 완성되어 있다
- 목표 완료일을 이미 달성했다

대신 이렇게 표현할 것:
- 프로토타입 범위에서 폐루프 복구 구조를 확장 중이다
- 오답 가능성을 전제로 제약과 검증을 덧대는 방향이다
- LLM provider는 환경과 통합 상황에 따라 조정되었다
- 완료 알림 구조는 ArgoCD Notifications 중심으로 정리 중이다

## 7. Genspark에 넣을 직접 지시문

아래 내용을 참고해서 한국어 프로젝트 발표용 PPT를 만들어줘.

요구사항:
- 총 10장 내외
- 16:9 비율
- 밝은 배경의 현대적인 기술 발표 스타일
- "dashboard" 느낌보다 "editorial technical keynote" 느낌
- 색상은 navy, fog, cyan 중심
- 카드 남용 금지
- 시스템 아키텍처 슬라이드는 컴포넌트 나열이 아니라 4개 역할 존 기반 폐루프 다이어그램으로 그려줘
- 아키텍처는 작은 박스를 너무 많이 만들지 말고, 4개 존과 메인 플로우 1줄이 먼저 읽히게 해줘
- 워크플로우 슬라이드는 현재 vs 목표 비교가 한눈에 보이게 크게 표현해줘
- "개발하면서 어려웠던 부분"과 "LLM 판단 정확도를 위해 한 것" 슬라이드는 반드시 포함해줘
- 텍스트는 너무 많지 않게, 발표자가 말로 설명할 수 있도록 요약형으로 써줘
- 각 슬라이드 본문은 핵심 포인트 3개 이하로 제한해줘
- GitOps 원칙, validate/retry, 후속 복구 검증 경로를 반드시 강조해줘
- OOMKilled 데모 예시에서 `memory 512Mi → 1Gi` 같은 실제 변경 예시를 포함해줘

## 8. 발표자가 말할 때 반복하면 좋은 표현

- 관측성이 근거를 만들고, AI가 수정안을 만들고, GitOps가 안전하게 반영합니다.
- DR-Kube의 핵심은 감지, 판단, Git 변경, 복구 검증의 폐루프입니다.
- 정확도는 모델 성능만이 아니라 입력 품질, 정책 제약, validate, retry, 사후 검증으로 확보했습니다.
- 이 프로젝트는 LLM을 믿는 시스템이 아니라, LLM의 오답 가능성을 관리하는 시스템에 가깝습니다.
