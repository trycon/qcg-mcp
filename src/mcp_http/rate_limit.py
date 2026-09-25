"""Per-caller rate limiting for /mcp (token buckets, in memory).

Requests that act on a customer's data are limited per credential; public
discovery requests (tools/list, UI resources…) per client IP. Credentials are
kept only as a SHA-256 digest. Each server task keeps its own buckets, so the
effective limit scales with the task count — this is abuse protection, not
metering; the Scanova API enforces its own quotas behind it.
"""

import hashlib
import threading
import time
from dataclasses import dataclass

# Buckets idle this long are dropped, so the table can't grow without bound.
_IDLE_S = 15 * 60


@dataclass
class _Bucket:
    tokens: float
    updated: float


class RateLimiter:
    def __init__(self, per_minute: int, burst: int | None = None, clock=time.monotonic) -> None:
        self.rate = per_minute / 60.0
        self.capacity = float(burst if burst is not None else per_minute)
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()
        self._last_sweep = clock()

    def acquire(self, key: str, cost: int = 1) -> float:
        """Take `cost` tokens for `key`. Returns 0 if allowed, else seconds to wait."""
        now = self._clock()
        with self._lock:
            self._sweep(now)
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = self._buckets[key] = _Bucket(self.capacity, now)
            else:
                bucket.tokens = min(self.capacity, bucket.tokens + (now - bucket.updated) * self.rate)
                bucket.updated = now
            if bucket.tokens >= cost:
                bucket.tokens -= cost
                return 0.0
            return (cost - bucket.tokens) / self.rate

    def _sweep(self, now: float) -> None:
        if now - self._last_sweep < 60:
            return
        self._last_sweep = now
        for key in [k for k, b in self._buckets.items() if now - b.updated > _IDLE_S]:
            del self._buckets[key]


def credential_key(credential: str) -> str:
    return "cred:" + hashlib.sha256(credential.encode()).hexdigest()
