# AI DrKube - Kubernetes 장애 분석 AI Agent

Kubernetes 환경의 장애를 자동으로 분석하고 조치 방안을 제시하는 AI Agent입니다.

## 🚀 빠른 시작 (3단계)

### 1단계: 환경 설정
```cmd
cd agent
.\setup.bat
```

### 2단계: 실행
```cmd
.\run.bat issues\sample_oom.json
```

### 3단계: 결과 확인
```
============================================================
  DR-Kube 분석 결과
============================================================

📋 이슈: CrashLoopBackOff
📦 리소스: api-server-7d4f8b9c5-xyz
🔴 심각도: CRITICAL

🔍 근본 원인:
   컨테이너가 메모리 제한 초과로 강제 종료되었습니다.

💡 해결책:
   1. Deployment의 메모리 Limit을 1Gi로 상향 조정
   2. 메모리 프로파일링을 통해 누수 여부 확인
   3. 메모리 사용률 80% 초과 시 알람 설정

⚡ 실행 계획:
------------------------------------------------------------
  kubectl patch deployment api-server -n production \
    --type='json' \
    -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value":"1Gi"}]'
------------------------------------------------------------

📝 YAML 수정 (Diff):
------------------------------------------------------------
     spec:
       resources:
         limits:
  ❌ -     memory: 512Mi
  ✅ +     memory: 1Gi
------------------------------------------------------------
```

완료! 🎉

---

## 📋 사용 가능한 샘플 이슈

### 리소스 관련
```cmd
.\run.bat issues\sample_oom.json
.\run.bat issues\sample_cpu_throttle.json
```

### 설정/구성 관련
```cmd
.\run.bat issues\sample_image_pull.json
.\run.bat issues\sample_configmap_missing.json
.\run.bat issues\sample_pvc_pending.json
```

### 헬스체크 관련
```cmd
.\run.bat issues\sample_liveness_probe_fail.json
```

### 네트워크 관련
```cmd
.\run.bat issues\sample_network_policy.json
.\run.bat issues\sample_dns_resolution.json
```

### 스케줄링/권한 관련
```cmd
.\run.bat issues\sample_node_not_ready.json
.\run.bat issues\sample_rbac_permission.json
```

### 애플리케이션 관련
```cmd
.\run.bat issues\sample_app_crash.json
```

---

## 💡 실행 예시

### 예시 1: OOM (Out of Memory) 분석
```cmd
.\run.bat issues\sample_oom.json
```

**출력:**
- 📋 이슈: CrashLoopBackOff
- 🔴 심각도: CRITICAL
- 🔍 근본 원인: 메모리 512Mi 초과
- 💡 해결책: 메모리 1Gi로 증설
- ⚡ kubectl patch 명령어 제공
- 📝 YAML diff 제공

### 예시 2: RBAC 권한 부족
```cmd
.\run.bat issues\sample_rbac_permission.json
```

**출력:**
- 📋 이슈: Forbidden: insufficient permissions
- 🟠 심각도: HIGH
- 🔍 근본 원인: ServiceAccount에 pods 권한 없음
- 💡 해결책: Role 및 RoleBinding 생성
- ⚡ kubectl create role/rolebinding 명령어
- 📝 Role YAML diff

### 예시 3: DNS 해석 실패
```cmd
.\run.bat issues\sample_dns_resolution.json
```

**출력:**
- 📋 이슈: Name resolution failed
- 🔴 심각도: CRITICAL
- 🔍 근본 원인: CoreDNS Pod 비정상
- 💡 해결책: CoreDNS 재시작 및 메모리 증설
- ⚡ kubectl rollout restart 명령어
- 📝 CoreDNS 메모리 YAML diff

---

## 🎯 주요 기능

### 1. 간결한 3단계 해결책
- **즉시 조치**: 지금 바로 실행
- **근본 해결**: 재발 방지
- **모니터링**: 예방 조치

### 2. ⚡ 실행 계획
```bash
# 복사해서 바로 실행 가능한 kubectl 명령어
kubectl patch deployment api-server -n production \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value":"1Gi"}]'
```

### 3. 📝 YAML 수정 (Diff)
```yaml
spec:
  resources:
    limits:
❌ -     memory: 512Mi  # Before
✅ +     memory: 1Gi     # After
```

---

## 🛠️ 설치 요구사항

### 필수
- **Python 3.10+** - [다운로드](https://www.python.org/downloads/)
- **Google Gemini API 키** - [발급](https://makersuite.google.com/app/apikey)

### 선택 (K8S 연동 시)
- kubectl
- kubeconfig

---

## ⚙️ 환경 설정

### .env 파일
```env
# 필수
GOOGLE_API_KEY=your-api-key-here

# 선택
MODEL_NAME=gemini-3-flash-preview
VERBOSE=false
AUTO_APPROVE=false
```

---

## 📚 사용 방법

### 기본 사용
```cmd
.\run.bat issues\sample_oom.json
```

### 상세 출력 (Verbose)
```cmd
.\run.bat issues\sample_oom.json -v
```

### 샘플 목록 보기
```cmd
.\run.bat
```

---

## 🎓 기술 스택

- **LLM**: Google Gemini (gemini-3-flash-preview)
- **프레임워크**: LangGraph
- **언어**: Python 3.10+
- **라이브러리**: LangChain, python-dotenv, pydantic

---

## 📊 분석 가능한 이슈 유형

| 카테고리 | 이슈 유형 | 샘플 파일 |
|---------|----------|-----------|
| 리소스 | OOM, CPU Throttle | sample_oom.json, sample_cpu_throttle.json |
| 설정 | Image Pull, ConfigMap, PVC | sample_image_pull.json, sample_configmap_missing.json, sample_pvc_pending.json |
| 헬스체크 | Liveness Probe | sample_liveness_probe_fail.json |
| 네트워크 | Network Policy, DNS | sample_network_policy.json, sample_dns_resolution.json |
| 스케줄링 | Node NotReady, RBAC | sample_node_not_ready.json, sample_rbac_permission.json |
| 애플리케이션 | Crash | sample_app_crash.json |

---

## 📁 프로젝트 구조

```
agent/
├── run.bat                   # 실행 스크립트
├── setup.bat                 # 환경 설정
├── .env                      # 환경 변수
│
├── issues/                   # 샘플 이슈
│   ├── sample_oom.json
│   ├── sample_rbac_permission.json
│   └── ... (11개)
│
├── src/                      # 소스 코드
│   ├── cli.py
│   └── dr_kube/
│
└── docs/                     # 문서
    ├── QUICKSTART_KR.md
    ├── ARCHITECTURE.md
    └── ...
```

---

## 🔧 문제 해결

### Python을 찾을 수 없습니다
```cmd
# Python PATH 설정 확인
python --version
```

### 가상환경 오류
```cmd
# 수동 설치
python -m venv venv
.\venv\Scripts\activate
pip install -r src\requirements.txt
```

### API 키 오류
```cmd
# .env 파일 확인
notepad .env
```

---

## 📖 추가 문서

| 문서 | 설명 |
|------|------|
| [QUICKSTART_KR.md](./QUICKSTART_KR.md) | 빠른 시작 가이드 |
| [WINDOWS_SETUP.md](./WINDOWS_SETUP.md) | Windows 상세 설정 |
| [USAGE.md](./USAGE.md) | 사용 방법 및 옵션 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 아키텍처 및 작동 원리 |
| [CHANGELOG.md](./CHANGELOG.md) | 변경 이력 |

---

## 🎯 실전 예시

### 상황 1: 프로덕션 Pod가 계속 재시작됨
```cmd
.\run.bat issues\sample_oom.json
```
→ AI 분석: 메모리 부족
→ 해결: `kubectl patch`로 메모리 1Gi 증설

### 상황 2: CronJob이 실행 안 됨
```cmd
.\run.bat issues\sample_rbac_permission.json
```
→ AI 분석: RBAC 권한 부족
→ 해결: Role/RoleBinding 생성 명령어 제공

### 상황 3: 서비스 간 통신 안 됨
```cmd
.\run.bat issues\sample_dns_resolution.json
```
→ AI 분석: CoreDNS 문제
→ 해결: CoreDNS 재시작 및 리소스 증설

---

## 🚀 다음 단계

### 현재 (K8S 없이)
- ✅ 샘플 데이터로 AI 분석 테스트
- ✅ kubectl 명령어 학습
- ✅ YAML 수정 방법 학습

### 향후 (K8S 연동)
- 🔄 실시간 클러스터 모니터링
- 🔄 자동 조치 실행
- 🔄 Alertmanager 연동

---

## ⚠️ 보안 주의사항

**프로덕션 환경에서는:**
- `AUTO_REMEDIATION=false` 설정 필수
- 모든 조치는 수동 승인 후 실행
- 최소 권한 원칙 적용

---

## 💬 도움말

문제가 발생하면:
1. [WINDOWS_SETUP.md](./WINDOWS_SETUP.md) 확인
2. [USAGE.md](./USAGE.md) 참고
3. `-v` 옵션으로 상세 로그 확인

---

**Made with ❤️ using Google Gemini AI**
