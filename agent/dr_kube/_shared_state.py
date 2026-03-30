"""프로세스 내 공유 상태 (항상 dr_kube._shared_state로 임포트되므로 단일 인스턴스 보장)."""

# 코파일럿 모드: action_id → {result, issue_data, channel, ts}
pending_approvals: dict[str, dict] = {}

# PR 번호 → 이슈 ID 매핑
pr_to_thread: dict[int, str] = {}

# 머지 대기: pr_number → {channel, ts, issue_data, fix_description, pr_url, merged}
pending_merges: dict[int, dict] = {}
