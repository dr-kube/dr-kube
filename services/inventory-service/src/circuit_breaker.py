"""서킷 브레이커 구현"""
import time
import threading
from enum import Enum
from config import (
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT_S,
    CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS,
)


class State(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(self):
        self._state = State.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        return self._state.value

    def call(self, fn, *args, **kwargs):
        with self._lock:
            if self._state == State.OPEN:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= CIRCUIT_BREAKER_RECOVERY_TIMEOUT_S:
                    self._state = State.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    raise CircuitOpenError(
                        f"Circuit OPEN. 복구 대기 중 ({elapsed:.0f}s / {CIRCUIT_BREAKER_RECOVERY_TIMEOUT_S}s)"
                    )

            if self._state == State.HALF_OPEN:
                if self._half_open_calls >= CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS:
                    raise CircuitOpenError("HALF_OPEN 최대 호출 수 초과")
                self._half_open_calls += 1

        try:
            result = fn(*args, **kwargs)
            with self._lock:
                self._on_success()
            return result
        except Exception as e:
            with self._lock:
                self._on_failure()
            raise e

    def _on_success(self):
        self._failure_count = 0
        self._state = State.CLOSED

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= CIRCUIT_BREAKER_FAILURE_THRESHOLD:
            self._state = State.OPEN


class CircuitOpenError(Exception):
    pass


# 전역 인스턴스 (서비스당 하나)
circuit_breaker = CircuitBreaker()
