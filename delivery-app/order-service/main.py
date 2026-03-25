"""
order-service: 주문 생성 및 관리 서비스
- menu-service에서 메뉴 검증
- delivery-service에 배달 요청
"""
import os
import time
import uuid
import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="order-service", version="1.0.0")

MENU_SERVICE_URL = os.getenv("MENU_SERVICE_URL", "http://menu-service:8001")
DELIVERY_SERVICE_URL = os.getenv("DELIVERY_SERVICE_URL", "http://delivery-service:8002")

# Prometheus 메트릭
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["endpoint"])
ORDER_TOTAL = Counter("orders_total", "Total orders created", ["status"])

# 인메모리 주문 저장소
orders: dict[str, dict] = {}

# 메모리 점유용
_memory_hog: list = []


class OrderRequest(BaseModel):
    restaurant_id: str
    menu_items: list[str]  # menu_id 목록
    address: str
    customer_name: str


class OrderStatusUpdate(BaseModel):
    status: str  # pending, confirmed, preparing, delivering, delivered, cancelled


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "order-service",
        "dependencies": {
            "menu-service": MENU_SERVICE_URL,
            "delivery-service": DELIVERY_SERVICE_URL,
        },
    }


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/orders")
def list_orders():
    with REQUEST_LATENCY.labels(endpoint="/orders").time():
        REQUEST_COUNT.labels(method="GET", endpoint="/orders", status="200").inc()
        return list(orders.values())


@app.post("/orders", status_code=201)
def create_order(req: OrderRequest):
    with REQUEST_LATENCY.labels(endpoint="/orders").time():
        # 레스토랑 검증
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{MENU_SERVICE_URL}/restaurants/{req.restaurant_id}")
                if r.status_code == 404:
                    REQUEST_COUNT.labels(method="POST", endpoint="/orders", status="400").inc()
                    raise HTTPException(status_code=400, detail=f"레스토랑 {req.restaurant_id} 없음")
                restaurant = r.json()

                # 메뉴 아이템 검증 + 금액 계산
                total = 0
                validated_items = []
                for menu_id in req.menu_items:
                    mr = client.get(f"{MENU_SERVICE_URL}/menu/{menu_id}")
                    if mr.status_code == 404:
                        REQUEST_COUNT.labels(method="POST", endpoint="/orders", status="400").inc()
                        raise HTTPException(status_code=400, detail=f"메뉴 {menu_id} 없음")
                    item = mr.json()
                    total += item["price"]
                    validated_items.append(item)
        except httpx.RequestError as e:
            REQUEST_COUNT.labels(method="POST", endpoint="/orders", status="503").inc()
            raise HTTPException(status_code=503, detail=f"menu-service 연결 실패: {e}")

        # 주문 생성
        order_id = str(uuid.uuid4())[:8]
        order = {
            "id": order_id,
            "restaurant": restaurant,
            "items": validated_items,
            "total": total,
            "address": req.address,
            "customer_name": req.customer_name,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }

        # delivery-service에 배달 요청
        try:
            with httpx.Client(timeout=5.0) as client:
                dr = client.post(f"{DELIVERY_SERVICE_URL}/deliveries", json={
                    "order_id": order_id,
                    "address": req.address,
                    "restaurant_name": restaurant["name"],
                })
                if dr.status_code == 201:
                    order["delivery"] = dr.json()
                    order["status"] = "confirmed"
        except httpx.RequestError:
            # delivery-service 실패해도 주문은 생성 (degraded mode)
            order["delivery"] = None

        orders[order_id] = order
        ORDER_TOTAL.labels(status=order["status"]).inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/orders", status="201").inc()
        return order


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    with REQUEST_LATENCY.labels(endpoint="/orders/{id}").time():
        if order_id not in orders:
            REQUEST_COUNT.labels(method="GET", endpoint="/orders/{id}", status="404").inc()
            raise HTTPException(status_code=404, detail=f"주문 {order_id} 없음")
        REQUEST_COUNT.labels(method="GET", endpoint="/orders/{id}", status="200").inc()
        return orders[order_id]


@app.patch("/orders/{order_id}/status")
def update_order_status(order_id: str, update: OrderStatusUpdate):
    if order_id not in orders:
        raise HTTPException(status_code=404, detail=f"주문 {order_id} 없음")
    orders[order_id]["status"] = update.status
    orders[order_id]["updated_at"] = datetime.now().isoformat()
    return orders[order_id]


@app.delete("/orders/{order_id}")
def cancel_order(order_id: str):
    if order_id not in orders:
        raise HTTPException(status_code=404, detail=f"주문 {order_id} 없음")
    orders[order_id]["status"] = "cancelled"
    return {"message": f"주문 {order_id} 취소됨"}


# ============================================================
# Chaos 테스트용 엔드포인트
# ============================================================

@app.post("/simulate/oom")
def simulate_oom(mb: int = 100):
    """메모리 점유로 OOM 유발"""
    global _memory_hog
    chunk = " " * (mb * 1024 * 1024)
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


@app.post("/simulate/slow")
def simulate_slow(seconds: float = 2.0):
    """느린 응답 시뮬레이션"""
    time.sleep(seconds)
    return {"status": "completed", "delay_seconds": seconds}


@app.post("/simulate/reset")
def simulate_reset():
    global _memory_hog
    _memory_hog = []
    return {"status": "reset"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
