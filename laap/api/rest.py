"""REST API Framework"""
from __future__ import annotations
import time, json, logging, uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("api.rest")

@dataclass
class Endpoint:
    path: str = ""
    method: str = "GET"
    handler: Optional[Callable] = None
    description: str = ""

class RESTRouter:
    def __init__(self):
        self._endpoints: List[Endpoint] = []
    def get(self, path: str, handler: Callable):
        self._endpoints.append(Endpoint(path=path, method="GET", handler=handler))
    def post(self, path: str, handler: Callable):
        self._endpoints.append(Endpoint(path=path, method="POST", handler=handler))
    def put(self, path: str, handler: Callable):
        self._endpoints.append(Endpoint(path=path, method="PUT", handler=handler))
    def delete(self, path: str, handler: Callable):
        self._endpoints.append(Endpoint(path=path, method="DELETE", handler=handler))
    def handle(self, method: str, path: str, request: Dict = None) -> Dict:
        for ep in self._endpoints:
            if ep.method == method and ep.path == path:
                if ep.handler:
                    return ep.handler(request or {})
        return {"error": "not_found", "status": 404}
    def get_openapi_spec(self) -> Dict:
        paths = {}
        for ep in self._endpoints:
            if ep.path not in paths:
                paths[ep.path] = {}
            paths[ep.path][ep.method.lower()] = {"summary": ep.description}
        return {"openapi": "3.0.0", "info": {"title": "LAAP API", "version": "1.0"}, "paths": paths}

class ResponseFormatter:
    @staticmethod
    def success(data: Any = None, message: str = "ok") -> Dict:
        return {"status": "success", "message": message, "data": data, "timestamp": time.time()}
    @staticmethod
    def error(message: str, code: int = 400) -> Dict:
        return {"status": "error", "message": message, "code": code, "timestamp": time.time()}
