# DR-Kube 변경 이력

## 2026-02-14 - Chaos 확장, 알람 고도화, Agent 자동화

### 🌪️ Chaos 시나리오 확장 (#1186)
- 복합 카오스 5개 시나리오 추가:
  - `chaos/boutique-redis-failure.yaml`
  - `chaos/boutique-payment-delay.yaml`
  - `chaos/boutique-traffic-spike.yaml`
  - `chaos/boutique-dns-failure.yaml`
  - `chaos/boutique-replica-shortage.yaml`
- `Makefile`에 실행 타깃 추가 (`chaos-redis-failure`, `chaos-payment-delay`, `chaos-traffic-spike`, `chaos-dns-failure`, `chaos-replica-shortage`)
- `README.md`에 복합 장애 실행/검증 체크리스트 반영

### 🔔 알람 체계 개선 (운영 품질)
- `values/prometheus.yaml` 알람 라우팅/임계치/지속시간(`for`) 전면 조정
- 저트래픽/잡음 억제를 위한 조건 추가 (container 필터, 최소 트래픽 조건)
- `critical / warning / info` 라우팅 분리 및 노이즈 감소

### 🤖 Agent 자동 동작 복구/강화
- `applications/dr-kube-agent.yaml` 활성화 (주석 해제)
- `manifests/dr-kube-agent/deployment.yaml` 비용 보호 env 추가
  - `COST_MODE`, `MAX_LLM_CALLS_PER_DAY`, `DEDUP_COOLDOWN_MINUTES`
  - `HIGH_MAX_LLM_CALLS_PER_DAY`, `HIGH_DEDUP_COOLDOWN_MINUTES`
- 웹훅 비용 보호 로직 추가:
  - `agent/dr_kube/webhook.py` (일일 상한, fingerprint 쿨다운, 운영 모드/오버라이드)
  - `agent/dr_kube/converter.py` (Alertmanager fingerprint 전달)
  - `agent/.env.example` 운영 변수 추가

### 🌐 Ingress 안정화
- `values/nginx-ingress.yaml` 조정:
  - `replicaCount: 1`
  - `autoscaling` 비활성화
  - `updateStrategy`를 hostPort 환경에 맞게 조정 (`maxSurge: 0`, `maxUnavailable: 1`)
- 증상: `didn't have free ports` 스케줄링 에러 재발 방지

### 📦 이미지 태그 정책 전환 (latest → semver)
- `.github/workflows/agent-build.yaml`:
  - `latest` 태그 제거
  - `v*.*.*` 태그 기반 semver 이미지 빌드
  - 태그 빌드 시 `manifests/dr-kube-agent/deployment.yaml` 이미지 태그 자동 승격 커밋
- `manifests/dr-kube-agent/deployment.yaml` 기본 이미지 태그를 `v0.1.0`으로 변경

---

## 2026-02-07 - 모니터링 고도화 및 인프라 확장

### 🌐 Ingress 통합 관리

#### Online Boutique Ingress
- `manifests/online-boutique/ingress.yaml` 생성 (차트에 Ingress 템플릿 없어 raw manifest 사용)
- `applications/online-boutique.yaml`에 3rd source 추가 (manifests 디렉토리)
- `values/online-boutique.yaml` - frontend를 LoadBalancer → ClusterIP로 변경

#### Chaos Mesh Dashboard Ingress
- `values/chaos-mesh.yaml`에 dashboard ingress 추가
- `dashboard.securityMode: false` 설정 (로컬 개발용, 토큰 로그인 비활성화)

#### 등록된 도메인
| 서비스 | 로컬 | 외부 |
|--------|------|------|
| Grafana | grafana.drkube.local | grafana-drkube.huik.site |
| Prometheus | prometheus.drkube.local | prometheus-drkube.huik.site |
| Alertmanager | alert.drkube.local | alert-drkube.huik.site |
| ArgoCD | argocd.drkube.local | argocd-drkube.huik.site |
| Online Boutique | boutique.drkube.local | boutique-drkube.huik.site |
| Chaos Mesh | chaos.drkube.local | chaos-drkube.huik.site |
| Jaeger | jaeger.drkube.local | jaeger-drkube.huik.site |

---

### 📊 모니터링 확장

#### metrics-server 설치
- `values/metrics-server.yaml` 생성 (`--kubelet-insecure-tls` Kind 환경용)
- `applications/metrics-server.yaml` 생성 (kube-system 네임스페이스)
- `kubectl top nodes/pods` 실시간 리소스 모니터링 가능

#### Grafana 데이터소스 수정
- Prometheus URL 수정: `http://prom-prometheus-server` → `http://prometheus-server`
- "No data" 문제 해결

#### Grafana 커스텀 대시보드
- **Pod Resources (Real-time)** 대시보드 추가 (10초 자동 갱신)
  - CPU Usage by Pod, CPU Usage vs Limit, CPU Throttle Rate
  - Memory Usage by Pod, Memory Usage vs Limit, Memory Usage % (게이지)
  - Pod Restarts, OOMKilled Events
  - namespace/pod 템플릿 변수로 필터링

---

### 🔔 Slack 알림 연동

#### Alertmanager Slack 통합
- `values/prometheus.yaml`에 Slack receiver 설정
- K8s Secret 방식으로 webhook URL 보안 처리
  - `extraSecretMounts`로 Secret 파일 마운트
  - `slack_api_url_file`로 파일에서 URL 읽기
- 알림 템플릿: firing/resolved 상태 구분, 네임스페이스/Pod 정보 포함

#### 시크릿 관리 스크립트
- `scripts/setup-slack.sh` 생성 (Slack webhook Secret 수동 생성용)

---

### 🔍 Jaeger APM 설치

#### Jaeger All-in-One 배포
- `values/jaeger.yaml` 생성 (in-memory 저장, 로컬 개발용)
- `applications/jaeger.yaml` 생성 (jaegertracing/helm-charts v3.4.1)
- Ingress 설정 (jaeger.drkube.local / jaeger-drkube.huik.site)

#### Grafana 연동
- Jaeger 데이터소스 추가 (`uid: jaeger-uid`)
- Loki → Jaeger: `derivedFields`로 traceID 연결
- Jaeger → Loki: `tracesToLogsV2` 설정
- Jaeger → Prometheus: `tracesToMetrics` (Request Rate, Duration)
- `nodeGraph` 활성화

---

### 🔐 시크릿 관리 (SOPS + age)

#### 구축된 시스템
- `.sops.yaml` - SOPS 설정 (age 공개키)
- `secrets/secrets.yaml` - 평문 시크릿 (.gitignore)
- `secrets/secrets.enc.yaml` - 암호화된 시크릿 (Git 커밋 안전)
- `secrets/age.key` - 비밀키 (.gitignore, 오프라인 공유)

#### 관리되는 시크릿
| 시크릿 | 용도 | K8s 네임스페이스 |
|--------|------|-----------------|
| slack_webhook_url | Alertmanager 슬랙 알림 | monitoring |
| cloudflare_api_token | cert-manager DNS-01 | cert-manager |
| gemini_api_key | LLM API | agent/.env |

#### Makefile 명령어
```bash
make secrets-init      # 키 생성 (팀 리더)
make secrets-import    # 키 가져오기 (팀원)
make secrets-encrypt   # 암호화
make secrets-decrypt   # 복호화
make secrets-apply     # K8s Secret 생성
make secrets-status    # 상태 확인
```

---

### 🔧 버그 수정

| 문제 | 원인 | 해결 |
|------|------|------|
| Chaos Mesh 토큰 로그인 | `securityMode`가 top-level에 위치 | `dashboard.securityMode: false`로 이동 |
| Chaos Mesh CRD sync 실패 | annotation 262144 bytes 초과 | `Replace=true` 제거, `ServerSideApply=true` 유지 |
| Grafana "No data" | Prometheus URL 오류 | `prometheus-server`로 수정 |
| Alertmanager Pending | PVC storageClass 불일치 | PVC 삭제 후 재생성 |

---

## 2026-01-27 (Day 1) - 프로젝트 기반 구축

### 📋 프로젝트 정리 및 문서화

#### AI 도구 컨텍스트 설정
- `.github/copilot-instructions.md` 생성 - GitHub Copilot Chat용
- `.claude/CLAUDE.md` 업데이트 - Claude Code용
- 팀원 일관성을 위한 AI 도구 가이드 통일

#### 문서 폴더 정리
- docs/ 폴더 대폭 정리 (13개 → 5개)
- 중복/오래된 문서 삭제:
  - ❌ README.md (영문), QUICKSTART_KR.md, SETUP.md
  - ❌ WINDOWS_SETUP.md, USAGE.md, SUMMARY.md
  - ❌ IMPROVEMENTS.md, CHANGELOG.md (구버전)
- 유지된 문서:
  - ✅ README.md, ARCHITECTURE.md, ROADMAP.md
  - ✅ ALLOY_CONFIG.md, CHAOS_MESH_TOKEN.md

#### ROADMAP 작성
- Phase 1 (Week 1-2): 환경 + PR 생성
- Phase 2 (Week 3-4): 알람 + 데모
- 목표일: 2026-02-28

---

### 🛠️ 개발 환경 자동화

#### Makefile 전면 개편
```bash
# 클러스터 명령어
make setup              # Kind + ArgoCD 원클릭 설치
make teardown           # 클러스터 삭제
make port-forward       # 포트포워딩 시작 (ArgoCD:8080, Grafana:3000)
make port-forward-stop  # 포트포워딩 종료

# 에이전트 명령어
make agent-setup        # 환경 설정
make agent-run          # 이슈 분석
make agent-fix          # 분석 + PR 생성
make agent-oom          # OOM 이슈 분석
make agent-oom-fix      # OOM + PR 생성
make help               # 도움말
```

#### 로컬 환경 스크립트
- `scripts/setup.sh` - Kind 클러스터 + ArgoCD 원클릭 설치
  - 의존성 자동 설치 (Docker, Kind, kubectl, Helm)
  - Kind 3노드 클러스터 (control-plane + worker×2)
  - ArgoCD Helm 설치 + Root Application 배포
  - 포트포워딩 기능 내장
- `scripts/teardown.sh` - 클러스터 삭제
- `scripts/setup-agent.sh` - 에이전트 환경 설정 (기존)

#### 크로스 플랫폼 지원
- ✅ macOS (Intel/Apple Silicon)
- ✅ Windows + WSL2 (Ubuntu)
- ✅ Linux (Ubuntu/Debian)
- Homebrew 기반 통일된 설치 방식

---

### 🚀 에이전트 핵심 기능 구현

#### 워크플로우 확장 (3노드 → 4노드)
```
기존: load_issue → analyze → suggest
신규: load_issue → analyze → generate_fix → create_pr
```

#### 신규 노드
- **`generate_fix`** - LLM 기반 YAML 수정안 자동 생성
  - values 파일 읽기 → LLM 분석 → 수정된 YAML 출력
  - 이슈 타입별 대상 파일 매핑
- **`create_pr`** - GitHub PR 자동 생성
  - 브랜치 생성 → 파일 수정 → 커밋 → PR 생성
  - gh CLI 사용

#### 신규 파일
- `agent/dr_kube/github.py` - GitHub 클라이언트
  - `GitHubClient` 클래스 (브랜치/커밋/PR)
  - `generate_branch_name()` - 브랜치명 생성
  - `generate_pr_body()` - PR 본문 템플릿
- `agent/dr_kube/prompts.py` - `GENERATE_FIX_PROMPT` 추가

#### 상태 확장 (state.py)
```python
# 신규 필드
target_file: str      # 수정할 values 파일
fix_content: str      # 수정된 YAML
fix_description: str  # 변경 설명
branch_name: str      # PR 브랜치명
pr_url: str          # PR URL
pr_number: int       # PR 번호
```

#### CLI 개선 (cli.py)
- argparse 기반 명령어 구조
- `analyze` - 분석만
- `fix` - 분석 + PR 생성
- `--with-pr` 옵션 지원

---

### 🧪 테스트 환경 구축

#### OOM 테스트 앱 (Helm 기반)
- `charts/dr-kube-test/` - Helm 차트
- `values/oom-test.yaml` - 테스트 앱 values
- stress 컨테이너로 의도적 OOM 발생
- 에이전트가 수정할 수 있는 구조

#### 이슈 샘플 업데이트
- `issues/sample_oom.json` 업데이트
  - `values_file` 필드 추가
  - 실제 테스트 앱에 맞게 수정

---

### 🔧 버그 수정 및 호환성

#### Kind 호환성
- StorageClass `csi-storageclass` → `standard` 변경
  - values/prometheus.yaml
  - values/grafana.yaml
  - values/loki.yaml
- PVC Pending 문제 해결

#### ServiceMonitor 이슈
- nginx-ingress ServiceMonitor 비활성화
- CRD 미설치 환경 호환

#### 기타 수정
- PROJECT_ROOT 경로 수정 (parent 개수)
- generate_fix 변수 스코프 오류 수정
- ArgoCD 비밀번호 조회 로직 수정 (하드코딩된 비밀번호 사용)

---

### ✅ 완료된 체크리스트

#### Phase 1 (로컬 환경)
- [x] `scripts/setup.sh` - Kind + ArgoCD 설치
- [x] `scripts/teardown.sh` - 정리
- [x] Makefile 클러스터 명령어
- [x] 포트포워딩 기능
- [x] 크로스 플랫폼 테스트

#### Phase 1 (에이전트)
- [x] `generate_fix` - YAML 수정안 생성
- [x] `create_pr` - GitHub PR 생성
- [x] CLI 명령어 구조 개선

#### 문서화
- [x] `.github/copilot-instructions.md`
- [x] `.claude/CLAUDE.md` 업데이트
- [x] docs/ 폴더 정리
- [x] ROADMAP.md 작성

---

## 다음 단계 (Phase 2)
- [ ] `notify` 노드 구현 (Slack 알람)
- [ ] E2E 데모 시나리오
- [ ] 실제 OOM 테스트 + PR 생성 검증
