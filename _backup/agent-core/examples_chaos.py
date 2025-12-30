#!/usr/bin/env python3
"""
Chaos Engineering 실험 예제
다양한 카오스 시나리오를 보여줍니다.
"""
import sys
import time
from langgraph_agent.tools.chaos import (
    ChaosExperiment,
    check_chaos_mesh_prerequisites,
    quick_pod_kill,
    quick_memory_stress,
    quick_network_delay
)


def check_prerequisites():
    """사전 조건 확인"""
    print("🔍 Chaos Mesh 설치 확인 중...\n")
    success, message = check_chaos_mesh_prerequisites()
    print(message)
    return success


def scenario_1_pod_kill():
    """
    시나리오 1: Pod Kill - 파드 랜덤 삭제
    
    목적: 파드가 삭제되었을 때 자동 복구되는지 확인
    """
    print("\n" + "=" * 60)
    print("시나리오 1: Pod Kill Chaos")
    print("=" * 60)
    print("목적: 파드 복원력 테스트")
    print()
    
    chaos = ChaosExperiment(namespace="default")
    
    # app=nginx 라벨을 가진 파드 중 하나를 30초 동안 반복 삭제
    success, message = chaos.create_pod_kill_chaos(
        name="test-pod-kill",
        label_selector={"app": "nginx"},
        duration="30s",
        mode="one"
    )
    
    print(message)
    
    if success:
        print("\n💡 다음 명령어로 실험 상태를 확인하세요:")
        print("   kubectl get podchaos test-pod-kill -n default")
        print("\n🔄 파드가 재시작되는지 확인:")
        print("   kubectl get pods -n default -w")
        print("\n🗑️ 실험 종료:")
        print("   kubectl delete podchaos test-pod-kill -n default")


def scenario_2_memory_stress():
    """
    시나리오 2: Memory Stress - 메모리 부하
    
    목적: 메모리 부족 상황에서 애플리케이션 동작 확인
    """
    print("\n" + "=" * 60)
    print("시나리오 2: Memory Stress Chaos")
    print("=" * 60)
    print("목적: OOM 상황 시뮬레이션 및 자동 복구 테스트")
    print()
    
    chaos = ChaosExperiment(namespace="default")
    
    # 256MB 메모리 스트레스를 1분간 적용
    success, message = chaos.create_stress_chaos(
        name="test-memory-stress",
        label_selector={"app": "myapp"},
        memory="256MB",
        duration="1m"
    )
    
    print(message)
    
    if success:
        print("\n💡 메모리 사용량 확인:")
        print("   kubectl top pods -n default")
        print("\n🔄 OOMKilled 발생 확인:")
        print("   kubectl get pods -n default -w")
        print("\n⏱️ 1분 후 자동으로 종료됩니다")


def scenario_3_network_delay():
    """
    시나리오 3: Network Delay - 네트워크 지연
    
    목적: 네트워크 지연 상황에서 애플리케이션 동작 확인
    """
    print("\n" + "=" * 60)
    print("시나리오 3: Network Delay Chaos")
    print("=" * 60)
    print("목적: 네트워크 지연에 대한 애플리케이션 복원력 테스트")
    print()
    
    chaos = ChaosExperiment(namespace="default")
    
    # 100ms 네트워크 지연을 30초간 적용
    success, message = chaos.create_network_delay_chaos(
        name="test-network-delay",
        label_selector={"app": "api"},
        latency="100ms",
        duration="30s"
    )
    
    print(message)
    
    if success:
        print("\n💡 네트워크 지연 확인:")
        print("   # 파드 내부에서")
        print("   kubectl exec -it <pod-name> -- ping google.com")
        print("\n⏱️ 30초 후 자동으로 종료됩니다")


def scenario_4_network_loss():
    """
    시나리오 4: Network Packet Loss - 패킷 손실
    
    목적: 패킷 손실 상황에서 재시도 로직 확인
    """
    print("\n" + "=" * 60)
    print("시나리오 4: Network Packet Loss Chaos")
    print("=" * 60)
    print("목적: 패킷 손실 시 재시도 메커니즘 테스트")
    print()
    
    chaos = ChaosExperiment(namespace="default")
    
    # 25% 패킷 손실을 30초간 적용
    success, message = chaos.create_network_loss_chaos(
        name="test-packet-loss",
        label_selector={"app": "frontend"},
        loss="25",
        duration="30s"
    )
    
    print(message)
    
    if success:
        print("\n💡 패킷 손실 확인:")
        print("   kubectl logs -f <pod-name> -n default")
        print("\n⏱️ 30초 후 자동으로 종료됩니다")


def scenario_5_cpu_stress():
    """
    시나리오 5: CPU Stress - CPU 부하
    
    목적: CPU 부하 상황에서 성능 저하 확인
    """
    print("\n" + "=" * 60)
    print("시나리오 5: CPU Stress Chaos")
    print("=" * 60)
    print("목적: CPU 부하 시 애플리케이션 성능 테스트")
    print()
    
    chaos = ChaosExperiment(namespace="default")
    
    # 1 CPU 코어 부하를 1분간 적용
    success, message = chaos.create_stress_chaos(
        name="test-cpu-stress",
        label_selector={"app": "backend"},
        cpu="1",
        duration="1m"
    )
    
    print(message)
    
    if success:
        print("\n💡 CPU 사용량 확인:")
        print("   kubectl top pods -n default")
        print("\n⏱️ 1분 후 자동으로 종료됩니다")


def scenario_6_io_delay():
    """
    시나리오 6: I/O Delay - 디스크 I/O 지연
    
    목적: 디스크 I/O 지연 상황 확인
    """
    print("\n" + "=" * 60)
    print("시나리오 6: I/O Delay Chaos")
    print("=" * 60)
    print("목적: 디스크 I/O 지연 시 애플리케이션 동작 테스트")
    print()
    
    chaos = ChaosExperiment(namespace="default")
    
    # 100ms I/O 지연을 30초간 적용
    success, message = chaos.create_io_delay_chaos(
        name="test-io-delay",
        label_selector={"app": "database"},
        delay="100ms",
        duration="30s",
        path="/var/lib/data"
    )
    
    print(message)
    
    if success:
        print("\n💡 I/O 성능 확인:")
        print("   kubectl exec -it <pod-name> -- dd if=/dev/zero of=/tmp/test bs=1M count=100")
        print("\n⏱️ 30초 후 자동으로 종료됩니다")


def scenario_7_resilience_test():
    """
    시나리오 7: 복원력 통합 테스트
    
    목적: 카오스 발생 → dr-kube 자동 감지 → 자동 복구 전체 흐름
    """
    print("\n" + "=" * 60)
    print("시나리오 7: 복원력 통합 테스트")
    print("=" * 60)
    print("목적: 카오스 엔지니어링 + dr-kube 자동 복구")
    print()
    
    print("1️⃣  메모리 스트레스 발생...")
    success, message = quick_memory_stress(
        namespace="default",
        label_selector={"app": "test-app"},
        memory="512MB",
        duration="2m"
    )
    print(f"   {message}")
    
    if success:
        print("\n2️⃣  dr-kube 에이전트 실행으로 자동 복구 확인:")
        print("   python -m langgraph_agent.cli -n default")
        print("\n3️⃣  예상 동작:")
        print("   - OOMKilled 감지")
        print("   - 메모리 리소스 증가 제안")
        print("   - 승인 후 자동 수정")
        print("   - 파드 정상화")


def list_active_experiments():
    """실행 중인 실험 목록"""
    print("\n" + "=" * 60)
    print("실행 중인 Chaos 실험")
    print("=" * 60)
    
    chaos = ChaosExperiment(namespace="default")
    experiments = chaos.list_chaos_experiments()
    
    if not experiments:
        print("❌ 실행 중인 실험이 없습니다.\n")
        return
    
    for exp in experiments:
        print(f"\n📊 {exp['type']}: {exp['name']}")
        print(f"   네임스페이스: {exp['namespace']}")
        print(f"   생성 시간: {exp['created']}")
        
        spec = exp['spec']
        if 'duration' in spec:
            print(f"   지속 시간: {spec['duration']}")
        if 'selector' in spec:
            labels = spec['selector'].get('labelSelectors', {})
            print(f"   대상: {labels}")


def cleanup_all():
    """모든 실험 정리"""
    print("\n" + "=" * 60)
    print("모든 Chaos 실험 정리")
    print("=" * 60)
    
    chaos = ChaosExperiment(namespace="default")
    experiments = chaos.list_chaos_experiments()
    
    if not experiments:
        print("❌ 정리할 실험이 없습니다.\n")
        return
    
    for exp in experiments:
        print(f"🗑️  {exp['type']}/{exp['name']} 삭제 중...")
        success, message = chaos.delete_chaos(exp['type'], exp['name'])
        print(f"   {message}")


def main():
    """메인 함수"""
    print("""
╔══════════════════════════════════════════════════════════╗
║          Chaos Engineering 실험 예제                    ║
║          Powered by Chaos Mesh                           ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # 사전 조건 확인
    if not check_prerequisites():
        print("\n⚠️  Chaos Mesh를 설치한 후 다시 실행하세요.")
        return 1
    
    print("""
사용 가능한 시나리오:
1. Pod Kill - 파드 랜덤 삭제
2. Memory Stress - 메모리 부하
3. Network Delay - 네트워크 지연
4. Network Packet Loss - 패킷 손실
5. CPU Stress - CPU 부하
6. I/O Delay - 디스크 I/O 지연
7. 복원력 통합 테스트 (권장)
8. 실행 중인 실험 목록
9. 모든 실험 정리

⚠️  주의: 프로덕션 환경에서는 신중하게 사용하세요!
""")
    
    # 원하는 시나리오의 주석을 제거하고 실행하세요
    # scenario_1_pod_kill()
    # scenario_2_memory_stress()
    # scenario_3_network_delay()
    # scenario_4_network_loss()
    # scenario_5_cpu_stress()
    # scenario_6_io_delay()
    # scenario_7_resilience_test()
    # list_active_experiments()
    # cleanup_all()
    
    print("\n💡 위 시나리오 중 하나를 선택하여 주석을 해제하고 실행하세요!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
