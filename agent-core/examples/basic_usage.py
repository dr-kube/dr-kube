#!/usr/bin/env python3
"""
기본 사용 예제
"""
from agents import OOMKilledAgent
from config import LLM_PROVIDER, GEMINI_API_KEY, OPENAI_API_KEY


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


def example_1_analyze_all_oom_pods():
    """예제 1: 네임스페이스의 모든 OOMKilled 파드 분석"""
    print("=" * 80)
    print("예제 1: 모든 OOMKilled 파드 분석")
    print("=" * 80)

    agent = get_agent()
    result = agent.analyze_oomkilled_pods(namespace="default")
    print(result)


def example_2_analyze_specific_pod():
    """예제 2: 특정 파드의 OOMKilled 이슈 분석"""
    print("\n" + "=" * 80)
    print("예제 2: 특정 파드 분석")
    print("=" * 80)

    agent = get_agent()

    pod_name = "oom-test"  # 분석할 파드 이름
    namespace = "default"

    result = agent.analyze_specific_pod(pod_name, namespace)
    print(result)


def example_3_get_fix_instructions():
    """예제 3: OOM 이슈 해결 방법 가져오기"""
    print("\n" + "=" * 80)
    print("예제 3: 해결 방법 가이드")
    print("=" * 80)

    agent = get_agent()

    pod_name = "oom-test"
    namespace = "default"

    # 에이전트가 자동으로 적절한 메모리 리미트를 계산
    result = agent.get_fix_instructions(pod_name, namespace)
    print(result)


def example_4_custom_query():
    """예제 4: 커스텀 쿼리"""
    print("\n" + "=" * 80)
    print("예제 4: 커스텀 쿼리")
    print("=" * 80)

    agent = get_agent()

    custom_query = """
    default 네임스페이스에서 scenario=oom-killed 레이블을 가진 파드를 찾아서:
    1. 현재 메모리 설정 확인
    2. 재시작 횟수 확인
    3. 적절한 메모리 리미트 추천
    4. Deployment 수정 방법 안내
    """

    result = agent.agent.invoke({"input": custom_query})
    print(result["output"])


if __name__ == "__main__":
    try:
        get_agent()  # API 키 체크
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)

    # 원하는 예제의 주석을 제거하고 실행하세요
    example_1_analyze_all_oom_pods()
    # example_2_analyze_specific_pod()
    # example_3_get_fix_instructions()
    # example_4_custom_query()
