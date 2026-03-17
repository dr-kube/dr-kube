"""inventory-service - 재고 조회 API (캐싱 + 서킷 브레이커)

Online Boutique productcatalogservice 앞단에서
재고 상태를 캐싱하고 서킷 브레이커로 장애를 격리.
"""
import time
import asyncio
import logging
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

import config
from cache import cache
from circuit_breaker import circuit_breaker, CircuitOpenError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("inventory-service")

app = FastAPI(title="inventory-service", version="1.0.0")

_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)


@app.get("/healthz")
def health():
    return {"status": "ok", "circuit": circuit_breaker.state}


@app.get("/readyz")
def ready():
    if circuit_breaker.state == "OPEN":
        return JSONResponse(status_code=503, content={"status": "not ready", "reason": "circuit OPEN"})
    return {"status": "ready"}


@app.get("/inventory/{product_id}")
async def get_inventory(product_id: str):
    # 캐시 확인
    cached = cache.get(product_id)
    if cached is not None:
        return {"product_id": product_id, "stock": cached, "source": "cache"}

    async with _semaphore:
        try:
            result = await _fetch_from_upstream(product_id)
            cache.set(product_id, result)
            return {"product_id": product_id, "stock": result, "source": "upstream"}
        except CircuitOpenError as e:
            logger.warning(f"Circuit OPEN: {e}")
            raise HTTPException(status_code=503, detail=str(e))
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="upstream timeout")
        except Exception as e:
            logger.error(f"inventory fetch failed: {e}")
            raise HTTPException(status_code=502, detail="upstream error")


async def _fetch_from_upstream(product_id: str) -> dict:
    """productcatalogservice에서 상품 정보 조회 (재시도 포함)"""
    timeout_s = config.UPSTREAM_TIMEOUT_MS / 1000
    url = f"http://{config.PRODUCT_CATALOG_HOST}:{config.PRODUCT_CATALOG_PORT}/products/{product_id}"

    last_exc = None
    for attempt in range(config.UPSTREAM_MAX_RETRIES + 1):
        if attempt > 0:
            backoff = config.UPSTREAM_RETRY_BACKOFF_MS / 1000 * (2 ** (attempt - 1))
            await asyncio.sleep(min(backoff, 5.0))

        try:
            def do_request():
                with httpx.Client(timeout=timeout_s) as client:
                    resp = client.get(url)
                    resp.raise_for_status()
                    return resp.json()

            result = circuit_breaker.call(do_request)
            return result
        except CircuitOpenError:
            raise
        except Exception as e:
            last_exc = e
            logger.warning(f"upstream attempt {attempt+1}/{config.UPSTREAM_MAX_RETRIES+1} failed: {e}")

    raise last_exc


@app.get("/cache/stats")
def cache_stats():
    return cache.stats()


@app.get("/config")
def get_config():
    """현재 설정값 확인 (디버깅용)"""
    return {
        "upstream_timeout_ms": config.UPSTREAM_TIMEOUT_MS,
        "upstream_max_retries": config.UPSTREAM_MAX_RETRIES,
        "upstream_retry_backoff_ms": config.UPSTREAM_RETRY_BACKOFF_MS,
        "circuit_breaker_failure_threshold": config.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        "circuit_breaker_recovery_timeout_s": config.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_S,
        "cache_ttl_seconds": config.CACHE_TTL_SECONDS,
        "cache_max_size": config.CACHE_MAX_SIZE,
        "max_concurrent_requests": config.MAX_CONCURRENT_REQUESTS,
    }
