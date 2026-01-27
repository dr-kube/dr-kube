# Kubernetes 장애 샘플 이슈

## 📋 전체 샘플 목록 (11개)

### 🔴 리소스 관련

#### 1. OOM (Out of Memory)
```cmd
.\run.bat issues\sample_oom.json
```
**증상:** CrashLoopBackOff
**원인:** 메모리 512Mi 초과
**해결:** 메모리 Limit 1Gi로 증설

---

#### 2. CPU Throttling
```cmd
.\run.bat issues\sample_cpu_throttle.json
```
**증상:** 성능 저하
**원인:** CPU Limit 500m 부족
**해결:** CPU Limit 1000m으로 증설

---

### ⚙️ 설정/구성 관련

#### 3. 이미지 Pull 실패
```cmd
.\run.bat issues\sample_image_pull.json
```
**증상:** ImagePullBackOff
**원인:** 프라이빗 레지스트리 인증 실패
**해결:** imagePullSecrets 추가

---

#### 4. ConfigMap 누락
```cmd
.\run.bat issues\sample_configmap_missing.json
```
**증상:** CreateContainerConfigError
**원인:** ConfigMap 'app-config' 존재하지 않음
**해결:** ConfigMap 생성 또는 optional 설정

---

#### 5. PVC Pending
```cmd
.\run.bat issues\sample_pvc_pending.json
```
**증상:** PersistentVolumeClaim Pending
**원인:** StorageClass 누락
**해결:** StorageClass 생성 또는 PV 수동 바인딩

---

### 💚 헬스체크 관련

#### 6. Liveness Probe 실패
```cmd
.\run.bat issues\sample_liveness_probe_fail.json
```
**증상:** 지속적인 재시작
**원인:** 헬스체크 503 응답
**해결:** initialDelaySeconds 증가 또는 애플리케이션 수정

---

### 🌐 네트워크 관련

#### 7. 네트워크 연결 실패
```cmd
.\run.bat issues\sample_network_policy.json
```
**증상:** Service Connection Timeout
**원인:** NetworkPolicy가 트래픽 차단
**해결:** NetworkPolicy 규칙 수정

---

#### 8. DNS 해석 실패
```cmd
.\run.bat issues\sample_dns_resolution.json
```
**증상:** Name resolution failed
**원인:** CoreDNS Pod 비정상
**해결:** CoreDNS 재시작 및 메모리 증설

---

### 📍 스케줄링/권한 관련

#### 9. 노드 스케줄링 실패
```cmd
.\run.bat issues\sample_node_not_ready.json
```
**증상:** Pod stuck in Pending
**원인:** 사용 가능한 노드 부족
**해결:** 노드 추가 또는 리소스 재조정

---

#### 10. RBAC 권한 부족
```cmd
.\run.bat issues\sample_rbac_permission.json
```
**증상:** Forbidden: insufficient permissions
**원인:** ServiceAccount에 pods 권한 없음
**해결:** Role 및 RoleBinding 생성

---

### 💥 애플리케이션 관련

#### 11. 앱 크래시
```cmd
.\run.bat issues\sample_app_crash.json
```
**증상:** CrashLoopBackOff
**원인:** 환경 변수 누락, DB 연결 실패
**해결:** 환경 변수 설정 및 의존성 확인

---

## 🎯 카테고리별 빠른 실행

### 모든 리소스 이슈
```cmd
.\run.bat issues\sample_oom.json
.\run.bat issues\sample_cpu_throttle.json
```

### 모든 설정 이슈
```cmd
.\run.bat issues\sample_image_pull.json
.\run.bat issues\sample_configmap_missing.json
.\run.bat issues\sample_pvc_pending.json
```

### 모든 네트워크 이슈
```cmd
.\run.bat issues\sample_network_policy.json
.\run.bat issues\sample_dns_resolution.json
```

### 모든 권한 이슈
```cmd
.\run.bat issues\sample_node_not_ready.json
.\run.bat issues\sample_rbac_permission.json
```

---

## 📖 이슈 파일 구조

각 이슈 파일은 다음과 같은 형식입니다:

```json
{
  "id": "issue-001",
  "type": "pod_crash",
  "namespace": "production",
  "resource": "api-server-7d4f8b9c5-xyz",
  "error_message": "CrashLoopBackOff",
  "logs": [
    "2026-01-24T10:00:00Z Error: OOMKilled",
    "..."
  ],
  "timestamp": "2026-01-24T10:00:00Z"
}
```

---

## 🔍 AI 분석 결과

각 샘플에 대해 AI가 제공하는 정보:

1. **📋 이슈**: 에러 메시지
2. **📦 리소스**: 영향받은 리소스
3. **🔴/🟠/🟡/🟢 심각도**: Critical/High/Medium/Low
4. **🔍 근본 원인**: 한 문장 요약
5. **💡 해결책**: 3단계 (즉시/근본/모니터링)
6. **⚡ 실행 계획**: kubectl 명령어
7. **📝 YAML Diff**: Before/After

---

## 💡 실전 활용

### 학습용
- 각 샘플을 실행해보고 AI 분석 결과 확인
- kubectl 명령어 학습
- YAML 수정 방법 학습

### 테스트용
- 실제 K8S 장애와 유사한 샘플 선택
- AI 제안 명령어를 테스트 환경에 적용
- 결과 확인 및 학습

---

**더 자세한 정보는 [README_KR.md](../README_KR.md)를 참고하세요.**
