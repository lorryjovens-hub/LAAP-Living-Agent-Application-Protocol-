"""
LAAP — Tool Registry
Central registry for tool registration, discovery, and execution.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import json, logging, threading

from laap.tools.base import Tool

logger = logging.getLogger("laap.tools")


class ToolRegistry:
    """Central registry for tool registration and execution (thread-safe)."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = {}
        self._lock = threading.RLock()

    def register(self, tool: Tool, overwrite: bool = False):
        """Register a tool. Skips if name exists (unless overwrite=True)."""
        with self._lock:
            if tool.name in self._tools and not overwrite:
                logger.debug(f"工具已存在，跳过注册: {tool.name}")
                return False
            if tool.name in self._tools and overwrite:
                logger.warning(f"工具已存在，覆盖: {tool.name}")
            self._tools[tool.name] = tool
            if tool.category not in self._categories:
                self._categories[tool.category] = []
            if tool.name not in self._categories[tool.category]:
                self._categories[tool.category].append(tool.name)
            logger.debug(f"已注册工具: {tool.name} [{tool.category}]")
            return True

    def tool(self, name: Optional[str] = None, category: str = "general",
             description: Optional[str] = None):
        """Decorator: @registry.tool(name=..., category=..., description=...)

        Syntactic sugar over register_fn. Returns a decorator that registers
        the decorated function and returns it unchanged so it remains usable.
        """
        def decorator(fn: Callable):
            self.register_fn(fn, name=name, category=category, description=description)
            return fn
        return decorator

    def register_fn(self, fn: Callable, name: Optional[str] = None,
                    category: str = "general", description: Optional[str] = None):
        from inspect import signature, getdoc
        from laap.tools.base import infer_json_schema
        sig = signature(fn)
        hints = {}
        for pname, p in sig.parameters.items():
            if pname not in ("self", "cls", "agent", "fc"):
                hints[pname] = p.annotation if p.annotation != p.empty else str
        param_descs = {}
        doc = getdoc(fn)
        if doc:
            try:
                from docstring_parser import parse as doc_parse
                for p in (doc_parse(doc).params or []):
                    param_descs[p.arg_name] = p.description or ""
            except Exception:
                pass
        schema = infer_json_schema(hints, param_descs)
        tool = Tool(
            name=name or fn.__name__,
            description=description or fn.__doc__ or "",
            parameters={"type": "object", "properties": schema["properties"],
                        "required": schema.get("required", [])},
            handler=fn, category=category,
        )
        return self.register(tool)

    def get(self, name: str) -> Optional[Tool]:
        with self._lock:
            return self._tools.get(name)

    def call(self, name: str, **kwargs) -> Any:
        with self._lock:
            tool = self._tools.get(name)
        if not tool:
            return json.dumps({"error": f"Tool '{name}' not found"})
        try:
            return tool.handler(**kwargs)
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {str(e)[:200]}"})

    def list(self, category: Optional[str] = None) -> List[Tool]:
        with self._lock:
            if category:
                return [self._tools[n] for n in self._categories.get(category, [])
                        if n in self._tools]
            return list(self._tools.values())

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._tools)

    @property
    def categories(self) -> List[str]:
        with self._lock:
            return list(self._categories.keys())

    def count_by_category(self) -> Dict[str, int]:
        with self._lock:
            return {cat: len(tools) for cat, tools in self._categories.items()}
