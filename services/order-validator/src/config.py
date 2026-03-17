"""
order-validator 설정 상수
★ DR-Kube 에이전트 수정 대상 파일

checkoutservice와 paymentservice 사이에서 주문 유효성을 검증.
에이전트가 이 값을 수정 → PR → ArgoCD → ConfigMap 갱신 → Pod 재시작으로 반영.
"""
import os

# ── 주문 금액 검증 ────────────────────────────────────────
# 너무 낮으면 정상 주문 거부 → OrderValidationFailed alert
MAX_ORDER_AMOUNT_USD: float = float(os.getenv("MAX_ORDER_AMOUNT_USD", "10000.0"))
MIN_ORDER_AMOUNT_USD: float = float(os.getenv("MIN_ORDER_AMOUNT_USD", "0.01"))

# ── 결제 서비스 연동 타임아웃 ─────────────────────────────
# 너무 낮으면 ServiceHighLatencyP99 / ServiceDown alert
PAYMENT_VALIDATION_TIMEOUT_MS: int = int(os.getenv("PAYMENT_VALIDATION_TIMEOUT_MS", "1000"))

# ── 중복 주문 방지 ────────────────────────────────────────
# 같은 user_id + product_id 조합의 재주문 방지 시간 창 (초)
# 너무 길면 정상 재구매 차단
DUPLICATE_CHECK_WINDOW_SECONDS: int = int(os.getenv("DUPLICATE_CHECK_WINDOW_SECONDS", "60"))

# 중복 방지 캐시 최대 항목 수. 너무 크면 메모리 증가
DUPLICATE_CACHE_MAX_ENTRIES: int = int(os.getenv("DUPLICATE_CACHE_MAX_ENTRIES", "10000"))

# ── 재시도 정책 ───────────────────────────────────────────
# 검증 실패 시 재시도 횟수. 너무 낮으면 일시 장애에 취약
VALIDATION_MAX_RETRIES: int = int(os.getenv("VALIDATION_MAX_RETRIES", "2"))

# 지수 백오프 기본값 (ms). 너무 낮으면 upstream 과부하
RETRY_BACKOFF_BASE_MS: int = int(os.getenv("RETRY_BACKOFF_BASE_MS", "200"))

# 최대 백오프 (ms)
RETRY_MAX_BACKOFF_MS: int = int(os.getenv("RETRY_MAX_BACKOFF_MS", "2000"))

# ── 동시성 제한 ───────────────────────────────────────────
# 너무 낮으면 checkoutservice 병목 → 카트/결제 지연 cascade
MAX_CONCURRENT_VALIDATIONS: int = int(os.getenv("MAX_CONCURRENT_VALIDATIONS", "30"))

# 큐 대기 타임아웃 (ms). 초과 시 429 반환
VALIDATION_QUEUE_TIMEOUT_MS: int = int(os.getenv("VALIDATION_QUEUE_TIMEOUT_MS", "500"))

# ── 서비스 주소 ───────────────────────────────────────────
PAYMENT_SERVICE_HOST: str = os.getenv(
    "PAYMENT_SERVICE_HOST",
    "paymentservice.online-boutique.svc.cluster.local",
)
PAYMENT_SERVICE_PORT: int = int(os.getenv("PAYMENT_SERVICE_PORT", "50051"))

SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8002"))
