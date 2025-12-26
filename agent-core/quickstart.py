#!/usr/bin/env python3
"""
빠른 시작 스크립트
dr-kube 에이전트를 간단히 테스트합니다.
"""
import os
import sys

# API 키가 없어도 작동하도록 mock 모드 활성화
if "GEMINI_API_KEY" not in os.environ:
    print("ℹ️  GEMINI_API_KEY가 없습니다. Mock 모드로 실행합니다.")
    print("   (실제 LLM 대신 규칙 기반 분석을 사용합니다)\n")

from langgraph_agent.agent import DrKubeAgent


def main():
    """메인 함수"""
    print("""
╔══════════════════════════════════════════════════════════╗
║           dr-kube 쿠버네티스 문제 해결 에이전트        ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # 1. 에이전트 생성
    print("1️⃣  에이전트 초기화 중...")
    agent = DrKubeAgent(namespace="default")
    print("   ✅ 완료\n")
    
    # 2. 자동 분석 (auto_approve=False로 승인 대기)
    print("2️⃣  클러스터 문제 탐지 중...")
    result = agent.analyze(auto_approve=False)
    print(f"   ✅ 분석 완료\n")
    
    # 3. 결과 출력
    print("3️⃣  분석 결과:")
    print("─" * 60)
    print(result["response"])
    print("─" * 60)
    print()
    
    # 4. 수정 계획이 있으면 승인 여부 물어보기
    if result.get("fix_plan"):
        print("4️⃣  수정 계획이 준비되었습니다.")
        print("   수정을 진행하시겠습니까? (y/n): ", end="")
        
        user_input = input().strip().lower()
        
        if user_input == "y":
            print("\n   수정 승인됨. 실행 중...")
            approve_result = agent.approve_fix()
            print(f"   ✅ {approve_result['response']}\n")
        else:
            print("\n   수정이 거부되었습니다.")
            reject_result = agent.reject_fix()
            print(f"   ℹ️  {reject_result['response']}\n")
    else:
        print("4️⃣  수정이 필요한 문제가 발견되지 않았습니다.\n")
    
    print("=" * 60)
    print("완료! 감사합니다.")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        print("   자세한 내용은 로그를 확인하세요.")
        sys.exit(1)
