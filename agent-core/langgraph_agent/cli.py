#!/usr/bin/env python3
"""
dr-kube CLI
LangGraph 기반 Kubernetes 이슈 해결 에이전트
"""
import argparse
import sys
from .agent import DrKubeAgent


def run_chaos_mode(args):
    """
    Chaos Engineering 모드 실행
    
    Args:
        args: CLI 인자
        
    Returns:
        종료 코드
    """
    from .tools.chaos import ChaosExperiment, check_chaos_mesh_prerequisites
    
    print("💥 Chaos Engineering 모드")
    print(f"   실험: {args.chaos}")
    print(f"   네임스페이스: {args.namespace}")
    print(f"   지속 시간: {args.chaos_duration}")
    print(f"   대상: {args.chaos_label}")
    print()
    
    # Chaos Mesh 확인
    success, message = check_chaos_mesh_prerequisites()
    if not success:
        print(message)
        return 1
    
    print("✅ Chaos Mesh 사용 가능\n")
    
    # 라벨 파싱
    label_parts = args.chaos_label.split("=")
    if len(label_parts) != 2:
        print("❌ 라벨 형식이 잘못되었습니다. 예: app=myapp")
        return 1
    
    label_selector = {label_parts[0]: label_parts[1]}
    chaos = ChaosExperiment(namespace=args.namespace)
    
    # 실험 타입별 실행
    experiment_name = f"cli-{args.chaos}-{label_parts[1]}"
    
    try:
        if args.chaos == "pod-kill":
            success, message = chaos.create_pod_kill_chaos(
                name=experiment_name,
                label_selector=label_selector,
                duration=args.chaos_duration,
                mode="one"
            )
        
        elif args.chaos == "memory-stress":
            success, message = chaos.create_stress_chaos(
                name=experiment_name,
                label_selector=label_selector,
                memory="256MB",
                duration=args.chaos_duration
            )
        
        elif args.chaos == "network-delay":
            success, message = chaos.create_network_delay_chaos(
                name=experiment_name,
                label_selector=label_selector,
                latency="100ms",
                duration=args.chaos_duration
            )
        
        elif args.chaos == "network-loss":
            success, message = chaos.create_network_loss_chaos(
                name=experiment_name,
                label_selector=label_selector,
                loss="25",
                duration=args.chaos_duration
            )
        
        elif args.chaos == "cpu-stress":
            success, message = chaos.create_stress_chaos(
                name=experiment_name,
                label_selector=label_selector,
                cpu="1",
                duration=args.chaos_duration
            )
        
        elif args.chaos == "io-delay":
            success, message = chaos.create_io_delay_chaos(
                name=experiment_name,
                label_selector=label_selector,
                delay="100ms",
                duration=args.chaos_duration
            )
        
        else:
            print(f"❌ 알 수 없는 실험 타입: {args.chaos}")
            return 1
        
        print(message)
        
        if success:
            print(f"\n💡 실험 상태 확인:")
            chaos_type = {
                "pod-kill": "podchaos",
                "memory-stress": "stresschaos",
                "network-delay": "networkchaos",
                "network-loss": "networkchaos",
                "cpu-stress": "stresschaos",
                "io-delay": "iochaos"
            }[args.chaos]
            
            print(f"   kubectl get {chaos_type} {experiment_name} -n {args.namespace}")
            print(f"\n🗑️ 실험 중단:")
            print(f"   kubectl delete {chaos_type} {experiment_name} -n {args.namespace}")
            print(f"\n⏱️ {args.chaos_duration} 후 자동으로 종료됩니다")
            
            return 0
        else:
            return 1
    
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="🤖 dr-kube: Kubernetes 이슈 자동 분석 및 해결 에이전트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # default 네임스페이스 스캔
  python -m langgraph_agent.cli -n default
  
  # 특정 파드 분석
  python -m langgraph_agent.cli -n default -p oom-test
  
  # 자동 승인으로 바로 수정 실행
  python -m langgraph_agent.cli -n default -p oom-test --auto-approve
        """
    )
    
    parser.add_argument(
        "-n", "--namespace",
        default="default",
        help="대상 네임스페이스 (기본값: default)"
    )
    
    parser.add_argument(
        "-p", "--pod",
        default=None,
        help="분석할 특정 파드 이름"
    )
    
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="수정 계획을 자동으로 승인하여 바로 실행"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="분석만 하고 수정하지 않음"
    )
    
    parser.add_argument(
        "--chaos",
        choices=["pod-kill", "memory-stress", "network-delay", "network-loss", "cpu-stress", "io-delay"],
        help="카오스 실험 실행 (Chaos Mesh 필요)"
    )
    
    parser.add_argument(
        "--chaos-duration",
        default="30s",
        help="카오스 실험 지속 시간 (기본값: 30s)"
    )
    
    parser.add_argument(
        "--chaos-label",
        default="app=test",
        help="카오스 대상 라벨 선택자 (기본값: app=test)"
    )
    
    args = parser.parse_args()
    
    # Chaos 모드 처리
    if args.chaos:
        return run_chaos_mode(args)
    
    print("🤖 dr-kube Agent 시작...")
    print(f"   네임스페이스: {args.namespace}")
    if args.pod:
        print(f"   대상 파드: {args.pod}")
    print()
    
    try:
        agent = DrKubeAgent(namespace=args.namespace)
        
        # 분석 실행
        result = agent.analyze(
            pod_name=args.pod,
            auto_approve=args.auto_approve and not args.dry_run
        )
        
        print(result["response"])
        print()
        
        # 수정 계획이 있고 승인 대기 중이면 사용자 입력 받기
        if not args.auto_approve and not args.dry_run:
            fix_plan = agent.get_fix_plan()
            if fix_plan and fix_plan.get("action") != "manual_fix_required":
                approval_status = agent._current_state.get("approval_status")
                if approval_status == "pending":
                    print("-" * 60)
                    user_input = input("수정을 실행하시겠습니까? (y/n): ").strip().lower()
                    
                    if user_input in ["y", "yes"]:
                        print("\n🔧 수정 실행 중...")
                        exec_result = agent.approve_fix()
                        print(exec_result["response"])
                    else:
                        print("\n⛔ 수정이 취소되었습니다.")
                        reject_result = agent.reject_fix()
                        print(reject_result["response"])
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n중단되었습니다.")
        return 1
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
