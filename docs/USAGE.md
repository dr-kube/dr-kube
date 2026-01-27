# AI DrKube 사용 가이드

## 🚀 기본 사용법

### 간단한 출력 (기본)
```cmd
run.bat issues\sample_oom.json
```

**출력 예시:**
```
============================================================
  DR-Kube 분석 결과
============================================================

📋 이슈: CrashLoopBackOff
📦 리소스: api-server-7d4f8b9c5-xyz
🔴 심각도: CRITICAL

🔍 근본 원인:
   컨테이너가 할당된 메모리 제한(512Mi)을 초과하여 커널에 의해
   강제 종료(OOMKilled)되었습니다.

💡 해결책:
   1. Deployment의 메모리 Limit을 1Gi로 상향 조정합니다.
   2. 메모리 프로파일링을 통해 누수 여부를 확인합니다.
   3. 메모리 사용률 80% 초과 시 알람을 설정합니다.

⚡ 실행 계획:
------------------------------------------------------------
  # Deployment의 메모리 Limit을 1Gi로 즉시 상향 조정
  kubectl patch deployment api-server -n production \
    --type='json' \
    -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value":"1Gi"}]'
------------------------------------------------------------

📝 YAML 수정 (Diff):
------------------------------------------------------------
     spec:
       template:
         spec:
           containers:
  ❌       - name: app
             resources:
               limits:
  ❌ -           memory: 512Mi
  ✅ +           memory: 1Gi
------------------------------------------------------------

============================================================
```

### 상세한 출력 (Verbose 모드)
```cmd
run.bat issues\sample_oom.json -v
```

또는
```cmd
run.bat issues\sample_oom.json --verbose
```

전체 AI 분석 내용을 포함한 상세한 출력을 보여줍니다.

## 📋 심각도 레벨

| 아이콘 | 심각도 | 설명 |
|--------|--------|------|
| 🔴 | CRITICAL | 즉시 조치 필요, 서비스 중단 상태 |
| 🟠 | HIGH | 빠른 조치 필요, 서비스 영향 있음 |
| 🟡 | MEDIUM | 계획된 조치 필요, 성능 저하 가능 |
| 🟢 | LOW | 모니터링 필요, 예방 차원 |

## 🔧 환경 설정

### .env 파일 설정

```env
# 필수: Google Gemini API 키
GOOGLE_API_KEY=your-api-key-here

# AI 모델 선택
MODEL_NAME=gemini-3-flash-preview

# 자동 승인 (true: 승인 프롬프트 건너뜀, false: 수동 승인)
AUTO_APPROVE=false

# Verbose 모드 (true: 항상 상세 출력, false: 간결한 출력)
VERBOSE=false
```

## 📝 실행 예제

### 1. OOM (Out of Memory) 이슈
```cmd
run.bat issues\sample_oom.json
```

**분석 내용:**
- 근본 원인: 메모리 제한 초과
- 해결책: 메모리 Limit 증설, 메모리 누수 점검, 알림 설정

### 2. 이미지 Pull 실패
```cmd
run.bat issues\sample_image_pull.json
```

**분석 내용:**
- 근본 원인: 레지스트리 인증 실패
- 해결책: Secret 생성, CI/CD 자동화, 알림 설정

### 3. CPU Throttling
```cmd
run.bat issues\sample_cpu_throttle.json
```

**분석 내용:**
- 근본 원인: CPU Limit 부족
- 해결책: CPU Limit 증설, VPA 도입, 모니터링 강화

## 🎯 해결책 구조

모든 분석 결과는 **3단계 해결책**을 제공합니다:

1. **즉시 조치** - 지금 당장 실행할 수 있는 빠른 해결 방법
2. **근본 해결** - 재발 방지를 위한 장기적 해결 방안
3. **모니터링** - 문제 예방을 위한 모니터링 및 알림 설정

## 💻 CLI 명령어

### 수동 실행
```cmd
cd agent\src
..\venv\Scripts\python.exe -m cli analyze ..\issues\sample_oom.json
```

### Verbose 모드 활성화
```cmd
cd agent\src
..\venv\Scripts\python.exe -m cli analyze ..\issues\sample_oom.json -v
```

### 가상환경 직접 사용
```cmd
cd agent
venv\Scripts\activate.bat
cd src
python -m cli analyze ..\issues\sample_oom.json
deactivate
```

## 🔍 출력 항목 설명

### 📋 이슈
분석 대상 Kubernetes 이슈의 에러 메시지

### 📦 리소스
문제가 발생한 Pod, Deployment, Job 등의 리소스 이름

### 🔴/🟠/🟡/🟢 심각도
이슈의 심각도 수준 (CRITICAL, HIGH, MEDIUM, LOW)

### 🔍 근본 원인
AI가 분석한 문제의 핵심 원인 (한 문장 요약)

### 💡 해결책
1. **즉시 조치** - 지금 바로 실행할 수 있는 해결 방법
2. **근본 해결** - 재발 방지를 위한 장기적 해결 방안
3. **모니터링** - 문제 예방을 위한 관찰 및 알림 설정

### ⚡ 실행 계획 (NEW!)
즉시 실행 가능한 `kubectl` 명령어를 제공합니다:
- 실제 리소스 이름과 네임스페이스가 포함됨
- 복사해서 바로 실행 가능
- 주석으로 명령어의 목적 설명

**예시:**
```bash
kubectl patch deployment api-server -n production \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value":"1Gi"}]'
```

### 📝 YAML 수정 (Diff) (NEW!)
변경이 필요한 YAML 부분을 diff 형식으로 표시합니다:
- ❌ (빨간색 `-`) - 삭제/변경 전 값
- ✅ (초록색 `+`) - 추가/변경 후 값
- 변경이 필요한 부분만 표시하여 명확함

**예시:**
```yaml
spec:
  template:
    spec:
      containers:
      - name: app
        resources:
          limits:
❌ -           memory: 512Mi
✅ +           memory: 1Gi
```

## 📊 비교: 기존 vs 개선된 출력

### 기존 (표 형식, 길고 복잡함)
```
해결책:
| 구분 | 조치 사항 | 명령어 및 상세 설명 |
| :--- | :--- | :--- |
| **단기 (즉시)** | **리소스 제한(Limits) 상향** | `resources.limits.memory`를... |
... (매우 긴 표)
```

### 개선됨 (간결하고 명확함)
```
💡 해결책:
   1. Deployment의 resources.limits.memory를 1Gi 이상으로 증설하세요.
   2. 애플리케이션의 메모리 누수 여부를 프로파일링하세요.
   3. 메모리 사용률 80% 초과 시 알림을 설정하세요.
```

## 🛠️ 문제 해결

### 출력이 여전히 길다면
프롬프트를 더 간결하게 수정:
```python
# src/dr_kube/prompts.py 수정
**주의**: 각 해결책은 한 줄로 핵심만 작성하세요.
```

### 한글이 깨진다면
```cmd
chcp 65001
run.bat issues\sample_oom.json
```

### Verbose 모드가 작동하지 않는다면
```cmd
# .env 파일에 추가
VERBOSE=true
```

## 📚 추가 자료

- 전체 설정 가이드: [WINDOWS_SETUP.md](./WINDOWS_SETUP.md)
- 빠른 시작: [QUICKSTART_KR.md](./QUICKSTART_KR.md)
- 프로젝트 개요: [README.md](./README.md)
