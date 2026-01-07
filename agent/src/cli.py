"""CLI 엔트리포인트"""
import sys
from dr_kube.graph import create_graph


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

    print("=" * 50)
    print("DR-Kube 분석 결과")
    print("=" * 50)
    print(f"이슈: {issue.get('error_message', 'N/A')} ({issue.get('resource', 'N/A')})")
    print(f"심각도: {result.get('severity', 'N/A')}")
    print()
    print("근본 원인:")
    print(f"  {result.get('root_cause', 'N/A')}")
    print()
    print("해결책:")
    for i, suggestion in enumerate(result.get("suggestions", []), 1):
        print(f"  {i}. {suggestion}")
    print("=" * 50)

    # 승인 프롬프트
    answer = input("\n승인하시겠습니까? (y/n): ").strip().lower()
    if answer == "y":
        print("\n승인됨. (실제 실행은 추후 구현 예정)")
    else:
        print("\n취소됨.")


if __name__ == "__main__":
    main()
