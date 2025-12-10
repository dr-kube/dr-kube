#!/usr/bin/env python3
"""
고급 사용 예제 - 커스텀 워크플로우
"""
from agents import OOMKilledAgent
from tools.k8s_tools import K8sClient
from config import LLM_PROVIDER, GEMINI_API_KEY, OPENAI_API_KEY
import yaml


def get_agent():
    """Provider에 따라 적절한 에이전트를 생성합니다."""
    if LLM_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY를 설정해주세요.")
        return OOMKilledAgent(api_key=GEMINI_API_KEY, provider="gemini")
    else:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY를 설정해주세요.")
        return OOMKilledAgent(api_key=OPENAI_API_KEY, provider="openai")


def monitor_and_analyze():
    """실시간 모니터링 및 분석 워크플로우"""
    print("🔍 OOMKilled 모니터링 및 자동 분석")
    print("=" * 80)

    k8s_client = K8sClient()
    agent = get_agent()

    # 모든 네임스페이스 체크
    namespaces = ["default", "production", "staging"]

    for namespace in namespaces:
        print(f"\n📦 네임스페이스: {namespace}")
        print("-" * 80)

        oom_pods = k8s_client.get_oomkilled_pods(namespace)

        if not oom_pods:
            print(f"✅ {namespace}에 OOMKilled 파드 없음")
            continue

        print(f"⚠️  {len(oom_pods)}개의 OOMKilled 파드 발견!")

        for pod_info in oom_pods:
            print(f"\n  파드: {pod_info['name']}")
            print(f"  컨테이너: {pod_info['container']}")
            print(f"  재시작 횟수: {pod_info['restart_count']}")

            # AI 에이전트로 분석
            print("\n  🤖 AI 분석 중...")
            result = agent.analyze_specific_pod(pod_info['name'], namespace)
            print(f"\n  분석 결과:\n{result}")
            print("\n" + "="*80)


def batch_fix_recommendations():
    """여러 파드에 대한 일괄 수정 권장사항"""
    print("🔧 일괄 수정 권장사항 생성")
    print("=" * 80)

    k8s_client = K8sClient()
    agent = get_agent()

    namespace = "default"
    oom_pods = k8s_client.get_oomkilled_pods(namespace)

    if not oom_pods:
        print("OOMKilled 파드를 찾을 수 없습니다.")
        return

    recommendations = []

    for pod_info in oom_pods:
        pod_name = pod_info['name']
        print(f"\n📊 {pod_name} 분석 중...")

        # 파드 상세 정보
        details = k8s_client.get_pod_details(pod_name, namespace)

        # AI 에이전트로 권장사항 생성
        fix_instructions = agent.get_fix_instructions(pod_name, namespace)

        recommendations.append({
            "pod": pod_name,
            "current_limits": details['containers'][0]['limits'],
            "recommendations": fix_instructions
        })

    # 결과 저장
    output_file = "oom_fix_recommendations.yaml"
    with open(output_file, 'w') as f:
        yaml.dump(recommendations, f, default_flow_style=False)

    print(f"\n✅ 권장사항이 {output_file}에 저장되었습니다.")


def compare_before_after():
    """수정 전후 비교"""
    print("📊 리소스 조정 전후 비교")
    print("=" * 80)

    k8s_client = K8sClient()

    pod_name = "oom-test"
    namespace = "default"

    # 현재 상태
    details = k8s_client.get_pod_details(pod_name, namespace)
    current_memory = details['containers'][0]['limits']['memory']
    restart_count = details['containers'][0]['restart_count']

    print(f"\n현재 설정:")
    print(f"  메모리 리미트: {current_memory}")
    print(f"  재시작 횟수: {restart_count}")

    # AI 추천
    agent = get_agent()
    recommendation = agent.analyze_specific_pod(pod_name, namespace)

    print(f"\n🤖 AI 권장사항:")
    print(recommendation)


if __name__ == "__main__":
    try:
        get_agent()  # API 키 체크
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)

    # 원하는 워크플로우 실행
    monitor_and_analyze()
    # batch_fix_recommendations()
    # compare_before_after()
