"""LangGraph 그래프 정의

워크플로우:
  with_pr=True:
    load_issue → classify_issue → [route]
      ├── argocd/analyze_only → analyze_only → END
      ├── rule_based → rule_based_fix → (실패 시 llm_fix) → validate → create_pr → END
      └── llm → llm_fix → validate → create_pr → END
                              ↑ (validate 실패, retry < 3)
                              └── (retry >= 3 → error_end)

  with_pr=False:
    load_issue → classify_issue → [route]
      ├── argocd/analyze_only → analyze_only → END
      ├── rule_based → rule_based_fix → END
      └── llm → llm_fix → END
"""
import json
import re
import yaml
from pathlib import Path
from langgraph.graph import StateGraph, END
from dr_kube.state import IssueState
from dr_kube.llm import get_llm
from dr_kube.prompts import LLM_FIX_PROMPT, ANALYZE_ONLY_PROMPT, ARGOCD_ANALYZE_PROMPT, PR_REVIEW_RESPONSE_PROMPT, SOURCE_AND_VALUES_FIX_PROMPT
from dr_kube.github import GitHubClient, generate_branch_name, generate_pr_body

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


def _parse_root_cause(text: str) -> str:
    """근본 원인 추출 - 콜론 뒤 같은 줄 또는 다음 줄 모두 대응.

    LLM이 **근본 원인:** 처럼 bold 마크다운을 쓰거나 영어로 응답하는 경우도 처리.
    """
    # 마크다운 bold/italic 제거 후 파싱
    clean = re.sub(r"\*+", "", text)
    # 한국어 패턴
    match = re.search(
        r"근본 원인:[^\S\n]*\n?([^\n]+(?:\n(?!심각도:|해결책:|```)[^\n]+)*)",
        clean,
        re.MULTILINE,
    )
    if match:
        return match.group(1).strip()
    # 영어 폴백: "Root Cause:" or "Root cause:"
    match = re.search(
        r"Root [Cc]ause:[^\S\n]*\n?([^\n]+(?:\n(?!Severity:|Solution:|```)[^\n]+)*)",
        clean,
        re.MULTILINE,
    )
    if match:
        return match.group(1).strip()
    return ""


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


def _parse_python_block(text: str) -> str:
    """Python 코드 블록 추출"""
    match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
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


def _try_rule_based_fix(issue: dict, original_yaml: str) -> tuple[str, str, str] | None:
    """정책 기반 수정안 생성 (LLM 없음).

    Returns:
      (fix_content, fix_description, root_cause) or None if not applicable
    """
    issue_type = issue.get("type", "unknown")
    if issue_type not in POLICY_RESTRICTED_TYPES | {"composite_incident"}:
        return None
    if issue_type == "composite_incident":
        # 복합 장애는 LLM이 다중 완화책을 생성하게 한다
        return None

    try:
        values_data = yaml.safe_load(original_yaml)
    except yaml.YAMLError:
        values_data = {}
    if not isinstance(values_data, dict):
        values_data = {}

    resource = _normalize_resource_key(issue.get("resource", ""))
    targets = [resource] if resource in (values_data or {}) else []
    for rel in RELATED_SERVICES.get(resource, []):
        if rel in (values_data or {}) and rel not in targets:
            targets.append(rel)
        if len(targets) >= 2:
            break

    fix_content, changed_targets = _apply_replica_bumps_text(original_yaml, targets)

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
        unique_roots = {p.split(".", 1)[0] for p in changed_paths if p}
        # 복합 장애는 최소 2개 이상의 서로 다른 서비스에 변경이 있어야 함
        if len(unique_roots) < 2:
            return (
                "정책 위반: composite_incident 는 최소 2개 이상의 서로 다른 서비스에 걸친 변경이 필요합니다. "
                f"현재 변경된 서비스: {sorted(unique_roots) or '없음'}"
            )

        has_only_resource_tuning = True
        for path in changed_paths:
            tokens = _path_tokens(path)
            if not (tokens & POLICY_DENY_TOKENS):
                has_only_resource_tuning = False
                break
        if has_only_resource_tuning:
            return "정책 위반: composite_incident 에서 리소스 튜닝 단독 변경은 금지됩니다. replicas/probe/timeout 계열을 포함하세요."
        return ""

    if issue_type not in POLICY_RESTRICTED_TYPES:
        return ""

    for path in changed_paths:
        tokens = _path_tokens(path)
        if tokens & POLICY_DENY_TOKENS:
            return (
                f"정책 위반: issue_type={issue_type} 에서 리소스 튜닝 변경({path})은 금지됩니다. "
                "replicas/PDB/timeout/retry/circuit-breaker 계열만 허용됩니다."
            )

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
        from dr_kube.converter import derive_values_file, derive_source_file
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
            target_file = ""  # 파일 없으면 analyze_only로 전환

    # source_file 결정 및 원본 읽기 (DR-Kube 커스텀 서비스)
    from dr_kube.converter import derive_source_file
    source_file = derive_source_file(issue_data.get("resource", ""))
    original_source = ""
    if source_file:
        source_path = PROJECT_ROOT / source_file
        if source_path.exists():
            with open(source_path, "r", encoding="utf-8") as f:
                original_source = f.read()

    # 수정 요청 시 주입된 review 컨텍스트 추출 (webhook이 issue_data에 임시 삽입)
    pr_review_comment = issue_data.pop("_review_comment", "")
    previous_fix_content = issue_data.pop("_previous_fix", "")

    return {
        "issue_data": issue_data,
        "target_file": target_file,
        "original_yaml": original_yaml,
        "source_file": source_file,
        "original_source": original_source,
        "retry_count": 0,
        "pr_review_comment": pr_review_comment,
        "previous_fix_content": previous_fix_content,
        "status": "loaded",
    }


def classify_issue(state: IssueState) -> IssueState:
    """이슈 유형 + target_file 기반으로 처리 경로(route) 결정.

    route 값:
      - argocd: ArgoCD 이벤트 → analyze_only (전용 프롬프트)
      - analyze_only: values 파일 없음 → analyze_only
      - rule_based: POLICY_RESTRICTED_TYPES → rule_based_fix 우선
      - llm: 그 외 → llm_fix
    """
    if state.get("status") == "error":
        return state

    issue = state.get("issue_data", {})
    issue_type = issue.get("type", "")
    target_file = state.get("target_file", "")
    original_yaml = state.get("original_yaml", "")

    if issue_type.startswith("argocd_"):
        route = "argocd"
    elif not target_file or not original_yaml:
        route = "analyze_only"
    elif issue_type in POLICY_RESTRICTED_TYPES:
        route = "rule_based"
    else:
        route = "llm"

    return {"route": route, "status": "classified"}


def analyze_only(state: IssueState) -> IssueState:
    """LLM 분석만 수행 (YAML 수정 없음).

    ArgoCD 이벤트와 values 파일이 없는 이슈를 공통으로 처리.
    """
    if state.get("status") == "error":
        return state

    issue = state["issue_data"]
    issue_type = issue.get("type", "")
    logs_text = "\n".join(issue.get("logs", []))

    if issue_type.startswith("argocd_"):
        prompt = ARGOCD_ANALYZE_PROMPT.format(
            type=issue_type,
            namespace=issue.get("namespace", "default"),
            resource=issue.get("resource", "unknown"),
            error_message=issue.get("error_message", ""),
            logs=logs_text,
        )
    else:
        prompt = ANALYZE_ONLY_PROMPT.format(
            type=issue_type,
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
            "root_cause": _parse_root_cause(result) or "분석 결과를 파싱할 수 없습니다",
            "severity": _parse_severity(result),
            "suggestions": _parse_suggestions(result) or ["로그를 더 확인하세요"],
            "fix_method": "none",
            "status": "done",
        }
    except Exception as e:
        return {"error": f"분석 실패: {str(e)}", "status": "error"}


def rule_based_fix(state: IssueState) -> IssueState:
    """결정론적 룰 기반 수정안 생성 (LLM 없음).

    성공 시: fix_content, fix_description, root_cause 반환 → validate로 진행
    실패 시: route='llm' 설정 → llm_fix로 폴백
    """
    if state.get("status") == "error":
        return state

    issue = state["issue_data"]
    original_yaml = state.get("original_yaml", "")

    result = _try_rule_based_fix(issue, original_yaml)
    if result is None:
        # 룰 기반 적용 불가 → LLM으로 폴백
        return {"route": "llm"}

    fix_content, fix_description, root_cause = result
    return {
        "root_cause": root_cause,
        "severity": "high",
        "suggestions": [
            "서비스 레플리카를 증설해 단일 장애점(SPOF)을 줄였습니다.",
            "후속으로 timeout/retry 정책을 서비스 코드/차트에 반영하세요.",
        ],
        "fix_content": fix_content,
        "fix_description": fix_description,
        "fix_method": "rule_based",
        "status": "analyzed",
    }


def llm_fix(state: IssueState) -> IssueState:
    """LLM으로 이슈 분석 + YAML 수정안 생성.

    retry 시 validation_error를 프롬프트에 주입해 LLM이 오류를 수정하게 한다.
    """
    if state.get("status") == "error":
        return state

    issue = state["issue_data"]
    target_file = state.get("target_file", "")
    original_yaml = state.get("original_yaml", "")
    source_file = state.get("source_file", "")
    original_source = state.get("original_source", "")
    retry_count = state.get("retry_count", 0)
    validation_error = state.get("validation_error", "")
    pr_review_comment = state.get("pr_review_comment", "")
    previous_fix_content = state.get("previous_fix_content", "")
    logs_text = "\n".join(issue.get("logs", []))

    # 수정 요청 루프: 이전 fix_content + review comment 있으면 PR_REVIEW_RESPONSE_PROMPT 사용
    if pr_review_comment and previous_fix_content:
        prompt = PR_REVIEW_RESPONSE_PROMPT.format(
            type=issue.get("type", "unknown"),
            namespace=issue.get("namespace", "default"),
            resource=issue.get("resource", "unknown"),
            error_message=issue.get("error_message", ""),
            target_file=target_file,
            original_fix=previous_fix_content,
            pr_review_comment=pr_review_comment,
            current_yaml=original_yaml,
        )
    else:
        # retry 시 이전 검증 오류를 프롬프트에 주입
        retry_context = ""
        if retry_count > 0 and validation_error:
            retry_context = (
                f"\n[이전 시도 오류 - 반드시 수정]\n{validation_error}\n"
            )

        # 소스코드가 있으면 values + Python 동시 수정 프롬프트 사용
        if source_file and original_source:
            prompt = SOURCE_AND_VALUES_FIX_PROMPT.format(
                retry_context=retry_context,
                type=issue.get("type", "unknown"),
                namespace=issue.get("namespace", "default"),
                resource=issue.get("resource", "unknown"),
                error_message=issue.get("error_message", ""),
                logs=logs_text,
                target_file=target_file,
                current_yaml=original_yaml,
                source_file=source_file,
                current_source=original_source,
            )
        else:
            prompt = LLM_FIX_PROMPT.format(
                retry_context=retry_context,
                type=issue.get("type", "unknown"),
                namespace=issue.get("namespace", "default"),
                resource=issue.get("resource", "unknown"),
                error_message=issue.get("error_message", ""),
                logs=logs_text,
                target_file=target_file,
                current_yaml=original_yaml,
            )

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        result = _extract_llm_content(response)

        root_cause = _parse_root_cause(result)
        severity = _parse_severity(result)
        suggestions = _parse_suggestions(result)
        fix_content = _parse_yaml_block(result)
        fix_source = _parse_python_block(result) if source_file else ""
        raw_desc = _parse_field(result, r"변경 설명:\s*(.+?)(?:\n|$)") or "자동 생성된 수정안"
        # LLM이 마크다운 bold/italic을 넣을 수 있어서 제거
        fix_description = re.sub(r"[*_`#~]", "", raw_desc).strip()

        if not fix_content:
            return {
                "root_cause": root_cause or "분석 결과를 파싱할 수 없습니다",
                "severity": severity,
                "suggestions": suggestions,
                "error": "LLM 응답에서 YAML 블록을 추출할 수 없습니다",
                "status": "error",
            }

        return {
            "root_cause": root_cause or "분석 결과를 파싱할 수 없습니다",
            "severity": severity,
            "suggestions": suggestions or ["로그를 더 확인하세요"],
            "fix_content": fix_content,
            "fix_source": fix_source,
            "fix_description": fix_description,
            "fix_method": "llm",
            "status": "analyzed",
        }
    except Exception as e:
        return {"error": f"분석 + 수정안 생성 실패: {str(e)}", "status": "error"}


def _analyze_only(state: IssueState) -> IssueState:
    """values 파일이 없는 이슈의 분석만 수행"""
    issue = state["issue_data"]
    logs_text = "\n".join(issue.get("logs", []))

    prompt = ANALYZE_ONLY_PROMPT.format(
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
        return {"error": f"분석 실패: {str(e)}", "status": "error"}


def validate(state: IssueState) -> IssueState:
    """YAML 수정안 검증: 문법 + 변경 확인 + 정책 준수"""
    fix_content = state.get("fix_content", "")
    original_yaml = state.get("original_yaml", "")
    retry_count = state.get("retry_count", 0)

    def _fail(msg: str) -> IssueState:
        return {"retry_count": retry_count + 1, "validation_error": msg, "status": "validation_failed"}

    # 1. YAML 문법 검증
    try:
        parsed = yaml.safe_load(fix_content)
        if parsed is None:
            return _fail("YAML 파싱 결과가 비어있습니다")
    except yaml.YAMLError as e:
        return _fail(f"YAML 문법 오류: {str(e)}")

    # 2. dict 형식인지 확인
    if not isinstance(parsed, dict):
        return _fail("YAML이 dict 형식이 아닙니다")

    issue = state.get("issue_data", {})
    issue_type = issue.get("type", "unknown")
    original_parsed = None

    # 3. 원본과 동일한지 확인
    try:
        original_parsed = yaml.safe_load(original_yaml)
        if parsed == original_parsed:
            return _fail("수정안이 원본과 동일합니다")
    except yaml.YAMLError:
        pass  # 원본 파싱 실패해도 수정안 검증은 통과

    # 4. 장애 타입별 수정 정책 검증
    if issue_type in POLICY_RESTRICTED_TYPES | {"composite_incident"}:
        if not isinstance(original_parsed, dict):
            return _fail(f"정책 검증 실패: issue_type={issue_type} 는 원본 YAML 파싱이 필요합니다")

        changed_paths = _collect_changed_paths(original_parsed, parsed)
        policy_error = _validate_remediation_policy(issue_type, changed_paths)
        if policy_error:
            return _fail(policy_error)

    # 5. Python 소스코드 문법 검증 (있는 경우)
    fix_source = state.get("fix_source", "")
    if fix_source:
        import ast
        try:
            ast.parse(fix_source)
        except SyntaxError as e:
            return _fail(f"Python 문법 오류: {e}")
        if fix_source == state.get("original_source", ""):
            return _fail("Python 수정안이 원본과 동일합니다")

    return {"status": "validated"}


def create_pr(state: IssueState) -> IssueState:
    """GitHub PR 생성"""
    if state.get("error"):
        return state

    issue = state.get("issue_data", {})
    target_file = state.get("target_file", "")
    fix_content = state.get("fix_content", "")

    if not target_file or not fix_content:
        return {"error": "수정할 파일 또는 내용이 없습니다", "status": "error"}

    branch_name = generate_branch_name(
        issue.get("type", "fix"), issue.get("resource", "unknown")
    )
    gh = GitHubClient(str(PROJECT_ROOT))

    source_file = state.get("source_file", "")
    fix_source = state.get("fix_source", "")

    try:
        success, msg = gh.create_branch(branch_name)
        if not success:
            return {"error": f"브랜치 생성 실패: {msg}", "status": "error"}

        # values 파일 쓰기
        target_path = PROJECT_ROOT / target_file
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(fix_content)

        # 소스코드 파일 쓰기 (있는 경우)
        files_to_commit = [target_file]
        if source_file and fix_source:
            source_path = PROJECT_ROOT / source_file
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(fix_source)
            files_to_commit.append(source_file)

        commit_message = f"fix({issue.get('resource', 'unknown')}): {state.get('fix_description', '자동 수정')}"
        success, msg = gh.commit_files_and_push(files_to_commit, commit_message, branch_name)
        if not success:
            gh.cleanup()
            return {"error": f"커밋/푸시 실패: {msg}", "status": "error"}

        pr_title = f"fix({issue.get('resource', 'unknown')}): {state.get('fix_description', '자동 수정')}"
        pr_body = generate_pr_body(state)
        success, pr_url, pr_number = gh.create_pr(branch_name, pr_title, pr_body)

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


def error_end(state: IssueState) -> IssueState:
    """에러 상태로 워크플로우 종료"""
    retry_count = state.get("retry_count", 0)
    error_msg = state.get("error", "") or state.get("validation_error", "알 수 없는 오류")
    if retry_count >= MAX_RETRIES:
        error_msg = f"검증 {MAX_RETRIES}회 실패 후 종료: {error_msg}"
    return {"status": "error", "error": error_msg}


# =============================================================================
# 라우팅 함수
# =============================================================================

def _route_issue(state: IssueState) -> str:
    """classify_issue 후 라우팅"""
    if state.get("status") == "error":
        return "error_end"
    return state.get("route", "llm")


def _after_rule_based(state: IssueState) -> str:
    """rule_based_fix 후 라우팅.

    룰 기반 성공 → validate
    룰 기반 실패(route='llm') → llm_fix
    에러 → error_end
    """
    if state.get("status") == "error":
        return "error_end"
    if state.get("route") == "llm":
        return "llm"
    return "validate"


def _after_llm_fix(state: IssueState) -> str:
    """llm_fix 후 라우팅"""
    if state.get("status") == "error":
        return "error_end"
    return "validate"


def _should_retry(state: IssueState) -> str:
    """validate 후 라우팅"""
    if state.get("status") == "validated":
        return "create_pr"
    if state.get("retry_count", 0) >= MAX_RETRIES:
        return "error_end"
    return "llm_fix"


# =============================================================================
# 그래프 생성
# =============================================================================

def create_graph(with_pr: bool = False):
    """LangGraph 워크플로우 생성

    Args:
        with_pr: True면 validate + PR 생성까지 포함, False면 분석/수정안만
    """
    workflow = StateGraph(IssueState)

    # 공통 노드
    workflow.add_node("load_issue", load_issue)
    workflow.add_node("classify_issue", classify_issue)
    workflow.add_node("analyze_only", analyze_only)
    workflow.add_node("rule_based_fix", rule_based_fix)
    workflow.add_node("llm_fix", llm_fix)
    workflow.add_node("error_end", error_end)

    workflow.set_entry_point("load_issue")
    workflow.add_edge("load_issue", "classify_issue")

    # classify → 각 경로
    _route_map = {
        "argocd": "analyze_only",
        "analyze_only": "analyze_only",
        "rule_based": "rule_based_fix",
        "llm": "llm_fix",
        "error_end": "error_end",
    }
    workflow.add_conditional_edges("classify_issue", _route_issue, _route_map)

    if with_pr:
        workflow.add_node("validate", validate)
        workflow.add_node("create_pr", create_pr)

        # analyze_only → 분석 완료 후 END (PR 생성 없음)
        workflow.add_edge("analyze_only", END)

        # rule_based_fix → validate 또는 llm_fix 폴백
        workflow.add_conditional_edges(
            "rule_based_fix",
            _after_rule_based,
            {"validate": "validate", "llm": "llm_fix", "error_end": "error_end"},
        )

        # llm_fix → validate
        workflow.add_conditional_edges(
            "llm_fix",
            _after_llm_fix,
            {"validate": "validate", "error_end": "error_end"},
        )

        # validate → create_pr / retry / error_end
        workflow.add_conditional_edges(
            "validate",
            _should_retry,
            {"create_pr": "create_pr", "llm_fix": "llm_fix", "error_end": "error_end"},
        )

        workflow.add_edge("create_pr", END)
    else:
        # 분석 전용: 각 노드에서 바로 END
        workflow.add_edge("analyze_only", END)
        workflow.add_edge("rule_based_fix", END)
        workflow.add_edge("llm_fix", END)

    workflow.add_edge("error_end", END)

    return workflow.compile()
