# Chaos Mesh 설치 가이드

## 🚀 ArgoCD + Helm을 통한 자동 설치

Chaos Mesh가 GitOps 방식으로 자동 설치되도록 구성되었습니다.

### 설치 방법

#### 방법 1: ArgoCD로 자동 설치 (권장)

```bash
# GitOps를 통한 자동 배포
kubectl apply -f chaos-mesh/Application.yaml
```

ArgoCD가 자동으로:
1. Chaos Mesh Helm Chart를 다운로드
2. `helm-values/chaos-mesh/values.yaml` 설정 적용
3. `chaos-mesh` 네임스페이스에 설치
4. 자동 동기화 및 복구 활성화

#### 방법 2: Helm으로 직접 설치

```bash
# Helm repo 추가
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update

# Chaos Mesh 설치
helm install chaos-mesh chaos-mesh/chaos-mesh \
  -n chaos-mesh \
  --create-namespace \
  -f helm-values/chaos-mesh/values.yaml
```

### 설치 확인

```bash
# 1. 네임스페이스 확인
kubectl get ns chaos-mesh

# 2. 파드 상태 확인
kubectl get pods -n chaos-mesh

# 예상 출력:
# NAME                                        READY   STATUS    RESTARTS   AGE
# chaos-controller-manager-xxx                1/1     Running   0          1m
# chaos-daemon-xxx                            1/1     Running   0          1m
# chaos-dashboard-xxx                         1/1     Running   0          1m
# chaos-dns-server-xxx                        1/1     Running   0          1m

# 3. CRD 확인
kubectl api-resources --api-group=chaos-mesh.org

# 예상 출력:
# NAME              SHORTNAMES   APIVERSION              NAMESPACED   KIND
# awschaos                       chaos-mesh.org/v1alpha1 true         AwsChaos
# podchaos                       chaos-mesh.org/v1alpha1 true         PodChaos
# networkchaos                   chaos-mesh.org/v1alpha1 true         NetworkChaos
# iochaos                        chaos-mesh.org/v1alpha1 true         IOChaos
# stresschaos                    chaos-mesh.org/v1alpha1 true         StressChaos
# ...

# 4. dr-kube에서 확인
cd agent-core
python -c "from langgraph_agent.tools import chaos; print('Chaos Mesh installed:', chaos.is_chaos_mesh_installed())"
```

### ArgoCD UI에서 확인

```bash
# ArgoCD UI 포트포워딩
kubectl port-forward svc/argocd-server -n argocd 8080:443

# 브라우저에서 접속
open https://localhost:8080
```

ArgoCD UI에서 `chaos-mesh` Application의 상태를 확인할 수 있습니다.

---

## 📊 Chaos Mesh Dashboard 접근

### 로컬 포트포워딩

```bash
kubectl port-forward svc/chaos-dashboard -n chaos-mesh 2333:2333
```

브라우저에서 http://localhost:2333 접속

### Ingress 설정 (선택)

Ingress를 통해 외부에서 접근하려면 `helm-values/chaos-mesh/values.yaml` 수정:

```yaml
dashboard:
  ingress:
    enabled: true
    annotations:
      kubernetes.io/ingress.class: nginx
      cert-manager.io/cluster-issuer: letsencrypt-prod
    hosts:
      - host: chaos-mesh.yourdomain.com
        paths:
          - path: /
            pathType: Prefix
    tls:
      - secretName: chaos-mesh-tls
        hosts:
          - chaos-mesh.yourdomain.com
```

---

## 🔧 설정 커스터마이징

### Container Runtime 변경

Docker 사용 시 `helm-values/chaos-mesh/values.yaml` 수정:

```yaml
chaosDaemon:
  runtime: docker
  socketPath: /var/run/docker.sock
```

### 특정 네임스페이스만 대상으로 제한

```yaml
enableFilterNamespace: true
targetNamespace: default,dev,staging
```

### 실험 타입 제한

특정 카오스 타입만 활성화:

```yaml
enablePodChaos: true
enableNetworkChaos: true
enableIOChaos: false
enableStressChaos: true
enableTimeChaos: false
```

### Prometheus 모니터링 활성화

```yaml
prometheus:
  serviceMonitor:
    enabled: true
    interval: 30s
```

---

## 🎯 dr-kube와 함께 사용

### 1. Chaos Mesh 설치 확인

```bash
cd agent-core
python -c "from langgraph_agent.tools import chaos; print(chaos.is_chaos_mesh_installed())"
```

### 2. CLI로 카오스 실험

```bash
# Memory Stress 실험
python -m langgraph_agent.cli \
  --chaos memory-stress \
  --chaos-label app=test-app \
  --chaos-duration 2m

# Pod Kill 실험
python -m langgraph_agent.cli \
  --chaos pod-kill \
  --chaos-label app=nginx \
  --chaos-duration 1m
```

### 3. Python 코드로 사용

```python
from langgraph_agent.tools.chaos import ChaosExperiment

chaos = ChaosExperiment(namespace="default")

# Memory Stress
chaos.create_stress_chaos(
    name="test-memory",
    label_selector={"app": "myapp"},
    memory="256MB",
    duration="1m"
)
```

### 4. 복원력 통합 테스트

```bash
# 1. 카오스 발생
python -m langgraph_agent.cli --chaos memory-stress

# 2. dr-kube로 자동 복구
python -m langgraph_agent.cli -n default
```

---

## 🗑️ 제거

### ArgoCD로 제거

```bash
kubectl delete -f chaos-mesh/Application.yaml
```

### Helm으로 제거

```bash
helm uninstall chaos-mesh -n chaos-mesh
kubectl delete namespace chaos-mesh
```

### CRD 완전 제거

```bash
kubectl delete crd $(kubectl get crd | grep chaos-mesh.org | awk '{print $1}')
```

---

## 📚 참고 자료

- [Chaos Mesh 공식 문서](https://chaos-mesh.org/docs/)
- [Helm Chart 설정](https://github.com/chaos-mesh/chaos-mesh/tree/master/helm/chaos-mesh)
- [dr-kube Chaos 가이드](../agent-core/CHAOS_ENGINEERING.md)

---

## 🔍 트러블슈팅

### 파드가 시작하지 않음

```bash
# 로그 확인
kubectl logs -n chaos-mesh <pod-name>

# 이벤트 확인
kubectl get events -n chaos-mesh
```

### CRD 설치 오류

```bash
# CRD 상태 확인
kubectl get crd | grep chaos-mesh

# 수동 설치
kubectl apply -f https://mirrors.chaos-mesh.org/latest/crd.yaml
```

### Runtime Socket 오류

컨테이너 런타임에 맞게 설정 변경:

- **containerd**: `/run/containerd/containerd.sock`
- **docker**: `/var/run/docker.sock`
- **cri-o**: `/var/run/crio/crio.sock`

---

## ✅ 설치 완료 체크리스트

- [ ] ArgoCD Application 배포됨
- [ ] chaos-mesh 네임스페이스 생성됨
- [ ] 모든 파드가 Running 상태
- [ ] CRD가 설치됨
- [ ] Dashboard 접근 가능
- [ ] dr-kube에서 감지됨

모든 항목이 체크되면 카오스 실험을 시작할 수 있습니다! 🎉
