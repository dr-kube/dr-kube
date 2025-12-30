# 🎭 Chaos Engineering with Chaos Mesh

dr-kube에 Chaos Mesh 통합으로 강력한 카오스 엔지니어링 기능이 추가되었습니다!

## 🚀 빠른 시작

### 1. Chaos Mesh 설치

#### 방법 1: Helm으로 설치 (권장)

```bash
# Helm repo 추가
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update

# Chaos Mesh 설치
helm install chaos-mesh chaos-mesh/chaos-mesh \
  -n chaos-mesh \
  --create-namespace \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock
```

#### 방법 2: kubectl로 설치

```bash
curl -sSL https://mirrors.chaos-mesh.org/latest/install.sh | bash
```

#### 방법 3: Kind 클러스터용

```bash
curl -sSL https://mirrors.chaos-mesh.org/latest/install.sh | bash -s -- --local kind
```

### 2. 설치 확인

```bash
# Chaos Mesh 파드 확인
kubectl get pods -n chaos-mesh

# CRD 확인
kubectl api-resources --api-group=chaos-mesh.org

# dr-kube에서 확인
python -c "from langgraph_agent.tools import chaos; print(chaos.is_chaos_mesh_installed())"
```

---

## 💥 카오스 실험 타입

### 1. **Pod Chaos** - 파드 장애
- `pod-kill`: 파드 삭제
- `pod-failure`: 파드 사용 불가능하게 만들기
- `container-kill`: 특정 컨테이너만 삭제

### 2. **Network Chaos** - 네트워크 장애
- `delay`: 네트워크 지연
- `loss`: 패킷 손실
- `corrupt`: 패킷 손상
- `duplicate`: 패킷 중복
- `partition`: 네트워크 분할

### 3. **Stress Chaos** - 리소스 부하
- `memory`: 메모리 스트레스
- `cpu`: CPU 스트레스

### 4. **IO Chaos** - I/O 장애
- `latency`: I/O 지연
- `fault`: I/O 오류
- `attrOverride`: 파일 속성 변경

### 5. **Time Chaos** - 시간 왜곡
- 시간 앞당기기/뒤로 미루기

---

## 🎯 사용 방법

### 방법 1: CLI로 실행

```bash
# Pod Kill 실험
python -m langgraph_agent.cli \
  --chaos pod-kill \
  --namespace default \
  --chaos-label app=nginx \
  --chaos-duration 1m

# Memory Stress 실험
python -m langgraph_agent.cli \
  --chaos memory-stress \
  --chaos-label app=myapp \
  --chaos-duration 2m

# Network Delay 실험
python -m langgraph_agent.cli \
  --chaos network-delay \
  --chaos-label app=api \
  --chaos-duration 30s
```

### 방법 2: 예제 스크립트

```bash
./examples_chaos.py
```

스크립트에서 원하는 시나리오의 주석을 해제하고 실행:

```python
# 시나리오 선택
scenario_1_pod_kill()           # Pod Kill
scenario_2_memory_stress()      # Memory Stress  
scenario_3_network_delay()      # Network Delay
scenario_7_resilience_test()    # 통합 테스트 (권장)
```

### 방법 3: Python 코드로

```python
from langgraph_agent.tools.chaos import ChaosExperiment

# Chaos 인스턴스 생성
chaos = ChaosExperiment(namespace="default")

# Pod Kill 실험
chaos.create_pod_kill_chaos(
    name="my-pod-kill-test",
    label_selector={"app": "nginx"},
    duration="30s",
    mode="one"
)

# Memory Stress 실험
chaos.create_stress_chaos(
    name="my-memory-test",
    label_selector={"app": "myapp"},
    memory="256MB",
    duration="1m"
)

# Network Delay 실험
chaos.create_network_delay_chaos(
    name="my-network-test",
    label_selector={"app": "api"},
    latency="100ms",
    duration="30s"
)
```

### 방법 4: 간편 함수

```python
from langgraph_agent.tools.chaos import (
    quick_pod_kill,
    quick_memory_stress,
    quick_network_delay
)

# Pod Kill
quick_pod_kill("default", {"app": "nginx"}, "30s")

# Memory Stress
quick_memory_stress("default", {"app": "test"}, "256MB", "1m")

# Network Delay
quick_network_delay("default", {"app": "api"}, "100ms", "30s")
```

---

## 🎬 실전 시나리오

### 시나리오 1: OOM 테스트 + 자동 복구

```bash
# 1. Memory Stress로 OOM 유발
python -m langgraph_agent.cli \
  --chaos memory-stress \
  --chaos-label app=test-app \
  --chaos-duration 2m

# 2. dr-kube로 자동 감지 및 복구
python -m langgraph_agent.cli -n default

# 예상 결과:
# - OOMKilled 감지
# - 메모리 리소스 증가 제안
# - 승인 후 자동 수정
```

### 시나리오 2: Pod Kill + 복원력 테스트

```bash
# 1. Pod Kill 실험
python -m langgraph_agent.cli \
  --chaos pod-kill \
  --chaos-label app=nginx \
  --chaos-duration 1m

# 2. 파드 재시작 모니터링
kubectl get pods -n default -w

# 예상 결과:
# - 파드 자동 재시작
# - ReplicaSet이 새 파드 생성
# - 서비스 연속성 유지
```

### 시나리오 3: Network Delay + 성능 테스트

```bash
# 1. Network Delay 주입
python -m langgraph_agent.cli \
  --chaos network-delay \
  --chaos-label app=api \
  --chaos-duration 1m

# 2. API 응답 시간 확인
curl -w "@curl-format.txt" -o /dev/null -s http://your-api/endpoint

# 예상 결과:
# - 응답 시간 증가
# - 타임아웃 발생 가능
# - 재시도 로직 작동 확인
```

---

## 📊 실험 관리

### 실행 중인 실험 확인

```bash
# 모든 Chaos 실험 조회
kubectl get podchaos,networkchaos,stresschaos,iochaos -A

# 특정 타입만 조회
kubectl get podchaos -n default
kubectl get networkchaos -n default

# 상세 정보
kubectl describe podchaos <name> -n default
```

### 실험 중단

```bash
# 특정 실험 삭제
kubectl delete podchaos <name> -n default

# 모든 실험 삭제
kubectl delete podchaos --all -n default
kubectl delete networkchaos --all -n default
kubectl delete stresschaos --all -n default
```

### Python으로 관리

```python
from langgraph_agent.tools.chaos import ChaosExperiment

chaos = ChaosExperiment(namespace="default")

# 실험 목록
experiments = chaos.list_chaos_experiments()
for exp in experiments:
    print(f"{exp['type']}: {exp['name']}")

# 실험 삭제
chaos.delete_chaos("podchaos", "my-test")
```

---

## 🛡️ 안전 가이드

### 1. 개발 환경에서 먼저 테스트

```bash
# 개발 네임스페이스에서
python -m langgraph_agent.cli \
  --chaos pod-kill \
  --namespace dev \
  --chaos-label app=test
```

### 2. 짧은 지속 시간으로 시작

```bash
# 30초로 시작
--chaos-duration 30s

# 문제 없으면 점진적으로 증가
--chaos-duration 1m
--chaos-duration 5m
```

### 3. 라벨 선택자 정확하게 지정

```bash
# ❌ 너무 광범위
--chaos-label tier=backend

# ✅ 구체적으로
--chaos-label app=test-service,version=v1
```

### 4. 프로덕션 환경 주의사항

- ⚠️ 업무 시간 외 실행
- ⚠️ 모니터링 시스템 준비
- ⚠️ 롤백 계획 수립
- ⚠️ 팀원들에게 사전 공지
- ⚠️ 중요한 서비스는 제외

---

## 🎓 Best Practices

### 1. 점진적 접근

```
1주차: Pod Kill (1개 파드)
2주차: Pod Kill (여러 파드)
3주차: Memory Stress
4주차: Network Chaos
5주차: 복합 시나리오
```

### 2. 가설 수립

실험 전에 질문하기:
- "파드가 삭제되면 서비스가 계속 작동하나?"
- "메모리가 부족하면 자동으로 복구되나?"
- "네트워크 지연 시 재시도가 작동하나?"

### 3. 메트릭 수집

```bash
# 실험 전
kubectl top pods -n default

# 실험 중
kubectl top pods -n default -w

# 실험 후
kubectl get events -n default
```

### 4. 문서화

```markdown
## 실험: Pod Kill Test
- 날짜: 2024-12-26
- 대상: nginx 파드
- 지속 시간: 1분
- 결과: 파드 자동 재시작, 서비스 중단 없음
- 개선 사항: ReplicaSet을 3개로 증가
```

---

## 📚 참고 자료

- [Chaos Mesh 공식 문서](https://chaos-mesh.org/docs/)
- [Chaos Engineering 원칙](https://principlesofchaos.org/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/cluster-administration/)

---

## 🤝 통합 워크플로우

```bash
# 1. Chaos 실험으로 문제 발생
python -m langgraph_agent.cli --chaos memory-stress

# 2. dr-kube로 자동 감지
python -m langgraph_agent.cli -n default

# 3. 자동 수정 승인
# (대화형으로 y 입력 또는 --auto-approve)

# 4. 복구 확인
kubectl get pods -n default
```

이것이 **dr-kube + Chaos Mesh**의 진정한 힘입니다! 🚀

---

**Happy Chaos Engineering! 💥**
