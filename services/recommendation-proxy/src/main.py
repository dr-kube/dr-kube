"""recommendation-proxy - 추천 서비스 캐싱 프록시

recommendationservice 앞단에서 동일 user_id의 추천 결과를 TTL 기반으로 캐싱.
ML 추론 비용 절감 + 레이턴시 개선.
"""
import asyncio
import logging
import time
import hashlib
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("recommendation-proxy")

app = FastAPI(title="recommendation-proxy", version="1.0.0")

# 인메모리 캐시: cache_key → (result, expires_at)
_cache: dict[str, tuple[list, float]] = {}
_cache_lock = asyncio.Lock()
_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)

_stats = {"hits": 0, "misses": 0, "errors": 0}


def _cache_key(user_id: str, product_ids: list[str]) -> str:
    raw = f"{user_id}:{','.join(sorted(product_ids))}"
    return hashlib.md5(raw.encode()).hexdigest()


async def _get_cached(key: str) -> list | None:
    async with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        result, expires_at = entry
        if time.time() > expires_at:
            del _cache[key]
            return None
        return result


async def _set_cached(key: str, value: list):
    async with _cache_lock:
        # 캐시 초과 시 만료 항목 정리
        if len(_cache) >= config.CACHE_MAX_ENTRIES:
            now = time.time()
            expired_keys = [k for k, (_, exp) in _cache.items() if exp < now]
            for k in expired_keys:
                del _cache[k]
            if len(_cache) >= config.CACHE_MAX_ENTRIES:
                oldest = min(_cache, key=lambda k: _cache[k][1])
                del _cache[oldest]
        _cache[key] = (value, time.time() + config.CACHE_TTL_SECONDS)


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.get("/readyz")
def ready():
    return {"status": "ready"}


@app.get("/recommendations")
async def get_recommendations(
    user_id: str = Query(...),
    product_ids: list[str] = Query(default=[]),
    max_results: int = Query(default=None),
):
    effective_max = min(max_results or config.MAX_RECOMMENDATIONS_PER_REQUEST, config.MAX_RECOMMENDATIONS_PER_REQUEST)
    key = _cache_key(user_id, product_ids)

    cached = await _get_cached(key)
    if cached is not None:
        _stats["hits"] += 1
        return {"user_id": user_id, "recommendations": cached[:effective_max], "source": "cache"}

    _stats["misses"] += 1
    async with _semaphore:
        results = await _fetch_recommendations(user_id, product_ids)
        await _set_cached(key, results)
        return {"user_id": user_id, "recommendations": results[:effective_max], "source": "upstream"}


async def _fetch_recommendations(user_id: str, product_ids: list[str]) -> list:
    timeout_s = config.RECOMMENDATION_TIMEOUT_MS / 1000
    url = (
        f"http://{config.RECOMMENDATION_SERVICE_HOST}:{config.RECOMMENDATION_SERVICE_PORT}"
        f"/recommendations?user_id={user_id}"
    )

    last_exc = None
    for attempt in range(config.RECOMMENDATION_MAX_RETRIES + 1):
        if attempt > 0:
            await asyncio.sleep(0.1 * (2 ** attempt))
        try:
            async with httpx.AsyncClient(timeout=timeout_s) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                return data.get("recommendations", [])
        except Exception as e:
            last_exc = e
            logger.warning(f"upstream attempt {attempt+1} failed: {e}")

    _stats["errors"] += 1
    raise HTTPException(status_code=502, detail=f"upstream error: {last_exc}")


@app.get("/stats")
def stats():
    total = _stats["hits"] + _stats["misses"]
    hit_rate = _stats["hits"] / total if total > 0 else 0
    return {
        **_stats,
        "total_requests": total,
        "cache_hit_rate": round(hit_rate, 3),
        "cache_size": len(_cache),
        "cache_max_entries": config.CACHE_MAX_ENTRIES,
    }


@app.get("/config")
def get_config():
    return {
        "cache_ttl_seconds": config.CACHE_TTL_SECONDS,
        "cache_max_entries": config.CACHE_MAX_ENTRIES,
        "recommendation_timeout_ms": config.RECOMMENDATION_TIMEOUT_MS,
        "recommendation_max_retries": config.RECOMMENDATION_MAX_RETRIES,
        "max_recommendations_per_request": config.MAX_RECOMMENDATIONS_PER_REQUEST,
        "max_concurrent_requests": config.MAX_CONCURRENT_REQUESTS,
    }
