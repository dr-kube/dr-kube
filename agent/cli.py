"""CLI 엔트리포인트"""
import sys
import os
import argparse
from dotenv import load_dotenv
from dr_kube.graph import create_graph

# 환경 변수 로드
load_dotenv()

# Windows 콘솔에서 UTF-8 출력 활성화
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def print_analysis_result(result: dict, verbose: bool = False):
    """분석 결과 출력"""
    issue = result.get("issue_data", {})

    # 심각도별 이모지
    severity = result.get('severity', 'medium').lower()
    severity_icon = {
        'critical': '🔴',
        'high': '🟠',
        'medium': '🟡',
        'low': '🟢'
    }.get(severity, '⚪')

    print("\n" + "=" * 60)
    print("  DR-Kube 분석 결과")
    print("=" * 60)
    print(f"\n📋 이슈: {issue.get('error_message', 'N/A')}")
    print(f"📦 리소스: {issue.get('resource', 'N/A')}")
    print(f"{severity_icon} 심각도: {severity.upper()}")
    print(f"\n🔍 근본 원인:")
    print(f"   {result.get('root_cause', 'N/A')}")
    print(f"\n💡 해결책:")
    for i, suggestion in enumerate(result.get("suggestions", []), 1):
        suggestion_lines = suggestion.strip().split('\n')
        print(f"   {i}. {suggestion_lines[0]}")
        for line in suggestion_lines[1:]:
            if line.strip():
                print(f"      {line.strip()}")

    # 수정안 설명 표시
    fix_description = result.get("fix_description", "").strip()
    if fix_description:
        fix_method = result.get("fix_method", "")
        method_label = {"rule_based": "[룰 기반]", "llm": "[LLM]", "none": ""}.get(fix_method, "")
        print(f"\n🔧 수정안 {method_label}: {fix_description}")
        target_file = result.get("target_file", "")
        if target_file:
            print(f"   파일: {target_file}")

    # PR 생성 결과
    if result.get("pr_url"):
        print(f"\n🔗 PR 생성됨:")
        print(f"   {result.get('pr_url')}")
        print(f"   브랜치: {result.get('branch_name')}")

    print("\n" + "=" * 60)

    # VERBOSE 모드: fix_content (수정된 YAML) 출력
    if verbose and result.get("fix_content"):
        print("\n📄 수정된 YAML:")
        print("-" * 60)
        print(result.get('fix_content', 'N/A'))
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="DR-Kube 에이전트")
    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # analyze 명령어
    analyze_parser = subparsers.add_parser("analyze", help="이슈 분석")
    analyze_parser.add_argument("issue_file", help="이슈 JSON 파일 경로")
    analyze_parser.add_argument("-v", "--verbose", action="store_true", help="상세 출력")
    analyze_parser.add_argument("--with-pr", action="store_true", help="PR 생성까지 실행")

    # fix 명령어 (PR 생성 포함)
    fix_parser = subparsers.add_parser("fix", help="이슈 분석 + PR 생성")
    fix_parser.add_argument("issue_file", help="이슈 JSON 파일 경로")
    fix_parser.add_argument("-v", "--verbose", action="store_true", help="상세 출력")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    issue_file = args.issue_file
    verbose = args.verbose or os.getenv("VERBOSE", "false").lower() == "true"

    # PR 생성 여부 결정
    with_pr = args.command == "fix" or getattr(args, "with_pr", False)

    # 그래프 생성
    graph = create_graph(with_pr=with_pr)

    if with_pr:
        print(f"\n🚀 이슈 분석 + PR 생성 중: {issue_file}\n")
    else:
        print(f"\n🔍 이슈 분석 중: {issue_file}\n")

    result = graph.invoke({"issue_file": issue_file})

    if result.get("error"):
        print(f"\n❌ 에러 발생: {result['error']}")
        sys.exit(1)

    print_analysis_result(result, verbose)

    # PR 미생성 시 승인 프롬프트
    if not with_pr:
        auto_approve = os.getenv("AUTO_APPROVE", "false").lower() == "true"
        if auto_approve:
            print("\n자동 승인됨.")
        else:
            try:
                answer = input("\nPR을 생성하시겠습니까? (y/n): ").strip().lower()
                if answer == "y":
                    print("\n🚀 PR 생성 중...")
                    # PR 생성 플로우 실행
                    pr_graph = create_graph(with_pr=True)
                    pr_result = pr_graph.invoke({"issue_file": issue_file})
                    if pr_result.get("error"):
                        print(f"\n❌ PR 생성 실패: {pr_result['error']}")
                    else:
                        print(f"\n✅ PR 생성 완료: {pr_result.get('pr_url')}")
                else:
                    print("\n취소됨.")
            except (EOFError, KeyboardInterrupt):
                print("\n\n분석 완료.")


if __name__ == "__main__":
    main()
