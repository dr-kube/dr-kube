"""order-validator - 주문 유효성 검증 서비스

checkoutservice → order-validator → paymentservice 흐름에서
주문 금액 범위, 중복 주문 방지, 결제 사전 검증을 수행.
"""
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import config
from validator import OrderRequest, validate_order, dup_cache_stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("order-validator")

app = FastAPI(title="order-validator", version="1.0.0")

_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_VALIDATIONS)
_stats = {"validated": 0, "rejected": 0, "timeout": 0}


class ValidateRequest(BaseModel):
    order_id: str
    user_id: str
    product_ids: list[str]
    amount_usd: float


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.get("/readyz")
def ready():
    return {"status": "ready"}


@app.post("/validate")
async def validate(req: ValidateRequest):
    try:
        async with asyncio.timeout(config.VALIDATION_QUEUE_TIMEOUT_MS / 1000):
            async with _semaphore:
                order = OrderRequest(
                    order_id=req.order_id,
                    user_id=req.user_id,
                    product_ids=req.product_ids,
                    amount_usd=req.amount_usd,
                )
                result = await validate_order(order)

        if result.valid:
            _stats["validated"] += 1
            return {"order_id": req.order_id, "valid": True}
        else:
            _stats["rejected"] += 1
            return {"order_id": req.order_id, "valid": False, "reason": result.reason}

    except asyncio.TimeoutError:
        _stats["timeout"] += 1
        logger.warning(f"validation queue timeout: order_id={req.order_id}")
        raise HTTPException(status_code=429, detail="validation queue full")
    except Exception as e:
        logger.error(f"validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
def stats():
    total = _stats["validated"] + _stats["rejected"]
    rejection_rate = _stats["rejected"] / total if total > 0 else 0
    return {
        **_stats,
        "total": total,
        "rejection_rate": round(rejection_rate, 3),
        "duplicate_cache": dup_cache_stats(),
    }


@app.get("/config")
def get_config():
    return {
        "max_order_amount_usd": config.MAX_ORDER_AMOUNT_USD,
        "min_order_amount_usd": config.MIN_ORDER_AMOUNT_USD,
        "payment_validation_timeout_ms": config.PAYMENT_VALIDATION_TIMEOUT_MS,
        "duplicate_check_window_seconds": config.DUPLICATE_CHECK_WINDOW_SECONDS,
        "validation_max_retries": config.VALIDATION_MAX_RETRIES,
        "retry_backoff_base_ms": config.RETRY_BACKOFF_BASE_MS,
        "max_concurrent_validations": config.MAX_CONCURRENT_VALIDATIONS,
        "validation_queue_timeout_ms": config.VALIDATION_QUEUE_TIMEOUT_MS,
    }
