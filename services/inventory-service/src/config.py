"""
inventory-service 설정 상수
★ DR-Kube 에이전트 수정 대상 파일

환경변수로 오버라이드 가능. 기본값은 이 파일의 상수.
에이전트가 이 값을 수정하면 PR → ArgoCD sync → ConfigMap 갱신 → Pod 재시작으로 반영.
"""
import os

# ── 외부 API 타임아웃 ─────────────────────────────────────
# 너무 낮으면 ServiceHighLatencyP99 alert 발생
UPSTREAM_TIMEOUT_MS: int = int(os.getenv("UPSTREAM_TIMEOUT_MS", "500"))

# 재시도 횟수. 너무 낮으면 일시 장애에 취약
UPSTREAM_MAX_RETRIES: int = int(os.getenv("UPSTREAM_MAX_RETRIES", "2"))

# 재시도 간격 (지수 백오프 기반값, ms)
UPSTREAM_RETRY_BACKOFF_MS: int = int(os.getenv("UPSTREAM_RETRY_BACKOFF_MS", "200"))

# ── 서킷 브레이커 ─────────────────────────────────────────
# 연속 실패 횟수 임계값. 너무 낮으면 잦은 circuit open → ServiceDown alert
CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))

# OPEN 후 HALF-OPEN 전환까지 대기 시간 (초)
CIRCUIT_BREAKER_RECOVERY_TIMEOUT_S: int = int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT_S", "30"))

# HALF-OPEN 상태에서 허용하는 최대 요청 수
CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS: int = int(os.getenv("CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS", "3"))

# ── 인메모리 캐시 ─────────────────────────────────────────
# TTL 너무 짧으면 upstream 과부하 → CPUThrottling alert
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "60"))

# 캐시 최대 항목 수. 너무 크면 메모리 증가 → OOMKilled
CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))

# ── 서버 동시성 ───────────────────────────────────────────
# 너무 낮으면 503 에러 / ServiceDown alert
MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "50"))

# 요청 큐 초과 시 거부 임계값
REQUEST_QUEUE_SIZE: int = int(os.getenv("REQUEST_QUEUE_SIZE", "100"))

# ── 업스트림 서비스 주소 ──────────────────────────────────
# Online Boutique productcatalogservice 연동
PRODUCT_CATALOG_HOST: str = os.getenv("PRODUCT_CATALOG_HOST", "productcatalogservice.online-boutique.svc.cluster.local")
PRODUCT_CATALOG_PORT: int = int(os.getenv("PRODUCT_CATALOG_PORT", "3550"))
