"""이슈 타입별 수정 정책 및 서비스 토폴로지"""

# delivery-app 서비스 → manifest 파일 매핑
DELIVERY_SERVICES: dict[str, str] = {
    "frontend":          "manifests/delivery-app/frontend.yaml",
    "order-service":     "manifests/delivery-app/order-service.yaml",
    "menu-service":      "manifests/delivery-app/menu-service.yaml",
    "delivery-service":  "manifests/delivery-app/delivery-service.yaml",
}

# 서비스 간 의존 관계 (호출 방향)
DEPENDENCY_GRAPH: dict[str, list[str]] = {
    "frontend":          ["order-service"],
    "order-service":     ["menu-service", "delivery-service"],
    "menu-service":      [],
    "delivery-service":  [],
}

# 이슈 타입별 정책
ISSUE_POLICY: dict[str, dict] = {
    "oom": {
        # memory limit 증가만 허용, 최소 1.5배 ~ 최대 4배
        "allowed_field_patterns": ["resources.limits.memory", "resources.requests.memory"],
        "forbidden_field_patterns": ["spec.replicas", "spec.template.spec.containers[*].env"],
        "min_factor": 1.5,
        "max_factor": 4.0,
        "requires_human": False,
        "retry_strategies": ["conservative", "moderate", "aggressive"],
    },
    "crash_loop": {
        # 환경변수나 probe 조정만 허용, 핵심 서비스면 human 필수
        "allowed_field_patterns": [
            "spec.template.spec.containers[*].livenessProbe",
            "spec.template.spec.containers[*].readinessProbe",
            "spec.template.spec.containers[*].env",
        ],
        "forbidden_field_patterns": ["spec.replicas"],
        "requires_human": True,  # 항상 human 승인
        "retry_strategies": ["conservative", "moderate", "aggressive"],
    },
    "service_error": {
        # 연결 실패는 replicas 증설 또는 probe 완화
        "allowed_field_patterns": [
            "spec.replicas",
            "spec.template.spec.containers[*].readinessProbe",
            "spec.template.spec.containers[*].livenessProbe",
        ],
        "forbidden_field_patterns": [],
        "requires_human": False,
        "retry_strategies": ["conservative", "moderate", "aggressive"],
    },
    "high_latency": {
        # replicas 증설 또는 resource limit 증가
        "allowed_field_patterns": [
            "spec.replicas",
            "resources.limits.cpu",
            "resources.requests.cpu",
        ],
        "forbidden_field_patterns": [],
        "requires_human": False,
        "retry_strategies": ["conservative", "moderate", "aggressive"],
    },
    "resource_exhaustion": {
        # CPU 관련 조정 + replicas
        "allowed_field_patterns": [
            "spec.replicas",
            "resources.limits.cpu",
            "resources.requests.cpu",
        ],
        "forbidden_field_patterns": [],
        "requires_human": False,
        "retry_strategies": ["conservative", "moderate", "aggressive"],
    },
    "unknown": {
        "allowed_field_patterns": [],
        "forbidden_field_patterns": [],
        "requires_human": True,
        "retry_strategies": ["conservative"],
    },
}

# human approval 강제 조건 (정책과 별개로 추가 조건)
FORCE_HUMAN_APPROVAL_CONDITIONS = {
    "critical_services": ["order-service"],   # 핵심 트랜잭션 서비스
    "multi_service_threshold": 2,             # 영향 서비스 2개 이상이면 human
    "retry_threshold": 1,                     # 재시도 횟수가 1 이상이면 human
}


def should_require_human(
    issue_type: str,
    severity: str,
    affected_services: list[str],
    retry_count: int,
    llm_requires_human: bool,
) -> bool:
    """human approval 필요 여부 결정"""
    policy = ISSUE_POLICY.get(issue_type, ISSUE_POLICY["unknown"])

    # 정책 기본값
    if policy["requires_human"]:
        return True

    # LLM이 위험하다고 판단
    if llm_requires_human:
        return True

    # 심각도 critical
    if severity == "critical":
        return True

    # 핵심 서비스 포함
    cond = FORCE_HUMAN_APPROVAL_CONDITIONS
    if any(svc in cond["critical_services"] for svc in affected_services):
        if severity in ("high", "critical"):
            return True

    # 다수 서비스 영향
    if len(affected_services) >= cond["multi_service_threshold"]:
        return True

    # 재시도 중
    if retry_count >= cond["retry_threshold"]:
        return True

    return False


def get_retry_strategy(issue_type: str, retry_count: int) -> str:
    """재시도 횟수에 따른 전략 반환"""
    strategies = ISSUE_POLICY.get(issue_type, {}).get(
        "retry_strategies", ["conservative", "moderate", "aggressive"]
    )
    idx = min(retry_count, len(strategies) - 1)
    return strategies[idx]
