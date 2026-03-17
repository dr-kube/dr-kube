"""
recommendation-proxy 설정 상수
★ DR-Kube 에이전트 수정 대상 파일

추천 서비스 앞단 캐싱 프록시의 동작을 제어.
에이전트가 이 값을 수정 → PR → ArgoCD → ConfigMap 갱신 → Pod 재시작으로 반영.
"""
import os

# ── 캐시 설정 ─────────────────────────────────────────────
# TTL 너무 짧으면 recommendationservice 과부하 → CPUThrottling
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))

# 최대 캐시 항목 수. 너무 크면 메모리 증가 → OOMKilled
CACHE_MAX_ENTRIES: int = int(os.getenv("CACHE_MAX_ENTRIES", "500"))

# ── 업스트림 추천 서비스 ──────────────────────────────────
RECOMMENDATION_SERVICE_HOST: str = os.getenv(
    "RECOMMENDATION_SERVICE_HOST",
    "recommendationservice.online-boutique.svc.cluster.local",
)
RECOMMENDATION_SERVICE_PORT: int = int(os.getenv("RECOMMENDATION_SERVICE_PORT", "8080"))

# 타임아웃 너무 낮으면 ServiceHighLatencyP99 alert
RECOMMENDATION_TIMEOUT_MS: int = int(os.getenv("RECOMMENDATION_TIMEOUT_MS", "800"))

# 재시도 횟수. 너무 높으면 레이턴시 누적
RECOMMENDATION_MAX_RETRIES: int = int(os.getenv("RECOMMENDATION_MAX_RETRIES", "3"))

# ── 응답 제한 ─────────────────────────────────────────────
# 요청당 최대 추천 수. 너무 크면 응답 페이로드 증가 → 메모리 압박
MAX_RECOMMENDATIONS_PER_REQUEST: int = int(os.getenv("MAX_RECOMMENDATIONS_PER_REQUEST", "10"))

# 배치 처리 크기 (여러 user_id 일괄 조회 시)
BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "5"))

# ── 서버 설정 ─────────────────────────────────────────────
SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8001"))
MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "40"))
