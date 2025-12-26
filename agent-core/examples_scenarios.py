#!/usr/bin/env python3
"""
다양한 시나리오 예제
각 상황별로 어떻게 사용하는지 보여줍니다.
"""
from langgraph_agent.tools.auto_fix import AutoFixer, quick_fix_oom, quick_restart


def scenario_1_oom_fix():
    """
    시나리오 1: OOM 문제 자동 수정
    
    상황: my-app 파드가 계속 OOMKilled됨
    해결: 메모리를 2배로 증가
    """
    print("=" * 60)
    print("시나리오 1: OOMKilled 자동 수정")
    print("=" * 60)
    
    # 방법 1: 간편 함수 사용
    success = quick_fix_oom(
        pod_name="oom-test-646f556576-vsgsb",
        namespace="default",
        container="python-oom"
    )
    
    if success:
        print("✅ 수정 완료!")
    else:
        print("❌ 수정 실패. 수동 확인 필요.")


def scenario_2_cpu_increase():
    """
    시나리오 2: CPU 부족 문제 해결
    
    상황: 애플리케이션이 느림, CPU throttling 발생
    해결: CPU를 1.5배로 증가
    """
    print("\n" + "=" * 60)
    print("시나리오 2: CPU Throttling 해결")
    print("=" * 60)
    
    fixer = AutoFixer(namespace="default")
    
    success, msg, changes = fixer.fix_cpu_throttling(
        pod_name="my-app-xxx",
        container_name="my-container",
        multiplier=1.5  # 1.5배 증가
    )
    
    print(f"결과: {msg}")
    if success:
        print(f"변경 내역: {changes}")


def scenario_3_restart_crashloop():
    """
    시나리오 3: CrashLoopBackOff 재시작
    
    상황: 파드가 계속 크래시
    해결: 간단히 재시작 시도
    """
    print("\n" + "=" * 60)
    print("시나리오 3: CrashLoopBackOff 재시작")
    print("=" * 60)
    
    # 방법 1: 간편 함수
    success = quick_restart("my-app-xxx", "default")
    
    # 방법 2: AutoFixer 클래스
    # fixer = AutoFixer("default")
    # success, msg, _ = fixer.restart_deployment("my-app-xxx")
    # print(msg)


def scenario_4_scale_up():
    """
    시나리오 4: 부하 증가로 파드 개수 늘리기
    
    상황: 트래픽 증가, 더 많은 파드 필요
    해결: 파드 개수를 5개로 증가
    """
    print("\n" + "=" * 60)
    print("시나리오 4: 파드 개수 증가")
    print("=" * 60)
    
    fixer = AutoFixer(namespace="default")
    
    success, msg, changes = fixer.scale_deployment(
        pod_name="my-app-xxx",
        replicas=5  # 5개로 증가
    )
    
    print(f"결과: {msg}")


def scenario_5_node_selector():
    """
    시나리오 5: 특정 노드에서만 실행
    
    상황: SSD 디스크가 있는 노드에서만 실행하고 싶음
    해결: nodeSelector 추가
    """
    print("\n" + "=" * 60)
    print("시나리오 5: NodeSelector 추가")
    print("=" * 60)
    
    fixer = AutoFixer(namespace="default")
    
    success, msg, changes = fixer.add_node_selector(
        pod_name="my-app-xxx",
        node_selector={
            "disktype": "ssd",
            "zone": "us-west-1a"
        }
    )
    
    print(f"결과: {msg}")


def scenario_6_batch_fix():
    """
    시나리오 6: 여러 문제 동시 해결
    
    상황: 여러 파드가 다양한 문제를 가지고 있음
    해결: 각 문제에 맞게 자동 수정
    """
    print("\n" + "=" * 60)
    print("시나리오 6: 일괄 수정")
    print("=" * 60)
    
    # 여러 파드의 문제를 한번에 해결
    problems = [
        ("pod-1", "oom"),
        ("pod-2", "crashloop"),
        ("pod-3", "cpu"),
    ]
    
    fixer = AutoFixer("default")
    
    for pod_name, issue_type in problems:
        print(f"\n처리 중: {pod_name} ({issue_type})")
        
        if issue_type == "oom":
            success, msg, _ = fixer.fix_oom_issue(pod_name, "app", multiplier=2.0)
        elif issue_type == "crashloop":
            success, msg, _ = fixer.restart_deployment(pod_name)
        elif issue_type == "cpu":
            success, msg, _ = fixer.fix_cpu_throttling(pod_name, "app", multiplier=1.5)
        
        status = "✅" if success else "❌"
        print(f"{status} {msg}")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║         dr-kube 자동 수정 툴 시나리오 예제             ║
╚══════════════════════════════════════════════════════════╝

각 시나리오를 확인하고 필요한 것을 실행하세요.
주의: 실제 클러스터에 영향을 줄 수 있으니 주의하세요!

사용 가능한 시나리오:
1. OOMKilled 자동 수정
2. CPU Throttling 해결
3. CrashLoopBackOff 재시작
4. 파드 개수 증가
5. NodeSelector 추가
6. 여러 문제 일괄 수정
""")
    
    # 원하는 시나리오의 주석을 제거하고 실행하세요
    scenario_1_oom_fix()
    # scenario_2_cpu_increase()
    # scenario_3_restart_crashloop()
    # scenario_4_scale_up()
    # scenario_5_node_selector()
    # scenario_6_batch_fix()
