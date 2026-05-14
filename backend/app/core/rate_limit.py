from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class BucketState:
    tokens: float
    updated_at: float


class InMemoryTokenBucket:
    def __init__(self, capacity: int, refill_window_seconds: int) -> None:
        self.capacity = capacity
        self.refill_window_seconds = refill_window_seconds
        self._buckets: dict[str, BucketState] = {}

    def allow(self, key: str, cost: int = 1) -> bool:
        now = time.monotonic()
        state = self._buckets.get(key, BucketState(tokens=self.capacity, updated_at=now))
        elapsed = now - state.updated_at
        refill_rate = self.capacity / self.refill_window_seconds
        state.tokens = min(self.capacity, state.tokens + elapsed * refill_rate)
        state.updated_at = now

        if state.tokens < cost:
            self._buckets[key] = state
            return False

        state.tokens -= cost
        self._buckets[key] = state
        return True

