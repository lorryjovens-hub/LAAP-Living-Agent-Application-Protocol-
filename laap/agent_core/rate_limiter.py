"""RateLimiter — 请求速率限制(TokenBucket算法)"""
from __future__ import annotations
import time, threading, logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.rate_limiter")

class TokenBucket:
    def __init__(self, rate: float = 10, capacity: int = 20):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.RLock()
    def consume(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    def get_wait_time(self) -> float:
        with self._lock:
            if self.tokens >= 1:
                return 0
            return (1 - self.tokens) / max(self.rate, 0.001)

class RateLimiter:
    def __init__(self):
        self._buckets: Dict[str, TokenBucket] = {}
        self._defaults = {"deepseek": (10, 20), "openai": (20, 40), "default": (5, 10)}
    def acquire(self, scope: str, tokens: int = 1, timeout: float = 10.0) -> bool:
        if scope not in self._buckets:
            rate, cap = self._defaults.get(scope, self._defaults["default"])
            self._buckets[scope] = TokenBucket(rate, cap)
        start = time.time()
        while time.time() - start < timeout:
            if self._buckets[scope].consume(tokens):
                return True
            time.sleep(0.1)
        return False
    def get_stats(self) -> dict:
        return {k: {"tokens": round(b.tokens, 1), "rate": b.rate} for k, b in self._buckets.items()}
