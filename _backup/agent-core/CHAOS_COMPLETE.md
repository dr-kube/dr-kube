# 🎉 Chaos Engineering 기능 추가 완료!

## ✅ 구현 완료

### 1. Chaos Mesh 통합 도구 (`tools/chaos.py`)
- ✅ ChaosExperiment 클래스
- ✅ 6가지 카오스 실험 타입
  - Pod Kill
  - Memory Stress
  - CPU Stress
  - Network Delay
  - Network Packet Loss
  - I/O Delay
- ✅ 실험 관리 (생성, 삭제, 조회)
- ✅ 간편 함수 (quick_pod_kill, quick_memory_stress 등)

### 2. CLI 통합
```bash
# CLI에 --chaos 옵션 추가
python -m langgraph_agent.cli --chaos pod-kill
python -m langgraph_agent.cli --chaos memory-stress --chaos-duration 2m
python -m langgraph_agent.cli --chaos network-delay --chaos-label app=nginx
```

### 3. 예제 스크립트 (`examples_chaos.py`)
- 7가지 시나리오 포함
- 사용자 친화적 설명
- 실행 예제 및 확인 명령어 제공

### 4. 완전한 문서 (`CHAOS_ENGINEERING.md`)
- Chaos Mesh 설치 가이드
- 모든 실험 타입 설명
- 실전 시나리오
- Best Practices
- 안전 가이드

---

## 🚀 사용 방법

### 기본 사용

```bash
# 1. Chaos Mesh 설치 (한 번만)
helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace

# 2. CLI로 카오스 실험
python -m langgraph_agent.cli --chaos pod-kill --chaos-label app=nginx

# 3. 예제 스크립트
./examples_chaos.py
```

### Python 코드

```python
from langgraph_agent.tools.chaos import ChaosExperiment

chaos = ChaosExperiment(namespace="default")

# Pod Kill 실험
chaos.create_pod_kill_chaos(
    name="test-pod-kill",
    label_selector={"app": "nginx"},
    duration="30s"
)
```

---

## 💡 핵심 시나리오: 복원력 통합 테스트

```bash
# 1. Memory Stress로 OOM 유발
python -m langgraph_agent.cli \
  --chaos memory-stress \
  --chaos-label app=test-app \
  --chaos-duration 2m

# 2. dr-kube로 자동 감지 및 복구
python -m langgraph_agent.cli -n default

# 결과: 
# - OOMKilled 자동 감지 ✅
# - 메모리 증가 제안 ✅
# - 자동 수정 실행 ✅
# - 시스템 복원 ✅
```

이것이 **dr-kube + Chaos Mesh**의 힘입니다! 💪

---

## 📁 새로 추가된 파일

```
agent-core/
├── langgraph_agent/
│   └── tools/
│       └── chaos.py           # 🆕 Chaos Mesh 통합 도구
├── examples_chaos.py          # 🆕 카오스 실험 예제
├── CHAOS_ENGINEERING.md       # 🆕 상세 가이드
└── cli.py                     # 업데이트: --chaos 옵션 추가
```

---

## 🎯 다음 단계

1. **Chaos Mesh 설치**
   ```bash
   helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace
   ```

2. **첫 실험 실행**
   ```bash
   ./examples_chaos.py
   ```

3. **문서 읽기**
   - [CHAOS_ENGINEERING.md](CHAOS_ENGINEERING.md)

4. **통합 테스트**
   - 카오스 발생 → dr-kube 자동 복구

---

## 🎓 카오스 엔지니어링 원칙

1. **가설 수립**: "파드가 삭제되면 서비스가 계속 작동할 것이다"
2. **실험 설계**: Pod Kill chaos 30초
3. **실행**: CLI로 실험 시작
4. **관찰**: 파드 재시작 확인
5. **학습**: 복원 시간 측정, 개선점 도출

---

## 📊 지원하는 카오스 타입

| 타입 | 설명 | CLI 명령어 |
|------|------|-----------|
| pod-kill | 파드 삭제 | `--chaos pod-kill` |
| memory-stress | 메모리 부하 | `--chaos memory-stress` |
| cpu-stress | CPU 부하 | `--chaos cpu-stress` |
| network-delay | 네트워크 지연 | `--chaos network-delay` |
| network-loss | 패킷 손실 | `--chaos network-loss` |
| io-delay | I/O 지연 | `--chaos io-delay` |

---

**Happy Chaos Engineering! 💥**

카오스 실험으로 시스템의 복원력을 강화하세요!
