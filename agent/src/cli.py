"""CLI 엔트리포인트"""
import sys
import os
from dotenv import load_dotenv
from dr_kube.graph import create_graph

# 환경 변수 로드
load_dotenv()

# Windows 콘솔에서 UTF-8 출력 활성화
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "analyze":
        print("사용법: python -m cli analyze <이슈파일.json>")
        sys.exit(1)

    issue_file = sys.argv[2]
    graph = create_graph()

    print(f"\n이슈 분석 중: {issue_file}\n")

    result = graph.invoke({"issue_file": issue_file})

    if result.get("error"):
        print(f"에러 발생: {result['error']}")
        sys.exit(1)

    issue = result.get("issue_data", {})

    # 심각도별 이모지 (선택사항)
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
        # 긴 라인은 적절히 줄바꿈
        suggestion_lines = suggestion.strip().split('\n')
        print(f"   {i}. {suggestion_lines[0]}")
        for line in suggestion_lines[1:]:
            if line.strip():
                print(f"      {line.strip()}")

    # 실행 계획 표시
    action_plan = result.get("action_plan", "").strip()
    if action_plan:
        print(f"\n⚡ 실행 계획:")
        print("-" * 60)
        for line in action_plan.split('\n'):
            print(f"  {line}")
        print("-" * 60)

    # YAML diff 표시
    yaml_diff = result.get("yaml_diff", "").strip()
    if yaml_diff:
        print(f"\n📝 YAML 수정 (Diff):")
        print("-" * 60)
        for line in yaml_diff.split('\n'):
            stripped = line.strip()
            if stripped.startswith('-'):
                # 삭제된 라인
                print(f"  ❌ {line}")
            elif stripped.startswith('+'):
                # 추가된 라인
                print(f"  ✅ {line}")
            else:
                print(f"     {line}")
        print("-" * 60)

    print("\n" + "=" * 60)

    # VERBOSE 모드 확인
    verbose = os.getenv("VERBOSE", "false").lower() == "true" or "--verbose" in sys.argv or "-v" in sys.argv
    if verbose:
        print("\n📄 전체 분석 내용:")
        print("-" * 60)
        print(result.get('analysis', 'N/A'))
        print("=" * 60)

    # AUTO_APPROVE 환경 변수 확인
    auto_approve = os.getenv("AUTO_APPROVE", "false").lower() == "true"

    if auto_approve:
        print("\n자동 승인됨. (실제 실행은 추후 구현 예정)")
    else:
        try:
            answer = input("\n승인하시겠습니까? (y/n): ").strip().lower()
            if answer == "y":
                print("\n승인됨. (실제 실행은 추후 구현 예정)")
            else:
                print("\n취소됨.")
        except (EOFError, KeyboardInterrupt):
            print("\n\n분석 완료. (승인 프롬프트 건너뜀)")


if __name__ == "__main__":
    main()
