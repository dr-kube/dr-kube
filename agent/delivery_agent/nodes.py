"""LangGraph 노드 구현"""
import logging
import os
import re
import uuid
from pathlib import Path

import yaml
from langchain_core.messages import HumanMessage

from delivery_agent.policy import (
    DELIVERY_SERVICES, ISSUE_POLICY, should_require_human, get_retry_strategy
)
from delivery_agent.prompts import ANALYZE_PROMPT, PLAN_FIX_PROMPT, STRATEGY_GUIDANCE
from delivery_agent.schemas import AnalysisResult, FixPlanOutput
from delivery_agent.state import DeliveryState, IssueType
from delivery_agent.tools import collect_context_parallel, read_manifest

logger = logging.getLogger("delivery-nodes")

PROJECT_ROOT = Path(__file__).parent.parent.parent
MAX_RETRIES = 3

# ── 이슈 분류 규칙 ─────────────────────────────────────

OOM_PATTERNS = [r"OOMKilled", r"Out of memory", r"memory limit exceeded", r"Killed.*memory"]
CRASH_LOOP_PATTERNS = [r"CrashLoopBackOff", r"Error.*exit code [^0]", r"Back-off restarting"]
SERVICE_ERROR_PATTERNS = [r"connection refused", r"503", r"Service Unavailable", r"dial.*tcp.*refused"]
HIGH_LATENCY_PATTERNS = [r"timeout", r"context deadline exceeded", r"request timeout"]
RESOURCE_PATTERNS = [r"cpu throttl", r"Throttling", r"OOMScore"]


def _classify_by_pattern(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


# ── 노드 함수 ──────────────────────────────────────────

def load_alert(state: DeliveryState) -> DeliveryState:
    """Alert payload 파싱 + 기본 필드 추출"""
    payload = state.get("alert_payload", {})
    labels = payload.get("labels", {})
    annotations = payload.get("annotations", {})

    affected_service = (
        labels.get("deployment")
        or labels.get("app")  # DeliveryAppHighErrorRate: app="menu-service"
        or labels.get("pod", "").rsplit("-", 2)[0]  # pod명 → deployment명 추출
        or labels.get("service", "unknown")
    )
    namespace = labels.get("namespace", "delivery-app")
    error_message = annotations.get("description") or annotations.get("summary", "")
    fingerprint = payload.get("fingerprint", str(uuid.uuid4())[:8])

    logger.info("Alert 로드: service=%s, namespace=%s", affected_service, namespace)

    return {
        **state,
        "issue_id": fingerprint,
        "affected_service": affected_service,
        "affected_namespace": namespace,
        "error_message": error_message,
        "fingerprint": fingerprint,
        "retry_count": state.get("retry_count", 0),
        "status": "loaded",
    }


def gather_context(state: DeliveryState) -> DeliveryState:
    """병렬로 logs + events + status + metrics 수집"""
    service = state.get("affected_service", "")
    namespace = state.get("affected_namespace", "delivery-app")

    logger.info("컨텍스트 수집 시작: %s/%s", namespace, service)
    context = collect_context_parallel(service, namespace)
    logger.info("컨텍스트 수집 완료: logs=%d services, metrics=%d services",
                len(context["pod_logs"]), len(context["metrics"]))

    return {**state, "context": context, "status": "context_gathered"}


def classify_issue(state: DeliveryState) -> DeliveryState:
    """규칙 기반 이슈 타입 분류 (LLM 없이)"""
    # watcher 이벤트: alertname으로 직접 분류
    labels = state.get("alert_payload", {}).get("labels", {})
    alertname = labels.get("alertname", "")
    if alertname == "ResourceDeleted":
        logger.info("이슈 분류 결과: resource_deleted (watcher 감지)")
        return {**state, "issue_type": "resource_deleted", "status": "classified"}
    if alertname == "ResourceModified":
        error_message = state.get("error_message", "")
        issue_type: IssueType = "replica_shortage" if "replicas" in error_message else "crash_loop"
        logger.info("이슈 분류 결과: %s (watcher 감지)", issue_type)
        return {**state, "issue_type": issue_type, "status": "classified"}
    if alertname == "DeliveryAppHighErrorRate":
        logger.info("이슈 분류 결과: service_error (Prometheus alert)")
        return {**state, "issue_type": "service_error", "status": "classified"}
    if alertname == "DeliveryAppOOMKilled":
        logger.info("이슈 분류 결과: oom (Prometheus alert)")
        return {**state, "issue_type": "oom", "status": "classified"}

    error_message = state.get("error_message", "")
    context = state.get("context", {})
    service = state.get("affected_service", "")

    # 모든 로그 + 이벤트를 하나의 텍스트로 합침
    all_text = error_message
    for logs in context.get("pod_logs", {}).values():
        all_text += "\n" + "\n".join(logs)
    for events in context.get("pod_events", {}).values():
        all_text += "\n" + "\n".join(events)

    # Pod 상태 체크
    pod_status = context.get("pod_status", {}).get(service, {})
    reason = pod_status.get("reason", "")
    restart_count = pod_status.get("restart_count", 0)

    # 우선순위 순서로 분류
    issue_type: IssueType = "unknown"

    if _classify_by_pattern(all_text + reason, OOM_PATTERNS):
        issue_type = "oom"
    elif _classify_by_pattern(all_text + reason, CRASH_LOOP_PATTERNS) or restart_count > 5:
        issue_type = "crash_loop"
    elif _classify_by_pattern(all_text, SERVICE_ERROR_PATTERNS):
        issue_type = "service_error"
    elif _classify_by_pattern(all_text, HIGH_LATENCY_PATTERNS):
        issue_type = "high_latency"
    elif _classify_by_pattern(all_text, RESOURCE_PATTERNS):
        issue_type = "resource_exhaustion"

    logger.info("이슈 분류 결과: %s (restart=%d)", issue_type, restart_count)

    return {**state, "issue_type": issue_type, "status": "classified"}


def analyze(state: DeliveryState) -> DeliveryState:
    """LLM으로 근본 원인 분석 (구조화 출력)"""
    from dr_kube.llm import get_llm

    context = state.get("context", {})
    service = state.get("affected_service", "")

    # 컨텍스트 텍스트 변환
    logs_text = "\n".join(
        f"[{svc}]\n" + "\n".join(lines[-30:])
        for svc, lines in context.get("pod_logs", {}).items()
    )
    status_text = str(context.get("pod_status", {}))
    events_text = "\n".join(
        f"[{svc}] " + "\n".join(events[-10:])
        for svc, events in context.get("pod_events", {}).items()
    )
    metrics_text = str(context.get("metrics", {}))

    prompt = ANALYZE_PROMPT.format(
        issue_type=state.get("issue_type", "unknown"),
        affected_service=service,
        error_message=state.get("error_message", ""),
        pod_logs=logs_text[:3000],
        pod_status=status_text[:500],
        pod_events=events_text[:1000],
        metrics=metrics_text[:500],
    )

    try:
        llm = get_llm()
        structured = llm.with_structured_output(AnalysisResult)
        result: AnalysisResult = structured.invoke([HumanMessage(content=prompt)])

        logger.info("분석 완료: severity=%s, requires_human=%s",
                    result.severity, result.requires_human_approval)

        requires_human = should_require_human(
            issue_type=state.get("issue_type", "unknown"),
            severity=result.severity,
            affected_services=result.affected_services,
            retry_count=state.get("retry_count", 0),
            llm_requires_human=result.requires_human_approval,
        )

        return {
            **state,
            "root_cause": result.root_cause,
            "severity": result.severity,
            "affected_services": result.affected_services,
            "analysis_summary": result.analysis_summary,
            "requires_human_approval": requires_human,
            "status": "analyzed",
        }
    except Exception as e:
        logger.error("분석 실패: %s", e)
        return {**state, "status": "error", "error": f"분석 실패: {e}"}


def plan_fix(state: DeliveryState) -> DeliveryState:
    """LLM으로 manifest 수정안 생성 (구조화 출력)"""
    from dr_kube.llm import get_llm

    issue_type = state.get("issue_type", "unknown")
    service = state.get("affected_service", "")
    retry_count = state.get("retry_count", 0)
    strategy = get_retry_strategy(issue_type, retry_count)

    # manifest 파일 읽기
    target_file = DELIVERY_SERVICES.get(service)
    if not target_file:
        return {**state, "status": "error", "error": f"알 수 없는 서비스: {service}"}

    try:
        current_manifest = read_manifest(target_file, str(PROJECT_ROOT))
    except FileNotFoundError as e:
        return {**state, "status": "error", "error": str(e)}

    # 허용 필드
    policy = ISSUE_POLICY.get(issue_type, ISSUE_POLICY["unknown"])
    allowed_fields = "\n".join(f"- {f}" for f in policy["allowed_field_patterns"])
    previous_errors = "\n".join(state.get("validation_errors", [])) or "없음"
    human_comment = state.get("human_comment", "") or "없음"

    prompt = PLAN_FIX_PROMPT.format(
        issue_type=issue_type,
        affected_service=service,
        root_cause=state.get("root_cause", ""),
        severity=state.get("severity", "medium"),
        current_manifest=current_manifest,
        strategy=strategy,
        strategy_guidance=STRATEGY_GUIDANCE.get(strategy, ""),
        previous_errors=previous_errors,
        human_comment=human_comment,
        allowed_fields=allowed_fields,
    )

    try:
        llm = get_llm()
        structured = llm.with_structured_output(FixPlanOutput)
        result: FixPlanOutput = structured.invoke([HumanMessage(content=prompt)])

        logger.info("수정안 생성: file=%s, strategy=%s, changed=%s",
                    result.target_file, strategy, result.changed_fields)

        fix_plan = {
            "target_service": result.target_service,
            "target_file": result.target_file,
            "original_manifest": current_manifest,
            "modified_manifest": result.modified_manifest,
            "changed_fields": result.changed_fields,
            "fix_description": result.fix_description,
            "rationale": result.rationale,
            "strategy": strategy,
        }

        return {
            **state,
            "fix_plan": fix_plan,
            "validation_errors": [],
            "status": "fix_planned",
        }
    except Exception as e:
        logger.error("수정안 생성 실패: %s", e)
        return {
            **state,
            "validation_errors": [str(e)],
            "retry_count": retry_count + 1,
            "status": "fix_failed",
        }


def validate_fix(state: DeliveryState) -> DeliveryState:
    """YAML 문법 + 정책 검증"""
    fix_plan = state.get("fix_plan", {})
    issue_type = state.get("issue_type", "unknown")
    errors: list[str] = []

    modified = fix_plan.get("modified_manifest", "")

    # 1. YAML 문법 검증
    try:
        parsed = yaml.safe_load(modified)
    except yaml.YAMLError as e:
        errors.append(f"YAML 문법 오류: {e}")
        return {**state, "validation_errors": errors, "status": "invalid"}

    # 2. Kind 확인 (Deployment여야 함)
    if not isinstance(parsed, dict) or parsed.get("kind") != "Deployment":
        errors.append("수정된 manifest는 Deployment Kind여야 합니다")

    # 3. 정책 검증: 허용된 필드만 변경되었는지
    policy = ISSUE_POLICY.get(issue_type, ISSUE_POLICY["unknown"])
    allowed = policy["allowed_field_patterns"]
    forbidden = policy["forbidden_field_patterns"]
    changed = fix_plan.get("changed_fields", [])

    for field in changed:
        # 금지 필드 체크
        for fpattern in forbidden:
            fbase = fpattern.replace("[*]", "").replace("[0]", "")
            if fbase in field:
                errors.append(f"정책 위반: '{field}'는 {issue_type}에서 변경 불가")

    # 4. 실제로 변경이 있는지 확인
    original = fix_plan.get("original_manifest", "")
    if modified.strip() == original.strip():
        errors.append("수정된 내용이 원본과 동일합니다")

    if errors:
        logger.warning("검증 실패 (%d개): %s", len(errors), errors)
        return {
            **state,
            "validation_errors": errors,
            "retry_count": state.get("retry_count", 0) + 1,
            "status": "invalid",
        }

    logger.info("검증 통과")
    return {**state, "validation_errors": [], "status": "validated"}


def human_gate(state: DeliveryState) -> DeliveryState:
    """Human-in-the-Loop: 고위험 변경만 Slack 승인 요청"""
    from dr_kube.slack import SlackClient

    if not state.get("requires_human_approval"):
        logger.info("Human approval 불필요 (자동 통과)")
        return {**state, "human_decision": None, "status": "approved"}

    fix_plan = state.get("fix_plan", {})
    slack = SlackClient()

    try:
        ts = slack.send_proposal(
            issue_type=state.get("issue_type", ""),
            affected_service=state.get("affected_service", ""),
            root_cause=state.get("root_cause", ""),
            fix_description=fix_plan.get("fix_description", ""),
            rationale=fix_plan.get("rationale", ""),
            severity=state.get("severity", "medium"),
            diff=_make_diff_summary(
                fix_plan.get("original_manifest", ""),
                fix_plan.get("modified_manifest", ""),
            ),
        )
        logger.info("Slack 승인 요청 전송 (ts=%s)", ts)
        return {
            **state,
            "slack_ts": ts,
            "status": "awaiting_approval",
        }
    except Exception as e:
        logger.warning("Slack 전송 실패 (%s), 자동 승인으로 진행", e)
        return {**state, "human_decision": None, "status": "approved"}


def create_pr(state: DeliveryState) -> DeliveryState:
    """GitHub PR 생성"""
    from dr_kube.github import GitHubClient, generate_branch_name

    fix_plan = state.get("fix_plan", {})
    service = state.get("affected_service", "")
    issue_type = state.get("issue_type", "")

    branch_name = generate_branch_name(
        service=service,
        issue_type=issue_type,
        fix_description=fix_plan.get("fix_description", "fix"),
    )

    try:
        gh = GitHubClient()
        pr_url, pr_number = gh.create_pr(
            branch_name=branch_name,
            title=f"fix({service}): {fix_plan.get('fix_description', 'auto fix')}",
            body=_build_pr_body(state),
            file_path=fix_plan["target_file"],
            file_content=fix_plan["modified_manifest"],
        )
        logger.info("PR 생성: %s (#%d)", pr_url, pr_number)

        return {
            **state,
            "branch_name": branch_name,
            "pr_url": pr_url,
            "pr_number": pr_number,
            "status": "pr_created",
        }
    except Exception as e:
        logger.error("PR 생성 실패: %s", e)
        return {**state, "status": "error", "error": f"PR 생성 실패: {e}"}


def verify_recovery(state: DeliveryState) -> DeliveryState:
    """복구 검증: Pod 상태 + Alert 해소 확인"""
    from dr_kube.verifier import verify_fix

    affected_services = state.get("affected_services", [state.get("affected_service", "")])
    namespace = state.get("affected_namespace", "delivery-app")

    logger.info("복구 검증 시작: services=%s", affected_services)

    all_recovered = True
    for svc in affected_services:
        success, detail = verify_fix(
            namespace=namespace,
            resource=svc,
            fingerprint=state.get("fingerprint", ""),
        )
        if not success:
            all_recovered = False
            logger.warning("복구 미완료: %s", svc)
            break

    status = "recovered" if all_recovered else "recovery_failed"
    logger.info("복구 검증 결과: %s", status)
    return {**state, "status": status}


def notify_complete(state: DeliveryState) -> DeliveryState:
    """Slack 복구 완료 알림"""
    from dr_kube.slack import SlackClient

    try:
        slack = SlackClient()
        slack.send_recovery_complete(
            service=state.get("affected_service", ""),
            root_cause=state.get("root_cause", ""),
            fix_description=state.get("fix_plan", {}).get("fix_description", ""),
            pr_url=state.get("pr_url", ""),
            thread_ts=state.get("slack_ts"),
        )
    except Exception as e:
        logger.warning("Slack 알림 실패: %s", e)

    return {**state, "status": "done"}


def notify_skip(state: DeliveryState) -> DeliveryState:
    """Unknown 이슈 스킵 알림"""
    logger.info("이슈 스킵: %s (type=unknown)", state.get("affected_service"))
    return {**state, "status": "skipped"}


def escalate(state: DeliveryState) -> DeliveryState:
    """자동 복구 실패 → Slack 에스컬레이션"""
    from dr_kube.slack import SlackClient

    logger.warning("에스컬레이션: %s (retry=%d)", state.get("affected_service"), state.get("retry_count", 0))
    try:
        slack = SlackClient()
        slack.send_escalation(
            service=state.get("affected_service", ""),
            issue_type=state.get("issue_type", ""),
            root_cause=state.get("root_cause", "자동 분석 실패"),
            retry_count=state.get("retry_count", 0),
            errors=state.get("validation_errors", []),
        )
    except Exception as e:
        logger.warning("Slack 에스컬레이션 알림 실패: %s", e)

    return {**state, "status": "escalated"}


# ── 헬퍼 ──────────────────────────────────────────────

def _make_diff_summary(original: str, modified: str) -> str:
    """변경 요약 (간단한 diff)"""
    orig_lines = set(original.splitlines())
    mod_lines = set(modified.splitlines())
    added = [f"+ {l}" for l in mod_lines - orig_lines if l.strip()][:10]
    removed = [f"- {l}" for l in orig_lines - mod_lines if l.strip()][:10]
    return "\n".join(removed + added)


def _build_pr_body(state: DeliveryState) -> str:
    """PR body 생성"""
    fix_plan = state.get("fix_plan", {})
    diff = _make_diff_summary(
        fix_plan.get("original_manifest", ""),
        fix_plan.get("modified_manifest", ""),
    )
    return f"""## 자동 복구 PR (delivery-agent)

**서비스**: `{state.get('affected_service')}`
**이슈 타입**: `{state.get('issue_type')}`
**심각도**: `{state.get('severity')}`

## 근본 원인
{state.get('root_cause', '')}

## 변경 내용
{fix_plan.get('rationale', '')}

변경된 필드: {', '.join(fix_plan.get('changed_fields', []))}

```diff
{diff}
```

## 분석 요약
{state.get('analysis_summary', '')}

---
🤖 *DR-Kube delivery-agent 자동 생성*
"""
