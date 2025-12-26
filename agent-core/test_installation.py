#!/usr/bin/env python3
"""
간단한 테스트 스크립트
에이전트의 기본 기능을 빠르게 테스트합니다.
"""
import sys
import os

# 테스트 모드 활성화
os.environ.setdefault("MOCK_MODE", "true")

def test_import():
    """모듈 import 테스트"""
    print("1️⃣  모듈 import 테스트...")
    try:
        from langgraph_agent.agent import DrKubeAgent
        from langgraph_agent.tools.auto_fix import AutoFixer, quick_fix_oom
        from langgraph_agent.tools import k8s, llm
        print("   ✅ 모든 모듈 import 성공!\n")
        return True
    except Exception as e:
        print(f"   ❌ Import 실패: {e}\n")
        return False


def test_agent_creation():
    """에이전트 생성 테스트"""
    print("2️⃣  에이전트 생성 테스트...")
    try:
        from langgraph_agent.agent import DrKubeAgent
        agent = DrKubeAgent(namespace="default")
        print("   ✅ 에이전트 생성 성공!\n")
        return True
    except Exception as e:
        print(f"   ❌ 에이전트 생성 실패: {e}\n")
        return False


def test_autofixer():
    """AutoFixer 클래스 테스트"""
    print("3️⃣  AutoFixer 클래스 테스트...")
    try:
        from langgraph_agent.tools.auto_fix import AutoFixer
        fixer = AutoFixer(namespace="default")
        
        # 메서드 존재 확인
        assert hasattr(fixer, "fix_oom_issue")
        assert hasattr(fixer, "fix_cpu_throttling")
        assert hasattr(fixer, "restart_deployment")
        assert hasattr(fixer, "scale_deployment")
        assert hasattr(fixer, "add_node_selector")
        
        print("   ✅ AutoFixer 클래스 사용 가능!\n")
        return True
    except Exception as e:
        print(f"   ❌ AutoFixer 테스트 실패: {e}\n")
        return False


def test_k8s_tools():
    """Kubernetes 도구 테스트"""
    print("4️⃣  Kubernetes 도구 테스트...")
    try:
        from langgraph_agent.tools import k8s
        
        # 함수 존재 확인
        assert hasattr(k8s, "run_kubectl")
        assert hasattr(k8s, "get_pods_with_issues")
        assert hasattr(k8s, "get_pod_details")
        
        print("   ✅ Kubernetes 도구 사용 가능!\n")
        return True
    except Exception as e:
        print(f"   ❌ Kubernetes 도구 테스트 실패: {e}\n")
        return False


def test_llm_tools():
    """LLM 도구 테스트"""
    print("5️⃣  LLM 도구 테스트...")
    try:
        from langgraph_agent.tools import llm
        
        # Mock 모드 확인
        is_mock = llm.is_mock_mode()
        print(f"   ℹ️  Mock 모드: {is_mock}")
        
        # 함수 존재 확인
        assert hasattr(llm, "analyze_oom_issue")
        assert hasattr(llm, "analyze_crashloop_issue")
        
        print("   ✅ LLM 도구 사용 가능!\n")
        return True
    except Exception as e:
        print(f"   ❌ LLM 도구 테스트 실패: {e}\n")
        return False


def main():
    """메인 테스트 함수"""
    print("""
╔══════════════════════════════════════════════════════════╗
║              dr-kube 에이전트 테스트                    ║
╚══════════════════════════════════════════════════════════╝
""")
    
    tests = [
        test_import,
        test_agent_creation,
        test_autofixer,
        test_k8s_tools,
        test_llm_tools,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # 결과 요약
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 모든 테스트 통과! ({passed}/{total})")
        print("\n✅ dr-kube 에이전트가 정상적으로 설치되었습니다!")
        print("   이제 quickstart.py를 실행하거나 CLI를 사용하세요.\n")
        return 0
    else:
        print(f"⚠️  일부 테스트 실패 ({passed}/{total})")
        print("   로그를 확인하고 문제를 해결하세요.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
