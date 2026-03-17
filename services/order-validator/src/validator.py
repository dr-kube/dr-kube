"""주문 검증 로직"""
import time
import asyncio
import logging
from dataclasses import dataclass

import config

logger = logging.getLogger("order-validator")


@dataclass
class OrderRequest:
    order_id: str
    user_id: str
    product_ids: list[str]
    amount_usd: float


@dataclass
class ValidationResult:
    valid: bool
    reason: str = ""


# 중복 주문 방지 캐시: "{user_id}:{product_key}" → expires_at
_duplicate_cache: dict[str, float] = {}
_dup_lock = asyncio.Lock()


async def validate_order(order: OrderRequest) -> ValidationResult:
    # 1. 금액 범위 검증
    if order.amount_usd < config.MIN_ORDER_AMOUNT_USD:
        return ValidationResult(False, f"주문 금액 {order.amount_usd} < 최솟값 {config.MIN_ORDER_AMOUNT_USD}")
    if order.amount_usd > config.MAX_ORDER_AMOUNT_USD:
        return ValidationResult(False, f"주문 금액 {order.amount_usd} > 최댓값 {config.MAX_ORDER_AMOUNT_USD}")

    # 2. 중복 주문 체크
    dup_key = f"{order.user_id}:{','.join(sorted(order.product_ids))}"
    if await _is_duplicate(dup_key):
        return ValidationResult(False, f"중복 주문 감지: {config.DUPLICATE_CHECK_WINDOW_SECONDS}초 내 동일 주문")

    # 3. 재시도 포함 결제 서비스 사전 검증
    result = await _validate_with_payment_service(order)
    if result.valid:
        await _mark_duplicate(dup_key)
    return result


async def _is_duplicate(key: str) -> bool:
    async with _dup_lock:
        expires_at = _duplicate_cache.get(key)
        if expires_at is None:
            return False
        if time.time() > expires_at:
            del _duplicate_cache[key]
            return False
        return True


async def _mark_duplicate(key: str):
    async with _dup_lock:
        # 캐시 크기 초과 시 만료된 항목 정리
        if len(_duplicate_cache) >= config.DUPLICATE_CACHE_MAX_ENTRIES:
            now = time.time()
            expired = [k for k, exp in _duplicate_cache.items() if exp < now]
            for k in expired:
                del _duplicate_cache[k]
        _duplicate_cache[key] = time.time() + config.DUPLICATE_CHECK_WINDOW_SECONDS


async def _validate_with_payment_service(order: OrderRequest) -> ValidationResult:
    """결제 서비스 사전 검증 (재시도 + 지수 백오프)"""
    timeout_s = config.PAYMENT_VALIDATION_TIMEOUT_MS / 1000

    last_exc: Exception | None = None
    for attempt in range(config.VALIDATION_MAX_RETRIES + 1):
        if attempt > 0:
            backoff_ms = min(
                config.RETRY_BACKOFF_BASE_MS * (2 ** (attempt - 1)),
                config.RETRY_MAX_BACKOFF_MS,
            )
            await asyncio.sleep(backoff_ms / 1000)

        try:
            # NOTE: 실제 환경에서는 gRPC로 paymentservice 호출
            # 여기서는 HTTP 모의 호출로 대체 (프로토타입)
            await asyncio.wait_for(
                _mock_payment_check(order.amount_usd),
                timeout=timeout_s,
            )
            return ValidationResult(True)
        except asyncio.TimeoutError:
            last_exc = TimeoutError(f"payment validation timeout ({config.PAYMENT_VALIDATION_TIMEOUT_MS}ms)")
            logger.warning(f"payment check timeout attempt {attempt+1}")
        except Exception as e:
            last_exc = e
            logger.warning(f"payment check failed attempt {attempt+1}: {e}")

    return ValidationResult(False, f"결제 서비스 검증 실패: {last_exc}")


async def _mock_payment_check(amount_usd: float):
    """결제 서비스 사전 검증 시뮬레이션 (실제 환경에서는 gRPC 호출로 대체)"""
    await asyncio.sleep(0.01)  # 10ms 시뮬레이션


def dup_cache_stats() -> dict:
    now = time.time()
    total = len(_duplicate_cache)
    active = sum(1 for exp in _duplicate_cache.values() if exp > now)
    return {
        "total": total,
        "active": active,
        "max_entries": config.DUPLICATE_CACHE_MAX_ENTRIES,
        "window_seconds": config.DUPLICATE_CHECK_WINDOW_SECONDS,
    }
