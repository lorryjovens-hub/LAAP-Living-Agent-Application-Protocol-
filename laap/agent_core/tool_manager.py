"""
LAAP Tool Manager — 工具注册与调用系统
类似 Hermes 的 tool system
"""
from __future__ import annotations
import time, json, logging, inspect, threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, get_type_hints

logger = logging.getLogger("agent_core.tools")

@dataclass
class ToolResult:
    success: bool = True
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0
    data: Any = None

@dataclass
class Tool:
    """工具定义 — 与OpenAI Function Calling格式兼容"""
    name: str = ""
    description: str = ""
    parameters: Dict = field(default_factory=dict)
    handler: Optional[Callable] = None
    enabled: bool = True
    category: str = "general"
    
    def to_openai_format(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

class ToolManager:
    """工具管理器 — 注册/发现/调用"""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._history: List[Dict] = []
        self._lock = threading.RLock()
    
    def register(self, tool: Tool):
        with self._lock:
            self._tools[tool.name] = tool
            logger.info(f"Tool registered: {tool.name}")
    
    def register_fn(self, name: str, description: str = "", 
                   parameters: Dict = None, category: str = "general"):
        """装饰器方式注册工具"""
        def decorator(func):
            # 自动从函数签名提取参数
            sig = inspect.signature(func)
            if not parameters:
                params = {"type": "object", "properties": {}, "required": []}
                for p_name, p_param in sig.parameters.items():
                    if p_name == 'self': continue
                    param_type = "string"
                    if p_param.annotation != inspect.Parameter.empty:
                        type_map = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}
                        param_type = type_map.get(p_param.annotation, "string")
                    params["properties"][p_name] = {"type": param_type, "description": ""}
                    if p_param.default == inspect.Parameter.empty:
                        params["required"].append(p_name)
            else:
                params = parameters
            
            tool = Tool(name=name or func.__name__, description=description or func.__doc__ or "",
                       parameters=params, handler=func, category=category)
            self.register(tool)
            return func
        return decorator
    
    def unregister(self, name: str):
        with self._lock:
            self._tools.pop(name, None)
    
    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)
    
    def list_tools(self, category: str = "") -> List[Tool]:
        if category:
            return [t for t in self._tools.values() if t.category == category and t.enabled]
        return [t for t in self._tools.values() if t.enabled]
    
    def call(self, name: str, arguments: Dict = None) -> ToolResult:
        """调用工具并返回结果"""
        start = time.time()
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found")
        if not tool.handler:
            return ToolResult(success=False, error=f"Tool '{name}' has no handler")
        
        try:
            args = arguments or {}
            result = tool.handler(**args)
            elapsed = (time.time() - start) * 1000
            
            output = str(result) if result is not None else ""
            tr = ToolResult(success=True, output=output, duration_ms=round(elapsed, 2), data=result)
            
            with self._lock:
                self._history.append({"tool": name, "args": args, "result": output[:200],
                                     "duration_ms": tr.duration_ms, "success": True})
                if len(self._history) > 1000:
                    self._history = self._history[-1000:]
            
            return tr
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            tr = ToolResult(success=False, error=str(e), duration_ms=round(elapsed, 2))
            with self._lock:
                self._history.append({"tool": name, "args": args, "result": str(e)[:200],
                                     "duration_ms": tr.duration_ms, "success": False})
            return tr
    
    def get_openai_tools(self) -> List[dict]:
        return [t.to_openai_format() for t in self.list_tools()]
    
    def get_stats(self) -> dict:
        total = len(self._history)
        success = sum(1 for h in self._history if h["success"])
        return {"total_calls": total, "success_rate": round(success/max(total,1)*100, 1),
                "tools": len(self._tools), "history": total}
