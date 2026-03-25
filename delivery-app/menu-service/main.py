"""
menu-service: 레스토랑 및 메뉴 관리 서비스
"""
import os
import time
import threading
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="menu-service", version="1.0.0")

# Prometheus 메트릭
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["endpoint"])

# 인메모리 데이터
RESTAURANTS = {
    "r1": {"id": "r1", "name": "서울치킨", "category": "치킨", "rating": 4.5},
    "r2": {"id": "r2", "name": "맛있는 피자", "category": "피자", "rating": 4.2},
    "r3": {"id": "r3", "name": "행복 분식", "category": "분식", "rating": 4.7},
}

MENUS = {
    "r1": [
        {"id": "m1", "name": "후라이드치킨", "price": 18000, "description": "바삭한 후라이드"},
        {"id": "m2", "name": "양념치킨", "price": 19000, "description": "달콤매콤 양념"},
        {"id": "m3", "name": "반반치킨", "price": 20000, "description": "후라이드+양념 반반"},
    ],
    "r2": [
        {"id": "m4", "name": "마르게리따", "price": 16000, "description": "토마토+모짜렐라"},
        {"id": "m5", "name": "페퍼로니", "price": 17000, "description": "매콤한 페퍼로니"},
        {"id": "m6", "name": "BBQ치킨피자", "price": 19000, "description": "BBQ소스 치킨"},
    ],
    "r3": [
        {"id": "m7", "name": "떡볶이", "price": 6000, "description": "쫄깃한 떡볶이"},
        {"id": "m8", "name": "순대국밥", "price": 9000, "description": "진한 국물"},
        {"id": "m9", "name": "김밥", "price": 3500, "description": "참기름 향 가득"},
    ],
}

# 메모리 점유용 (OOM 테스트)
_memory_hog: list = []


@app.get("/health")
def health():
    return {"status": "ok", "service": "menu-service"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/restaurants")
def list_restaurants():
    with REQUEST_LATENCY.labels(endpoint="/restaurants").time():
        REQUEST_COUNT.labels(method="GET", endpoint="/restaurants", status="200").inc()
        return list(RESTAURANTS.values())


@app.get("/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: str):
    with REQUEST_LATENCY.labels(endpoint="/restaurants/{id}").time():
        if restaurant_id not in RESTAURANTS:
            REQUEST_COUNT.labels(method="GET", endpoint="/restaurants/{id}", status="404").inc()
            raise HTTPException(status_code=404, detail=f"레스토랑 {restaurant_id} 없음")
        REQUEST_COUNT.labels(method="GET", endpoint="/restaurants/{id}", status="200").inc()
        return RESTAURANTS[restaurant_id]


@app.get("/restaurants/{restaurant_id}/menu")
def get_menu(restaurant_id: str):
    with REQUEST_LATENCY.labels(endpoint="/restaurants/{id}/menu").time():
        if restaurant_id not in RESTAURANTS:
            REQUEST_COUNT.labels(method="GET", endpoint="/restaurants/{id}/menu", status="404").inc()
            raise HTTPException(status_code=404, detail=f"레스토랑 {restaurant_id} 없음")
        REQUEST_COUNT.labels(method="GET", endpoint="/restaurants/{id}/menu", status="200").inc()
        return MENUS.get(restaurant_id, [])


@app.get("/menu/{menu_id}")
def get_menu_item(menu_id: str):
    for items in MENUS.values():
        for item in items:
            if item["id"] == menu_id:
                REQUEST_COUNT.labels(method="GET", endpoint="/menu/{id}", status="200").inc()
                return item
    REQUEST_COUNT.labels(method="GET", endpoint="/menu/{id}", status="404").inc()
    raise HTTPException(status_code=404, detail=f"메뉴 {menu_id} 없음")


# ============================================================
# Chaos 테스트용 엔드포인트
# ============================================================

@app.post("/simulate/oom")
def simulate_oom(mb: int = 100):
    """메모리 점유로 OOM 유발 (mb: 점유할 MB 수)"""
    global _memory_hog
    chunk = " " * (mb * 1024 * 1024)  # mb MB 문자열
    _memory_hog.append(chunk)
    return {"status": "allocated", "mb": mb, "total_chunks": len(_memory_hog)}


@app.post("/simulate/cpu")
def simulate_cpu(seconds: int = 5):
    """CPU 부하 유발"""
    def cpu_burn():
        end = time.time() + seconds
        while time.time() < end:
            _ = sum(i * i for i in range(10000))

    thread = threading.Thread(target=cpu_burn, daemon=True)
    thread.start()
    return {"status": "started", "seconds": seconds}


@app.post("/simulate/reset")
def simulate_reset():
    """점유한 메모리 해제"""
    global _memory_hog
    _memory_hog = []
    return {"status": "reset"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
