"""인메모리 TTL 캐시"""
import time
import threading
from config import CACHE_TTL_SECONDS, CACHE_MAX_SIZE


class TTLCache:
    def __init__(self):
        self._store: dict[str, tuple[any, float]] = {}  # key → (value, expires_at)
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value):
        with self._lock:
            # 캐시 크기 초과 시 만료된 항목 먼저 제거
            if len(self._store) >= CACHE_MAX_SIZE:
                now = time.time()
                expired = [k for k, (_, exp) in self._store.items() if exp < now]
                for k in expired:
                    del self._store[k]
                # 여전히 초과면 가장 오래된 항목 제거 (LRU 근사)
                if len(self._store) >= CACHE_MAX_SIZE:
                    oldest = min(self._store, key=lambda k: self._store[k][1])
                    del self._store[oldest]

            self._store[key] = (value, time.time() + CACHE_TTL_SECONDS)

    def stats(self) -> dict:
        with self._lock:
            now = time.time()
            total = len(self._store)
            expired = sum(1 for _, (_, exp) in self._store.items() if exp < now)
            return {"total": total, "active": total - expired, "expired": expired, "max_size": CACHE_MAX_SIZE}


cache = TTLCache()
