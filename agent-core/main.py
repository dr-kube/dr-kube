#!/usr/bin/env python3
"""
OOMKilled Agent - Kubernetes OOM 이슈 분석 및 해결 에이전트
"""
import argparse
from agents import OOMKilledAgent
from config import (
    LLM_PROVIDER,
    OPENAI_API_KEY, OPENAI_MODEL,
    GEMINI_API_KEY, GEMINI_MODEL
)


def main():
    parser = argparse.ArgumentParser(
        description="Kubernetes OOMKilled 이슈를 분석하고 해결책을 제시하는 AI 에이전트"
    )
    parser.add_argument(
        "--namespace", "-n",
        default="default",
        help="분석할 네임스페이스 (기본값: default)"
    )
    parser.add_argument(
        "--pod", "-p",
        help="분석할 특정 파드 이름"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="수정 방법 가이드 제공"
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini"],
        default=LLM_PROVIDER,
        help=f"LLM 제공자 선택 (기본값: {LLM_PROVIDER})"
    )
    parser.add_argument(
        "--model",
        help="사용할 모델 이름 (기본값: provider별 기본 모델)"
    )

    args = parser.parse_args()

    # Provider에 따라 API 키와 모델 선택
    if args.provider == "gemini":
        api_key = GEMINI_API_KEY
        model_name = args.model or GEMINI_MODEL
        if not api_key:
            print("❌ Error: GEMINI_API_KEY가 설정되지 않았습니다.")
            print(".env 파일에 GEMINI_API_KEY를 추가해주세요.")
            return
    else:  # openai
        api_key = OPENAI_API_KEY
        model_name = args.model or OPENAI_MODEL
        if not api_key:
            print("❌ Error: OPENAI_API_KEY가 설정되지 않았습니다.")
            print(".env 파일에 OPENAI_API_KEY를 추가해주세요.")
            return

    print("🤖 OOMKilled Agent 시작...")
    print(f"Provider: {args.provider}")
    print(f"모델: {model_name}")
    print(f"네임스페이스: {args.namespace}\n")

    agent = OOMKilledAgent(
        api_key=api_key,
        model_name=model_name,
        provider=args.provider
    )

    try:
        if args.pod:
            print(f"📊 파드 '{args.pod}' 분석 중...\n")
            if args.fix:
                result = agent.get_fix_instructions(args.pod, args.namespace)
            else:
                result = agent.analyze_specific_pod(args.pod, args.namespace)
        else:
            print(f"🔍 네임스페이스 '{args.namespace}'의 모든 OOMKilled 파드 분석 중...\n")
            result = agent.analyze_oomkilled_pods(args.namespace)

        print("\n" + "="*80)
        print("분석 결과")
        print("="*80)
        print(result)
        print("="*80 + "\n")

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
