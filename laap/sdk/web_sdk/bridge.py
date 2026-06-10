"""JS-Python Bridge — Web Worker桥接"""
from __future__ import annotations
import time, json, logging, uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("sdk.web.bridge")

class BridgeProtocol:
    def __init__(self):
        self._pending: Dict[str, Callable] = {}
    def call(self, method: str, args: Dict = None, callback: Callable = None) -> str:
        msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        message = json.dumps({"id": msg_id, "method": method, "args": args or {}})
        if callback:
            self._pending[msg_id] = callback
        logger.info(f"Bridge call: {method}")
        return msg_id
    def handle_response(self, msg_id: str, result: Any):
        callback = self._pending.pop(msg_id, None)
        if callback:
            callback(result)
    def serialize(self, data: Any) -> str:
        return json.dumps(data, default=str)
    def deserialize(self, data: str) -> Any:
        return json.loads(data)

class MethodInvoker:
    def __init__(self):
        self._methods: Dict[str, Callable] = {}
    def register(self, name: str, fn: Callable):
        self._methods[name] = fn
    def invoke(self, name: str, *args, **kwargs) -> Any:
        fn = self._methods.get(name)
        if fn:
            return fn(*args, **kwargs)
        raise KeyError(f"Method not found: {name}")

class EventEmitter:
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
    def on(self, event: str, listener: Callable):
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(listener)
    def emit(self, event: str, data: Any = None):
        for listener in self._listeners.get(event, []):
            try:
                listener(data)
            except Exception as e:
                logger.error(f"Event error: {e}")
    def remove_all(self, event: str):
        self._listeners.pop(event, None)
