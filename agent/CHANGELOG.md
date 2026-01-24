# AI DrKube 변경 이력

## 🎉 v1.1.0 - 실행 계획 및 YAML Diff 추가 (2026-01-24)

### 새로운 기능

#### ⚡ 실행 계획
- **즉시 실행 가능한 kubectl 명령어** 제공
- 실제 리소스 이름과 네임스페이스가 포함됨
- 복사해서 바로 실행 가능
- 주석으로 명령어의 목적 설명

**예시:**
```bash
kubectl patch deployment api-server -n production \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value":"1Gi"}]'
```

#### 📝 YAML 수정 (Diff)
- **변경이 필요한 YAML 부분**만 diff 형식으로 표시
- ❌ (빨간색 `-`) - 삭제/변경 전 값
- ✅ (초록색 `+`) - 추가/변경 후 값
- Before/After를 한눈에 비교 가능

**예시:**
```yaml
spec:
  resources:
    limits:
❌ -     memory: 512Mi
✅ +     memory: 1Gi
```

### 개선 사항
- **프롬프트 최적화** - AI가 구체적인 실행 계획과 YAML diff 생성
- **파싱 로직 강화** - 코드 블록 파싱 추가
- **출력 형식 개선** - 실행 계획과 diff를 명확하게 구분

### 기술 변경
- `IssueState`에 `action_plan`, `yaml_diff` 필드 추가
- `graph.py`에 코드 블록 파싱 로직 추가
- `cli.py`에 실행 계획 및 diff 출력 로직 추가
- `prompts.py`에 실행 계획 및 YAML diff 요청 추가

---

## 🚀 v1.0.0 - 초기 릴리스 (2026-01-24)

### 주요 기능
- **Windows 환경 완벽 지원**
- **간결한 출력 형식** (70% 더 짧게)
- **3단계 해결책** (즉시/근본/모니터링)
- **LangGraph 기반 워크플로우**
- **Google Gemini API 연동**

### 문서
- README.md - 프로젝트 개요
- ARCHITECTURE.md - 아키텍처 상세
- USAGE.md - 사용 방법
- QUICKSTART_KR.md - 빠른 시작
- WINDOWS_SETUP.md - Windows 설정

### 배치 스크립트
- `setup.bat` - 환경 설정
- `run.bat` - 실행
- `run_tools.bat` - 도구 실행

---

## 📊 버전별 주요 변경사항

| 버전 | 날짜 | 주요 변경사항 |
|------|------|---------------|
| v1.1.0 | 2026-01-24 | ⚡ 실행 계획, 📝 YAML Diff 추가 |
| v1.0.0 | 2026-01-24 | 🚀 초기 릴리스 |

---

## 🔮 향후 계획

### v1.2.0 (계획)
- [ ] 실제 kubectl 명령어 실행 기능
- [ ] 적용 전 시뮬레이션
- [ ] 롤백 기능

### v2.0.0 (계획)
- [ ] 실시간 K8S 클러스터 모니터링
- [ ] Alertmanager Webhook 연동
- [ ] 자동 조치 실행 (opt-in)
- [ ] 웹 UI
