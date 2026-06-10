"""LAAP Server SDK — 服务端"""
from __future__ import annotations
import time, json, logging, uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("sdk.server.server")

class RequestRouter:
    def __init__(self):
        self._routes: Dict[str, Callable] = {}
    def register(self, path: str, handler: Callable):
        self._routes[path] = handler
    def route(self, path: str, request: Dict) -> Any:
        handler = self._routes.get(path)
        if handler:
            return handler(request)
        return {"error": f"No handler for {path}"}

class MiddlewareChain:
    def __init__(self):
        self._middlewares: List[Callable] = []
    def use(self, middleware: Callable):
        self._middlewares.append(middleware)
    def process(self, request: Dict) -> Dict:
        for mw in self._middlewares:
            request = mw(request)
        return request

class LAAPServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.router = RequestRouter()
        self.middleware = MiddlewareChain()
        self._running = False
    def start(self):
        self._running = True
        logger.info(f"LAAPServer started: {self.host}:{self.port}")
    def stop(self):
        self._running = False
        logger.info("LAAPServer stopped")
    def handle_request(self, path: str, request: Dict) -> Any:
        processed = self.middleware.process(request)
        return self.router.route(path, processed)
