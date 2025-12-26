#!/usr/bin/env python3
"""
dr-kube CLI
LangGraph 기반 Kubernetes 이슈 해결 에이전트
"""
import argparse
import sys
from .agent import DrKubeAgent


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
    
    args = parser.parse_args()
    
    print("🤖 dr-kube Agent 시작...")
    print(f"   네임스페이스: {args.namespace}")
    if args.pod:
        print(f"   대상 파드: {args.pod}")
    print()
    
    try:
        agent = DrKubeAgent()
        
        # 분석 실행
        result = agent.analyze(
            namespace=args.namespace,
            pod_name=args.pod,
            auto_approve=args.auto_approve and not args.dry_run
        )
        
        print(result)
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
                        result = agent.approve_fix()
                        print(result)
                    else:
                        print("\n⛔ 수정이 취소되었습니다.")
                        result = agent.reject_fix()
        
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
