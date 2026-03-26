"""DeliveryState - LangGraph 워크플로우 상태"""
from typing import TypedDict, Literal

IssueType = Literal[
    "oom",               # OOMKilled - 메모리 초과
    "crash_loop",        # CrashLoopBackOff
    "service_error",     # 서비스 간 503/connection refused
    "high_latency",      # P99 지연 임계 초과
    "resource_exhaustion",  # CPU throttle
    "replica_shortage",  # replicas 0으로 강제 다운 (watcher 감지)
    "resource_deleted",  # Deployment/Service 삭제 (watcher 감지)
    "unknown",
]

RiskLevel = Literal["low", "medium", "high", "critical"]

RetryStrategy = Literal["conservative", "moderate", "aggressive"]


class ContextData(TypedDict, total=False):
    """병렬 수집된 컨텍스트"""
    pod_logs: dict[str, list[str]]      # service → 최근 로그 라인
    pod_events: dict[str, list[str]]    # service → K8s 이벤트
    pod_status: dict[str, dict]         # service → {phase, restart_count, conditions}
    metrics: dict[str, dict]            # service → {memory_pct, cpu_pct, rps, error_rate}
    dependency_health: dict[str, bool]  # service → upstream 응답 여부


class FixPlan(TypedDict, total=False):
    """수정 계획"""
    target_service: str         # 수정 대상 서비스
    target_file: str            # manifests/delivery-app/{service}.yaml
    original_manifest: str      # 수정 전 YAML
    modified_manifest: str      # 수정 후 YAML
    changed_fields: list[str]   # 변경된 YAML 경로 목록
    fix_description: str        # 60자 이내 영문 설명
    rationale: str              # 변경 근거 (한국어)
    strategy: RetryStrategy     # 이번 시도의 전략


class DeliveryState(TypedDict, total=False):
    # ── 입력 ──────────────────────────────────────
    alert_payload: dict
    issue_id: str
    issue_type: IssueType
    affected_service: str       # 직접 영향 서비스
    affected_namespace: str
    error_message: str
    fingerprint: str            # Alert fingerprint

    # ── 컨텍스트 ──────────────────────────────────
    context: ContextData

    # ── LLM 분석 결과 ──────────────────────────────
    root_cause: str
    severity: RiskLevel
    affected_services: list[str]   # 직접 + 연쇄 영향 목록
    analysis_summary: str

    # ── 수정 계획 ──────────────────────────────────
    fix_plan: FixPlan
    validation_errors: list[str]

    # ── Human-in-the-Loop ─────────────────────────
    requires_human_approval: bool
    slack_ts: str               # Slack 메시지 ts (스레드 답글용)
    slack_action_id: str        # Slack 버튼 action_id (resume 매핑용)
    human_decision: Literal["approve", "reject", "modify"] | None
    human_comment: str          # 수정 요청 시 사용자 코멘트

    # ── PR ────────────────────────────────────────
    branch_name: str
    pr_url: str
    pr_number: int

    # ── 워크플로우 제어 ────────────────────────────
    retry_count: int
    status: str
    error: str
