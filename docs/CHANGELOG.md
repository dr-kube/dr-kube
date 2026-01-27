# DR-Kube 변경 이력

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
