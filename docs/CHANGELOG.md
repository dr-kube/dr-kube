# DR-Kube 변경 이력

## 2026-01-27 (Day 1)

### 🚀 핵심 기능 구현

#### 에이전트 워크플로우 확장
- **`generate_fix` 노드** - LLM 기반 YAML 수정안 자동 생성
- **`create_pr` 노드** - GitHub PR 자동 생성 (gh CLI 사용)
- 워크플로우: `load_issue → analyze → generate_fix → create_pr`

#### 신규 파일
- `agent/dr_kube/github.py` - GitHub 클라이언트 (브랜치/커밋/PR)
- `charts/dr-kube-test/` - OOM 테스트용 Helm 차트
- `values/oom-test.yaml` - 테스트 앱 values

### 🛠️ 환경 구축

#### 로컬 클러스터 스크립트
- `scripts/setup.sh` - Kind + ArgoCD 원클릭 설치
- `scripts/teardown.sh` - 클러스터 삭제
- 포트포워딩 기능 추가 (`make port-forward`)

#### Makefile 명령어 추가
```bash
make setup              # 클러스터 설치
make teardown           # 클러스터 삭제
make port-forward       # 포트포워딩 시작
make agent-fix          # 분석 + PR 생성
make agent-oom-fix      # OOM 이슈 + PR
```

### 🔧 버그 수정
- StorageClass `csi-storageclass` → `standard` (Kind 호환)
- ServiceMonitor 비활성화 (CRD 미설치 환경)
- PROJECT_ROOT 경로 수정
- generate_fix 변수 스코프 오류 수정

### 📚 문서 정리
- docs/ 폴더 정리 (13개 → 5개)
- `.github/copilot-instructions.md` 생성
- ROADMAP.md 업데이트

### ✅ 완료된 체크리스트
- [x] `scripts/setup.sh` - Kind + ArgoCD 설치
- [x] `scripts/teardown.sh` - 정리
- [x] `generate_fix` - YAML 수정안 생성
- [x] `create_pr` - GitHub PR 생성

---

## 다음 단계 (Phase 2)
- [ ] `notify` 노드 구현 (Slack 알람)
- [ ] E2E 데모 시나리오
