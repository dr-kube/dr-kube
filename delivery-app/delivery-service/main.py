"""
delivery-service: 배달 상태 추적 서비스
- 주문별 배달 상태 관리 (접수→픽업→배달중→완료)
- 상태 자동 전환 시뮬레이션
"""
import os
import time
import uuid
import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="delivery-service", version="1.0.0")

# Prometheus 메트릭
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["endpoint"])
ACTIVE_DELIVERIES = Gauge("active_deliveries", "Currently active deliveries")
DELIVERY_TOTAL = Counter("deliveries_total", "Total deliveries", ["status"])

# 배달 상태 순서
DELIVERY_STATES = ["접수됨", "레스토랑픽업", "배달중", "완료"]

# 인메모리 배달 저장소
deliveries: dict[str, dict] = {}

# 메모리 점유용
_memory_hog: list = []


class DeliveryRequest(BaseModel):
    order_id: str
    address: str
    restaurant_name: str


def simulate_delivery_progress(delivery_id: str):
    """배달 상태를 주기적으로 자동 전환하는 백그라운드 스레드"""
    state_idx = 0
    while state_idx < len(DELIVERY_STATES) - 1:
        time.sleep(30)  # 30초마다 상태 전환
        state_idx += 1
        if delivery_id in deliveries:
            deliveries[delivery_id]["status"] = DELIVERY_STATES[state_idx]
            deliveries[delivery_id]["updated_at"] = datetime.now().isoformat()

            if DELIVERY_STATES[state_idx] == "완료":
                ACTIVE_DELIVERIES.dec()
                DELIVERY_TOTAL.labels(status="completed").inc()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "delivery-service",
        "active_deliveries": len([d for d in deliveries.values() if d["status"] != "완료"]),
    }


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/deliveries")
def list_deliveries():
    with REQUEST_LATENCY.labels(endpoint="/deliveries").time():
        REQUEST_COUNT.labels(method="GET", endpoint="/deliveries", status="200").inc()
        return list(deliveries.values())


@app.post("/deliveries", status_code=201)
def create_delivery(req: DeliveryRequest):
    with REQUEST_LATENCY.labels(endpoint="/deliveries").time():
        delivery_id = str(uuid.uuid4())[:8]
        estimated_minutes = 30 + (hash(req.address) % 20)  # 30~50분 랜덤 예상

        delivery = {
            "id": delivery_id,
            "order_id": req.order_id,
            "address": req.address,
            "restaurant_name": req.restaurant_name,
            "status": DELIVERY_STATES[0],  # 접수됨
            "estimated_minutes": estimated_minutes,
            "driver": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        deliveries[delivery_id] = delivery
        ACTIVE_DELIVERIES.inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/deliveries", status="201").inc()

        # 배달 상태 자동 전환 시작
        thread = threading.Thread(
            target=simulate_delivery_progress,
            args=(delivery_id,),
            daemon=True,
        )
        thread.start()

        return delivery


@app.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: str):
    with REQUEST_LATENCY.labels(endpoint="/deliveries/{id}").time():
        if delivery_id not in deliveries:
            REQUEST_COUNT.labels(method="GET", endpoint="/deliveries/{id}", status="404").inc()
            raise HTTPException(status_code=404, detail=f"배달 {delivery_id} 없음")
        REQUEST_COUNT.labels(method="GET", endpoint="/deliveries/{id}", status="200").inc()
        return deliveries[delivery_id]


@app.get("/deliveries/order/{order_id}")
def get_delivery_by_order(order_id: str):
    """주문 ID로 배달 조회"""
    for d in deliveries.values():
        if d["order_id"] == order_id:
            REQUEST_COUNT.labels(method="GET", endpoint="/deliveries/order/{id}", status="200").inc()
            return d
    REQUEST_COUNT.labels(method="GET", endpoint="/deliveries/order/{id}", status="404").inc()
    raise HTTPException(status_code=404, detail=f"주문 {order_id}의 배달 없음")


@app.patch("/deliveries/{delivery_id}/driver")
def assign_driver(delivery_id: str, driver_name: str):
    """드라이버 배정"""
    if delivery_id not in deliveries:
        raise HTTPException(status_code=404, detail=f"배달 {delivery_id} 없음")
    deliveries[delivery_id]["driver"] = driver_name
    return deliveries[delivery_id]


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


@app.post("/simulate/reset")
def simulate_reset():
    global _memory_hog
    _memory_hog = []
    return {"status": "reset"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
