"""LangGraph 그래프 정의

워크플로우:
  with_pr=True:
    load_issue → investigate(LLM+tools) → analyze_and_fix → validate → create_pr → END
                                                              ↓ 실패 (< 3회)
                                                            analyze_and_fix (재시도)
                                                              ↓ 실패 (>= 3회)
                                                            error_end → END
  with_pr=False:
    load_issue → investigate → analyze_and_fix → END
"""
import json
import logging
import os
import re
import yaml
from pathlib import Path
from langgraph.graph import StateGraph, END
from dr_kube.state import IssueState
from dr_kube.llm import get_llm
from dr_kube.prompts import (
    INVESTIGATE_PROMPT,
    ANALYZE_AND_FIX_PROMPT,
    ANALYZE_ONLY_PROMPT,
    ARGOCD_ANALYZE_PROMPT,
)
from dr_kube.tools import ALL_TOOLS
from dr_kube.github import GitHubClient, generate_branch_name, generate_pr_body

logger = logging.getLogger("dr-kube-investigate")

MAX_INVESTIGATE_ITERATIONS = int(os.getenv("MAX_INVESTIGATE_ITERATIONS", "5"))

# 프로젝트 루트 경로 (agent/dr_kube/graph.py → dr-kube/)
PROJECT_ROOT = Path(__file__).parent.parent.parent

MAX_RETRIES = 3
POLICY_RESTRICTED_TYPES = {"pod_crash", "service_error", "upstream_error", "service_down"}
POLICY_DENY_TOKENS = {"resources", "limits", "requests", "memory", "cpu"}
POLICY_ALLOW_TOKENS = {
    "replica",
    "replicas",
    "poddisruptionbudget",
    "pdb",
    "timeout",
    "retry",
    "retries",
    "backoff",
    "circuitbreaker",
    "connectionpool",
    "maxretries",
    "maxconnections",
}
RESOURCE_KEY_MAP = {
    "redis-cart": "redis",
}
RELATED_SERVICES = {
    "checkoutservice": ["paymentservice", "redis"],
    "paymentservice": ["checkoutservice"],
    "redis": ["checkoutservice"],
    "redis-cart": ["checkoutservice"],
    "frontend": ["checkoutservice", "productcatalogservice"],
}


# =============================================================================
# 헬퍼 함수
# =============================================================================

def _extract_llm_content(response) -> str:
    """LLM 응답에서 텍스트 추출 (Gemini/Ollama 호환)"""
    if isinstance(response.content, list):
        content = response.content[0] if response.content else ""
        if isinstance(content, dict) and "text" in content:
            return content["text"]
        elif hasattr(content, "text"):
            return content.text
        return str(content)
    elif isinstance(response.content, str):
        return response.content
    return str(response.content)


def _parse_field(text: str, pattern: str) -> str:
    """정규식으로 필드 추출"""
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _parse_severity(text: str) -> str:
    """심각도 파싱"""
    match = re.search(r"심각도:\s*(critical|high|medium|low)", text, re.IGNORECASE)
    return match.group(1).lower() if match else "medium"


def _parse_suggestions(text: str) -> list[str]:
    """해결책 목록 파싱"""
    matches = re.findall(r"^\d+\.\s*(.+)$", text, re.MULTILINE)
    return [s.strip() for s in matches if s.strip()][:3]


def _parse_yaml_block(text: str) -> str:
    """YAML 코드 블록 추출"""
    match = re.search(r"```yaml\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def _normalize_resource_key(resource: str) -> str:
    return RESOURCE_KEY_MAP.get(resource, resource)


def _apply_replica_bumps_text(original_yaml: str, targets: list[str]) -> tuple[str, list[str]]:
    """원본 YAML 텍스트에서 target 서비스의 replicas만 최소 변경."""
    lines = original_yaml.splitlines()
    changed: list[str] = []
    current_top_key = ""
    target_set = set(targets)

    for idx, line in enumerate(lines):
        # top-level key 추적 (들여쓰기 없는 "key:")
        if re.match(r"^[a-zA-Z0-9_-]+:\s*$", line):
            current_top_key = line.rstrip(":").strip()
            continue

        if current_top_key not in target_set:
            continue

        m = re.match(r"^(\s{2}replicas:\s*)(\d+)(\s*(#.*)?)$", line)
        if not m:
            continue

        cur = int(m.group(2))
        new_val = min(max(cur + 1, 2), 4)
        if new_val == cur:
            continue
        lines[idx] = f"{m.group(1)}{new_val}{m.group(3)}"
        if current_top_key not in changed:
            changed.append(current_top_key)

    return "\n".join(lines), changed


def _rule_based_fix(issue: dict, original_yaml: str) -> tuple[str, str, str] | None:
    """정책 기반 수정안 생성.

    Returns:
      (fix_content, fix_description, root_cause) or None
    """
    issue_type = issue.get("type", "unknown")
    if issue_type not in POLICY_RESTRICTED_TYPES | {"composite_incident"}:
        return None
    if issue_type == "composite_incident":
        # 복합 장애는 규칙 기반 replicas-only를 피하고 LLM이 다중 완화책을 생성하게 한다.
        return None

    try:
        values_data = yaml.safe_load(original_yaml)
    except yaml.YAMLError:
        values_data = {}
    if not isinstance(values_data, dict):
        values_data = {}

    changed_targets: list[str] = []

    resource = _normalize_resource_key(issue.get("resource", ""))
    targets = [resource] if resource in (values_data or {}) else []
    for rel in RELATED_SERVICES.get(resource, []):
        if rel in (values_data or {}) and rel not in targets:
            targets.append(rel)
        if len(targets) >= 2:
            break

    fix_content, changed_targets = _apply_replica_bumps_text(original_yaml, targets)

    # 실제 변경이 없다면 규칙 기반 실패로 간주
    if not changed_targets:
        return None
    fix_description = f"scale replicas for {', '.join(changed_targets[:2])}"
    root_cause = (
        f"서비스 가용성 저하({issue_type})가 감지되어 "
        f"핵심 경로 서비스({', '.join(changed_targets)}) 레플리카를 증설했습니다."
    )
    return fix_content, fix_description[:60], root_cause


def _collect_changed_paths(original, modified, prefix: str = "") -> list[str]:
    """두 YAML 객체 간 변경 경로를 수집."""
    paths: list[str] = []

    if isinstance(original, dict) and isinstance(modified, dict):
        keys = set(original.keys()) | set(modified.keys())
        for key in keys:
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            if key not in original or key not in modified:
                paths.append(next_prefix)
                continue
            paths.extend(_collect_changed_paths(original[key], modified[key], next_prefix))
        return paths

    if isinstance(original, list) and isinstance(modified, list):
        if original != modified:
            paths.append(f"{prefix}[]")
        return paths

    if original != modified:
        paths.append(prefix or "<root>")
    return paths


def _path_tokens(path: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", path.lower()) if t}


def _validate_remediation_policy(issue_type: str, changed_paths: list[str]) -> str:
    """장애 타입별 허용/금지 변경 정책 검사.

    반환값:
      - 정책 위반 메시지(str): 위반
      - 빈 문자열: 통과
    """
    if issue_type == "composite_incident":
        # 복합 인시던트는 최소 2개 이상의 독립 변경 필요
        unique_roots = {p.split(".", 1)[0] for p in changed_paths if p}
        if len(unique_roots) < 2 and len(changed_paths) < 2:
            return "정책 위반: composite_incident 는 최소 2개 이상의 독립 변경이 필요합니다."

        has_only_resource_tuning = True
        for path in changed_paths:
            tokens = _path_tokens(path)
            if not (tokens & POLICY_DENY_TOKENS):
                has_only_resource_tuning = False
                break
        if has_only_resource_tuning:
            return "정책 위반: composite_incident 에서 리소스 튜닝 단독 변경은 금지됩니다."
        return ""

    if issue_type not in POLICY_RESTRICTED_TYPES:
        return ""

    # 금지: 리소스 상향(memory/cpu/limits/requests/resources)
    for path in changed_paths:
        tokens = _path_tokens(path)
        if tokens & POLICY_DENY_TOKENS:
            return (
                f"정책 위반: issue_type={issue_type} 에서 리소스 튜닝 변경({path})은 금지됩니다. "
                "replicas/PDB/timeout/retry/circuit-breaker 계열만 허용됩니다."
            )

    # 허용 계열 변경이 최소 1개는 있어야 함
    has_allowed = False
    for path in changed_paths:
        tokens = _path_tokens(path)
        if tokens & POLICY_ALLOW_TOKENS:
            has_allowed = True
            break

    if not has_allowed:
        return (
            f"정책 위반: issue_type={issue_type} 는 replicas/PDB/timeout/retry/circuit-breaker "
            "계열 변경을 포함해야 합니다."
        )

    return ""


# =============================================================================
# 노드 함수
# =============================================================================

def load_issue(state: IssueState) -> IssueState:
    """이슈 파일 로드 + target_file 해석 + original_yaml 읽기"""
    if state.get("issue_data"):
        issue_data = state["issue_data"]
    else:
        try:
            with open(state["issue_file"], "r", encoding="utf-8") as f:
                issue_data = json.load(f)
        except Exception as e:
            return {"error": str(e), "status": "error"}

    # target_file 결정 (이슈에 명시된 값 우선, 없으면 converter에서 추론)
    target_file = issue_data.get("values_file", "")
    if not target_file:
        from dr_kube.converter import derive_values_file
        target_file = derive_values_file(
            issue_data.get("resource", ""),
            issue_data.get("namespace", ""),
        )

    # original_yaml 읽기
    original_yaml = ""
    if target_file:
        target_path = PROJECT_ROOT / target_file
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8") as f:
                original_yaml = f.read()
        else:
            target_file = ""  # 파일 없으면 analyze-only 전환

    return {
        "issue_data": issue_data,
        "target_file": target_file,
        "original_yaml": original_yaml,
        "retry_count": 0,
        "status": "loaded",
    }


def investigate(state: IssueState) -> IssueState:
    """LLM + tools: alert 기반으로 Loki/Prometheus/K8s를 조회하여 증거 수집"""
    if state.get("status") == "error":
        return state

    issue = state["issue_data"]
    alert_id = issue.get("id", "unknown")
    issue_type = issue.get("type", "unknown")
    resource = issue.get("resource", "unknown")
    namespace = issue.get("namespace", "default")
    logs_text = "\n".join(issue.get("logs", []))

    logger.info("[investigate] investigation start: alert_id=%s type=%s resource=%s",
                alert_id, issue_type, resource)

    prompt = INVESTIGATE_PROMPT.format(
        type=issue_type,
        namespace=namespace,
        resource=resource,
        error_message=issue.get("error_message", ""),
        logs=logs_text,
    )

    try:
        llm = get_llm()
        llm_with_tools = llm.bind_tools(ALL_TOOLS)
    except Exception as e:
        logger.error("[investigate] LLM/tool binding failed: %s", e)
        return {
            "investigation_summary": f"investigation failed: {e}",
            "unavailable_evidence": ["LLM tool binding failed"],
            "status": "investigated",
        }

    messages = [{"role": "user", "content": prompt}]
    evidence_logs: list[str] = []
    evidence_metrics: dict = {}
    evidence_pod_status: dict = {}
    unavailable: list[str] = []
    tool_map = {t.name: t for t in ALL_TOOLS}
    investigation_summary = ""

    for iteration in range(1, MAX_INVESTIGATE_ITERATIONS + 1):
        logger.info("[investigate] iteration %d/%d", iteration, MAX_INVESTIGATE_ITERATIONS)
        try:
            response = llm_with_tools.invoke(messages)
        except Exception as e:
            logger.error("[investigate] LLM invoke failed at iteration %d: %s", iteration, e)
            unavailable.append(f"LLM invoke failed at iteration {iteration}: {e}")
            break

        if not response.tool_calls:
            investigation_summary = _extract_llm_content(response)
            logger.info("[investigate] LLM decided to finish investigation")
            break

        messages.append(response)

        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            logger.info("[investigate] LLM decided: call %s(%s)", tool_name, json.dumps(tool_args, ensure_ascii=False))

            tool_fn = tool_map.get(tool_name)
            if not tool_fn:
                err_msg = f"Unknown tool: {tool_name}"
                logger.warning("[investigate] %s", err_msg)
                messages.append({"role": "tool", "content": err_msg, "tool_call_id": tc["id"]})
                continue

            try:
                tool_result = tool_fn.invoke(tool_args)
            except Exception as e:
                tool_result = json.dumps({"error": f"Tool execution error: {e}"})
                logger.warning("[investigate] tool_call: %s -> exception (%s)", tool_name, e)

            messages.append({"role": "tool", "content": str(tool_result), "tool_call_id": tc["id"]})

            _collect_evidence(
                tool_name, tool_args, tool_result,
                evidence_logs, evidence_metrics, evidence_pod_status, unavailable,
            )
    else:
        logger.info("[investigate] max iterations (%d) reached", MAX_INVESTIGATE_ITERATIONS)

    success_count = sum([
        1 if evidence_logs else 0,
        1 if evidence_metrics else 0,
        1 if evidence_pod_status else 0,
    ])
    total_sources = 3
    logger.info("[investigate] investigation complete: success %d/%d, failures: %s",
                success_count, total_sources,
                unavailable if unavailable else "none")
    if investigation_summary:
        logger.info("[investigate] investigation_summary: %s", investigation_summary[:200])

    return {
        "evidence_logs": evidence_logs,
        "evidence_metrics": evidence_metrics,
        "evidence_pod_status": evidence_pod_status,
        "investigation_summary": investigation_summary,
        "unavailable_evidence": unavailable,
        "status": "investigated",
    }


def _collect_evidence(
    tool_name: str, tool_args: dict, tool_result: str,
    evidence_logs: list[str], evidence_metrics: dict,
    evidence_pod_status: dict, unavailable: list[str],
) -> None:
    """Parse tool result and dispatch to the appropriate evidence bucket."""
    try:
        parsed = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
    except (json.JSONDecodeError, TypeError):
        parsed = {"raw": str(tool_result)}

    has_error = isinstance(parsed, dict) and "error" in parsed
    is_empty = isinstance(parsed, dict) and parsed.get("count", -1) == 0

    if tool_name == "query_loki_logs":
        if has_error or is_empty:
            desc = parsed.get("error") or parsed.get("note", "empty result")
            unavailable.append(f"Loki logs ({tool_args.get('app', '?')}, pattern={tool_args.get('pattern', '?')}): {desc}")
        elif isinstance(parsed, dict):
            for line in parsed.get("result", []):
                if line not in evidence_logs:
                    evidence_logs.append(line)

    elif tool_name == "query_prometheus":
        if has_error or is_empty:
            desc = parsed.get("error") or parsed.get("note", "empty result")
            unavailable.append(f"Prometheus ({tool_args.get('query', '?')}): {desc}")
        elif isinstance(parsed, dict):
            query_key = tool_args.get("query", "unknown")[:80]
            evidence_metrics[query_key] = parsed.get("result", [])

    elif tool_name == "get_pod_status":
        if has_error or is_empty:
            desc = parsed.get("error") or parsed.get("note", "empty result")
            unavailable.append(f"Pod status ({tool_args.get('app', '?')}): {desc}")
        elif isinstance(parsed, dict):
            app_key = tool_args.get("app", "unknown")
            evidence_pod_status[app_key] = parsed.get("result", [])


def _format_evidence(state: IssueState) -> tuple[str, str]:
    """Format evidence and unavailable info into prompt-ready strings."""
    parts = []

    logs = state.get("evidence_logs", [])
    if logs:
        parts.append("### Loki Logs")
        for line in logs[:30]:
            parts.append(f"  - {line[:300]}")

    metrics = state.get("evidence_metrics", {})
    if metrics:
        parts.append("### Prometheus Metrics")
        for query, results in metrics.items():
            parts.append(f"  Query: {query}")
            for r in results[:10]:
                if isinstance(r, dict):
                    metric_labels = r.get("metric", {})
                    value = r.get("value", "N/A")
                    parts.append(f"    {metric_labels} = {value}")
                else:
                    parts.append(f"    {r}")

    pod_status = state.get("evidence_pod_status", {})
    if pod_status:
        parts.append("### Pod Status")
        for app, pods in pod_status.items():
            parts.append(f"  App: {app}")
            for p in pods[:5]:
                if isinstance(p, dict):
                    parts.append(f"    {p.get('name', '?')}: phase={p.get('phase', '?')}, "
                                 f"containers={p.get('containers', [])}, "
                                 f"failedConditions={p.get('failedConditions', [])}")

    summary = state.get("investigation_summary", "")
    if summary:
        parts.append(f"### Investigation Summary\n{summary}")

    evidence_text = "\n".join(parts) if parts else "No evidence collected."

    unavailable_list = state.get("unavailable_evidence", [])
    unavailable_text = "\n".join(f"- {item}" for item in unavailable_list) if unavailable_list else "None"

    return evidence_text, unavailable_text


def analyze_and_fix(state: IssueState) -> IssueState:
    """LLM 1회 호출로 이슈 분석 + YAML 수정안 생성"""
    if state.get("status") == "error":
        return state

    issue = state["issue_data"]
    issue_type = issue.get("type", "")
    target_file = state.get("target_file", "")
    original_yaml = state.get("original_yaml", "")
    logs_text = "\n".join(issue.get("logs", []))

    # ArgoCD 이벤트: 전용 프롬프트로 분석만 수행, PR 경로 타지 않음
    if issue_type.startswith("argocd_"):
        return _analyze_argocd(state)

    # target_file이 없으면 분석만 수행
    if not target_file or not original_yaml:
        return _analyze_only(state)

    # PR 품질 안정화를 위해 crash/error 계열은 규칙 기반 우선 처리
    rule_result = _rule_based_fix(issue, original_yaml)
    if rule_result is not None:
        fix_content, fix_description, root_cause = rule_result
        return {
            "analysis": f"rule_based_fix applied for {issue.get('type', 'unknown')}",
            "root_cause": root_cause,
            "severity": "high",
            "suggestions": [
                "서비스 레플리카를 증설해 단일 장애점(SPOF)을 줄였습니다.",
                "후속으로 timeout/retry 정책을 서비스 코드/차트에 반영하세요.",
            ],
            "fix_content": fix_content,
            "fix_description": fix_description,
            "status": "analyzed",
        }

    evidence_text, unavailable_text = _format_evidence(state)

    prompt = ANALYZE_AND_FIX_PROMPT.format(
        type=issue.get("type", "unknown"),
        namespace=issue.get("namespace", "default"),
        resource=issue.get("resource", "unknown"),
        error_message=issue.get("error_message", ""),
        logs=logs_text,
        evidence=evidence_text,
        unavailable=unavailable_text,
        target_file=target_file,
        current_yaml=original_yaml,
    )

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        result = _extract_llm_content(response)

        # 파싱
        root_cause = _parse_field(result, r"근본 원인:\s*(.+?)(?:\n|$)")
        severity = _parse_severity(result)
        suggestions = _parse_suggestions(result)
        fix_content = _parse_yaml_block(result)
        fix_description = _parse_field(result, r"변경 설명:\s*(.+?)(?:\n|$)") or "자동 생성된 수정안"

        if not fix_content:
            return {
                "analysis": result,
                "root_cause": root_cause or "분석 결과를 파싱할 수 없습니다",
                "severity": severity,
                "suggestions": suggestions,
                "error": "LLM 응답에서 YAML 블록을 추출할 수 없습니다",
                "status": "error",
            }

        return {
            "analysis": result,
            "root_cause": root_cause or "분석 결과를 파싱할 수 없습니다",
            "severity": severity,
            "suggestions": suggestions or ["로그를 더 확인하세요"],
            "fix_content": fix_content,
            "fix_description": fix_description,
            "status": "analyzed",
        }
    except Exception as e:
        return {"error": f"분석 + 수정안 생성 실패: {str(e)}", "status": "error"}


def _analyze_argocd(state: IssueState) -> IssueState:
    """ArgoCD 이벤트 전용: ARGOCD_ANALYZE_PROMPT로 분석만 수행, status done으로 PR 경로 미진입"""
    issue = state["issue_data"]
    logs_text = "\n".join(issue.get("logs", []))

    prompt = ARGOCD_ANALYZE_PROMPT.format(
        type=issue.get("type", "unknown"),
        namespace=issue.get("namespace", "default"),
        resource=issue.get("resource", "unknown"),
        error_message=issue.get("error_message", ""),
        logs=logs_text,
    )

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        result = _extract_llm_content(response)
        return {
            "analysis": result,
            "root_cause": _parse_field(result, r"근본 원인:\s*(.+?)(?:\n|$)") or "분석 결과를 파싱할 수 없습니다",
            "severity": _parse_severity(result),
            "suggestions": _parse_suggestions(result) or ["로그를 더 확인하세요"],
            "status": "done",
        }
    except Exception as e:
        return {"error": f"ArgoCD 분석 실패: {str(e)}", "status": "error"}


def _analyze_only(state: IssueState) -> IssueState:
    """values 파일이 없는 이슈의 분석만 수행"""
    issue = state["issue_data"]
    logs_text = "\n".join(issue.get("logs", []))
    evidence_text, unavailable_text = _format_evidence(state)

    prompt = ANALYZE_ONLY_PROMPT.format(
        type=issue.get("type", "unknown"),
        namespace=issue.get("namespace", "default"),
        resource=issue.get("resource", "unknown"),
        error_message=issue.get("error_message", ""),
        logs=logs_text,
        evidence=evidence_text,
        unavailable=unavailable_text,
    )

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        result = _extract_llm_content(response)

        return {
            "analysis": result,
            "root_cause": _parse_field(result, r"근본 원인:\s*(.+?)(?:\n|$)") or "분석 결과를 파싱할 수 없습니다",
            "severity": _parse_severity(result),
            "suggestions": _parse_suggestions(result) or ["로그를 더 확인하세요"],
            "status": "done",
        }
    except Exception as e:
        return {"error": f"분석 실패: {str(e)}", "status": "error"}


def validate(state: IssueState) -> IssueState:
    """YAML 수정안 검증: 문법 + 변경 확인"""
    fix_content = state.get("fix_content", "")
    original_yaml = state.get("original_yaml", "")
    retry_count = state.get("retry_count", 0)

    # 1. YAML 문법 검증
    try:
        parsed = yaml.safe_load(fix_content)
        if parsed is None:
            return {"retry_count": retry_count + 1, "error": "YAML 파싱 결과가 비어있습니다", "status": "validation_failed"}
    except yaml.YAMLError as e:
        return {"retry_count": retry_count + 1, "error": f"YAML 문법 오류: {str(e)}", "status": "validation_failed"}

    issue = state.get("issue_data", {})
    issue_type = issue.get("type", "unknown")
    original_parsed = None

    # 2. 원본과 동일한지 확인
    try:
        original_parsed = yaml.safe_load(original_yaml)
        if parsed == original_parsed:
            return {"retry_count": retry_count + 1, "error": "수정안이 원본과 동일합니다", "status": "validation_failed"}
    except yaml.YAMLError:
        pass  # 원본 파싱 실패해도 수정안 검증은 통과

    # 3. dict 형식인지 확인
    if not isinstance(parsed, dict):
        return {"retry_count": retry_count + 1, "error": "YAML이 dict 형식이 아닙니다", "status": "validation_failed"}

    # 4. 장애 타입별 수정 정책 검증
    if issue_type in POLICY_RESTRICTED_TYPES:
        if not isinstance(original_parsed, dict):
            return {
                "retry_count": retry_count + 1,
                "error": f"정책 검증 실패: issue_type={issue_type} 는 원본 YAML 파싱이 필요합니다",
                "status": "validation_failed",
            }

        changed_paths = _collect_changed_paths(original_parsed, parsed)
        policy_error = _validate_remediation_policy(issue_type, changed_paths)
        if policy_error:
            return {
                "retry_count": retry_count + 1,
                "error": policy_error,
                "status": "validation_failed",
            }

    return {"status": "validated"}


def error_end(state: IssueState) -> IssueState:
    """에러 상태로 워크플로우 종료"""
    retry_count = state.get("retry_count", 0)
    error_msg = state.get("error", "알 수 없는 오류")
    if retry_count >= MAX_RETRIES:
        error_msg = f"검증 {MAX_RETRIES}회 실패 후 종료: {error_msg}"
    return {"status": "error", "error": error_msg}


def create_pr(state: IssueState) -> IssueState:
    """GitHub PR 생성"""
    if state.get("error"):
        return state

    issue = state.get("issue_data", {})
    target_file = state.get("target_file", "")
    fix_content = state.get("fix_content", "")

    if not target_file or not fix_content:
        return {"error": "수정할 파일 또는 내용이 없습니다", "status": "error"}

    # 브랜치명 생성
    branch_name = generate_branch_name(
        issue.get("type", "fix"), issue.get("resource", "unknown")
    )

    # GitHub 클라이언트
    gh = GitHubClient(str(PROJECT_ROOT))

    try:
        # 1. 브랜치 생성
        success, msg = gh.create_branch(branch_name)
        if not success:
            return {"error": f"브랜치 생성 실패: {msg}", "status": "error"}

        # 2. 파일 수정
        target_path = PROJECT_ROOT / target_file
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(fix_content)

        # 3. 커밋 및 푸시
        commit_message = f"fix({issue.get('resource', 'unknown')}): {state.get('fix_description', '자동 수정')}"
        success, msg = gh.commit_and_push(target_file, commit_message, branch_name)
        if not success:
            gh.cleanup()
            return {"error": f"커밋/푸시 실패: {msg}", "status": "error"}

        # 4. PR 생성
        pr_title = f"fix({issue.get('resource', 'unknown')}): {state.get('fix_description', '자동 수정')}"
        pr_body = generate_pr_body(state)
        success, pr_url, pr_number = gh.create_pr(branch_name, pr_title, pr_body)

        # main으로 복귀
        gh.cleanup()

        if not success:
            return {"error": f"PR 생성 실패: {pr_url}", "status": "error"}

        return {
            "branch_name": branch_name,
            "pr_url": pr_url,
            "pr_number": pr_number,
            "status": "pr_created",
        }
    except Exception as e:
        gh.cleanup()
        return {"error": f"PR 생성 중 오류: {str(e)}", "status": "error"}


# =============================================================================
# 라우팅 함수
# =============================================================================

def _should_create_pr(state: IssueState) -> str:
    """analyze_and_fix 후 라우팅"""
    if state.get("status") == "error":
        return "error_end"
    if state.get("status") == "done":
        return "end"  # 분석만 수행 완료
    return "validate"


def _should_retry(state: IssueState) -> str:
    """validate 후 라우팅"""
    if state.get("status") == "validated":
        return "create_pr"
    if state.get("retry_count", 0) >= MAX_RETRIES:
        return "error_end"
    return "retry"


# =============================================================================
# 그래프 생성
# =============================================================================

def create_graph(with_pr: bool = False):
    """LangGraph 워크플로우 생성

    Args:
        with_pr: True면 PR 생성까지 포함, False면 분석만
    """
    workflow = StateGraph(IssueState)

    workflow.add_node("load_issue", load_issue)
    workflow.add_node("investigate", investigate)
    workflow.add_node("analyze_and_fix", analyze_and_fix)

    if with_pr:
        workflow.add_node("validate", validate)
        workflow.add_node("create_pr", create_pr)
        workflow.add_node("error_end", error_end)

        workflow.set_entry_point("load_issue")
        workflow.add_edge("load_issue", "investigate")
        workflow.add_edge("investigate", "analyze_and_fix")

        workflow.add_conditional_edges(
            "analyze_and_fix",
            _should_create_pr,
            {"validate": "validate", "end": END, "error_end": "error_end"},
        )

        workflow.add_conditional_edges(
            "validate",
            _should_retry,
            {"create_pr": "create_pr", "retry": "analyze_and_fix", "error_end": "error_end"},
        )

        workflow.add_edge("create_pr", END)
        workflow.add_edge("error_end", END)
    else:
        workflow.set_entry_point("load_issue")
        workflow.add_edge("load_issue", "investigate")
        workflow.add_edge("investigate", "analyze_and_fix")
        workflow.add_edge("analyze_and_fix", END)

    return workflow.compile()
