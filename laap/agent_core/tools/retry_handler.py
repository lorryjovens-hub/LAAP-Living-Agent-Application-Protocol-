"""Tool Retry — 工具调用错误处理/重试/降级"""
from __future__ import annotations
import time, logging, random
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("agent_core.tools.retry")

class RetryHandler:
    """工具重试处理器 — 指数退避+熔断+降级"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._circuit: Dict[str, Dict] = {}
        self._stats = {"total_retries": 0, "total_failures": 0, "circuit_breaks": 0}
    
    def call(self, fn: Callable, *args, tool_name: str = "unknown", **kwargs) -> Any:
        """带重试和熔断的函数调用"""
        # 检查熔断
        if tool_name in self._circuit:
            state = self._circuit[tool_name]
            if state["status"] == "open":
                if time.time() - state["last_failure"] < state["recovery_time"]:
                    self._stats["circuit_breaks"] += 1
                    raise Exception(f"Circuit breaker open for {tool_name}")
                else:
                    state["status"] = "half-open"
        
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                result = fn(*args, **kwargs)
                # 成功: 关闭熔断
                if tool_name in self._circuit:
                    self._circuit[tool_name]["status"] = "closed"
                    self._circuit[tool_name]["failures"] = 0
                return result
            except Exception as e:
                last_error = e
                self._stats["total_failures"] += 1
                
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt) + random.uniform(0, 0.5), self.max_delay)
                    self._stats["total_retries"] += 1
                    logger.warning(f"Retry {attempt+1}/{self.max_retries} for {tool_name}: {e}")
                    time.sleep(delay)
                else:
                    # 打开熔断
                    self._circuit[tool_name] = {
                        "status": "open", "failures": self._circuit.get(tool_name, {}).get("failures", 0) + 1,
                        "last_failure": time.time(), "recovery_time": min(30 * (2 ** (self._circuit.get(tool_name, {}).get("failures", 0))), 300)
                    }
        
        raise last_error
    
    def get_stats(self) -> dict:
        return dict(self._stats, circuits=len(self._circuit))
