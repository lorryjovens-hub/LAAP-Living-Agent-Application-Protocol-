"""Service Discovery"""
from __future__ import annotations
import time, json, logging, threading, random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("infrastructure.distributed.discovery")

@dataclass
class ServiceEndpoint:
    service_name: str = ""
    host: str = ""
    port: int = 0
    protocol: str = "http"
    health_path: str = "/health"
    weight: int = 1
    metadata: Dict = field(default_factory=dict)

class Registry:
    def __init__(self):
        self._services: Dict[str, List[ServiceEndpoint]] = {}
        self._lock = threading.RLock()
    def register(self, endpoint: ServiceEndpoint):
        with self._lock:
            if endpoint.service_name not in self._services:
                self._services[endpoint.service_name] = []
            self._services[endpoint.service_name].append(endpoint)
    def unregister(self, service_name: str, host: str, port: int):
        with self._lock:
            self._services[service_name] = [e for e in self._services.get(service_name, [])
                                           if not (e.host == host and e.port == port)]
    def discover(self, service_name: str) -> List[ServiceEndpoint]:
        return self._services.get(service_name, [])
    def discover_one(self, service_name: str) -> Optional[ServiceEndpoint]:
        endpoints = self.discover(service_name)
        return random.choice(endpoints) if endpoints else None
