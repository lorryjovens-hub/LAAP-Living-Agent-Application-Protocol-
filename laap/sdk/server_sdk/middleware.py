"""Server Middleware"""
from __future__ import annotations
import time, json, logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("sdk.server.middleware")

class Middleware:
    def process(self, request: Dict) -> Dict:
        return request

class LoggingMiddleware(Middleware):
    def process(self, request: Dict) -> Dict:
        logger.info(f"Request: {request.get('path', 'unknown')}")
        return request

class AuthMiddleware(Middleware):
    def __init__(self, valid_tokens: List[str] = None):
        self.valid_tokens = valid_tokens or []
    def process(self, request: Dict) -> Dict:
        token = request.get("headers", {}).get("Authorization", "")
        if token not in self.valid_tokens:
            logger.warning("Auth failed")
        return request

class MetricsMiddleware(Middleware):
    def __init__(self):
        self._request_count = 0
        self._total_latency = 0.0
    def process(self, request: Dict) -> Dict:
        self._request_count += 1
        return request
    def get_stats(self) -> dict:
        return {"requests": self._request_count, "avg_latency": 0}
