# 🎭 Chaos Mesh 통합 완료!

## ✅ 구현 완료

### 1. ArgoCD Application (`chaos-mesh/Application.yaml`)
- ✅ Chaos Mesh Helm Chart 자동 배포
- ✅ GitOps 방식 설정
- ✅ 자동 동기화 및 복구 활성화

### 2. Helm Values (`helm-values/chaos-mesh/values.yaml`)
- ✅ Container Runtime: containerd 설정
- ✅ Dashboard 활성화
- ✅ 리소스 제한 설정
- ✅ 보안 설정 포함
- ✅ 타임존: Asia/Seoul

### 3. GitOps 통합 (`gitops/values.yaml`)
- ✅ ArgoCD App of Apps에 Chaos Mesh 추가
- ✅ 자동 프로비저닝 설정

### 4. 설치 가이드 (`chaos-mesh/INSTALL.md`)
- ✅ ArgoCD 설치 방법
- ✅ Helm 직접 설치 방법
- ✅ 설치 확인 절차
- ✅ Dashboard 접근 방법
- ✅ 트러블슈팅 가이드

---

## 🚀 빠른 시작

### 1. ArgoCD로 설치 (권장)

```bash
# Application 배포
kubectl apply -f chaos-mesh/Application.yaml

# 설치 확인
kubectl get pods -n chaos-mesh
kubectl api-resources --api-group=chaos-mesh.org
```

### 2. dr-kube에서 확인

```bash
cd agent-core
python -c "from langgraph_agent.tools import chaos; print('Chaos Mesh installed:', chaos.is_chaos_mesh_installed())"
```

### 3. Dashboard 접근

```bash
kubectl port-forward svc/chaos-dashboard -n chaos-mesh 2333:2333
# http://localhost:2333
```

### 4. 첫 카오스 실험

```bash
# CLI로 실험
cd agent-core
python -m langgraph_agent.cli --chaos pod-kill --chaos-label app=nginx

# 또는 예제 스크립트
./examples_chaos.py
```

---

## 📁 프로젝트 구조

```
dr-kube/
├── chaos-mesh/
│   ├── Application.yaml      # ArgoCD Application
│   └── INSTALL.md            # 설치 가이드
├── helm-values/
│   └── chaos-mesh/
│       └── values.yaml       # Helm 설정
├── gitops/
│   └── values.yaml          # App of Apps (Chaos Mesh 추가됨)
└── agent-core/
    ├── langgraph_agent/
    │   └── tools/
    │       └── chaos.py      # Chaos Mesh 통합 도구
    ├── examples_chaos.py     # 카오스 실험 예제
    └── CHAOS_ENGINEERING.md  # 상세 가이드
```

---

## 🎯 통합 워크플로우

```
1. GitOps 배포
   └─> kubectl apply -f chaos-mesh/Application.yaml

2. ArgoCD가 자동으로
   ├─> Helm Chart 다운로드
   ├─> values.yaml 적용
   └─> chaos-mesh 네임스페이스에 설치

3. dr-kube에서 사용
   ├─> CLI로 카오스 실험
   ├─> Python 코드로 실험
   └─> 자동 감지 및 복구 테스트

4. 복원력 테스트
   └─> 카오스 발생 → 자동 감지 → 자동 복구
```

---

## 💡 주요 기능

### Container Runtime 지원
- ✅ containerd (기본)
- ✅ docker
- ✅ cri-o

### 카오스 실험 타입
- ✅ Pod Chaos (kill, failure)
- ✅ Network Chaos (delay, loss, corrupt)
- ✅ Stress Chaos (memory, cpu)
- ✅ IO Chaos (latency, fault)
- ✅ Time Chaos
- ✅ DNS Chaos
- ✅ HTTP Chaos

### 보안 기능
- ✅ RBAC 설정
- ✅ Security Mode
- ✅ Namespace 격리
- ✅ 권한 제어

---

## 📊 모니터링

### Dashboard
```bash
kubectl port-forward svc/chaos-dashboard -n chaos-mesh 2333:2333
```

### Prometheus (선택)
values.yaml에서 활성화:
```yaml
prometheus:
  serviceMonitor:
    enabled: true
```

---

## 🔧 커스터마이징

### Docker 사용 시
```yaml
chaosDaemon:
  runtime: docker
  socketPath: /var/run/docker.sock
```

### 특정 네임스페이스만 대상
```yaml
enableFilterNamespace: true
targetNamespace: default,dev,staging
```

### Ingress 활성화
```yaml
dashboard:
  ingress:
    enabled: true
    hosts:
      - host: chaos-mesh.yourdomain.com
```

---

## 📚 문서

- [설치 가이드](chaos-mesh/INSTALL.md)
- [Chaos Engineering 가이드](agent-core/CHAOS_ENGINEERING.md)
- [dr-kube CLI 사용법](agent-core/README.md)

---

## ✅ 다음 단계

1. **설치**
   ```bash
   kubectl apply -f chaos-mesh/Application.yaml
   ```

2. **확인**
   ```bash
   kubectl get pods -n chaos-mesh
   ```

3. **테스트**
   ```bash
   cd agent-core
   ./examples_chaos.py
   ```

4. **통합**
   ```bash
   # 카오스 발생
   python -m langgraph_agent.cli --chaos memory-stress
   
   # 자동 복구
   python -m langgraph_agent.cli -n default
   ```

---

**Chaos Engineering with GitOps! 🎉**

이제 시스템의 복원력을 체계적으로 테스트할 수 있습니다!
