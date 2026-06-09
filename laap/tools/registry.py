"""
LAAP — Ao Tool Registry (upgraded with Hermes Agent auto-discovery)

AO-tool system with:
- Self-registering tool discovery via AST inspection
- Composable toolset support (via toolsets.py)
- TTL-cached availability checks
- Thread-safe registration and dispatch
- Async bridging for async tool handlers
- Keeps the `ao` singleton interface for backward compatibility
"""

from __future__ import annotations
import os
import asyncio
import ast
import importlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("laap.tools.registry")

# ── Constants ────────────────────────────────────────────────────

_CHECK_FN_TTL = 30.0
_check_fn_cache: Dict[Callable, tuple[float, bool]] = {}
_check_fn_cache_lock = threading.Lock()

# Persistent event loop for running async tool handlers
_tool_loop: Optional[asyncio.AbstractEventLoop] = None
_tool_loop_lock = threading.Lock()


# ── Availability Check Helpers ──────────────────────────────────

def _cached_check(fn: Callable) -> bool:
    """TTL-cached check_fn execution."""
    now = time.monotonic()
    with _check_fn_cache_lock:
        cached = _check_fn_cache.get(fn)
        if cached and now - cached[0] < _CHECK_FN_TTL:
            return cached[1]
    try:
        val = bool(fn())
    except Exception:
        val = False
    with _check_fn_cache_lock:
        _check_fn_cache[fn] = (now, val)
    return val


def invalidate_cache() -> None:
    """Clear all tool availability caches."""
    with _check_fn_cache_lock:
        _check_fn_cache.clear()


def _get_tool_loop():
    """Return a long-lived event loop for running async tool handlers.

    Using a persistent loop (instead of asyncio.run() which creates and
    *closes* a fresh loop every time) prevents "Event loop is closed"
    errors that occur when cached httpx/AsyncOpenAI clients attempt to
    close their transport on a dead loop.
    """
    global _tool_loop
    if _tool_loop is None or _tool_loop.is_closed():
        with _tool_loop_lock:
            if _tool_loop is None or _tool_loop.is_closed():
                _tool_loop = asyncio.new_event_loop()
    return _tool_loop


# ── Tool Entry ───────────────────────────────────────────────────

class ToolEntry:
    """A single tool's full metadata — schema, handler, constraints."""

    __slots__ = (
        "name", "toolset", "schema", "handler", "check_fn",
        "requires_env", "is_async", "description", "emoji",
        "max_concurrency", "timeout",
    )

    def __init__(self, name: str, schema: dict, handler: Callable,
                 toolset: str = "core", description: str = "",
                 check_fn: Optional[Callable] = None,
                 requires_env: Optional[List[str]] = None,
                 is_async: bool = False, emoji: str = "",
                 max_concurrency: int = 0, timeout: int = 300):
        self.name = name
        self.schema = schema
        self.handler = handler
        self.toolset = toolset
        self.description = description
        self.check_fn = check_fn
        self.requires_env = requires_env or []
        self.is_async = is_async
        self.emoji = emoji
        self.max_concurrency = max_concurrency
        self.timeout = timeout

    def is_available(self) -> bool:
        """Check whether this tool is available in the current environment."""
        if self.check_fn:
            return _cached_check(self.check_fn)
        if self.requires_env:
            return all(os.environ.get(k) for k in self.requires_env)
        return True

    def to_openai_schema(self) -> dict:
        """Return the OpenAI-compatible tool schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.schema,
            },
        }


# ── Registry ─────────────────────────────────────────────────────

class AoRegistry:
    """Central tool registry with auto-discovery, toolsets, and dispatch."""

    def __init__(self):
        self._entries: Dict[str, ToolEntry] = {}
        self._lock = threading.RLock()
        self._discovered = False

    # ── Registration ────────────────────────────────────────────

    def _register(self, name: str, schema: dict, handler: Callable,
                 toolset: str = "core", description: str = "",
                 check_fn: Optional[Callable] = None,
                 requires_env: Optional[List[str]] = None,
                 is_async: bool = False, emoji: str = "",
                 max_concurrency: int = 0, timeout: int = 300) -> bool:
        """Register a tool. Returns True if newly registered."""
        with self._lock:
            if name in self._entries:
                logger.debug(f"Tool already registered, skipping: {name}")
                return False
            entry = ToolEntry(
                name=name, schema=schema, handler=handler,
                toolset=toolset, description=description,
                check_fn=check_fn, requires_env=requires_env,
                is_async=is_async, emoji=emoji,
                max_concurrency=max_concurrency, timeout=timeout,
            )
            self._entries[name] = entry
            logger.debug(f"Registered tool: {name} [{toolset}]")
            return True

    def register_fn(self, fn: Callable, name: Optional[str] = None,
                    toolset: str = "core", description: Optional[str] = None):
        """Register a function as a tool, inferring schema from its signature.

        Args:
            fn: The function to register
            name: Tool name (defaults to function name)
            toolset: Toolset membership
            description: Optional description (defaults to docstring)
        """
        import inspect
        from laap.tools.base import infer_json_schema

        tool_name = name or fn.__name__
        desc = description or inspect.getdoc(fn) or ""
        sig = inspect.signature(fn)
        schema = infer_json_schema(fn)

        self._register(tool_name, schema, fn, toolset=toolset,
                      description=desc)

    # ── Discovery ──────────────────────────────────────────────

    def _has_registration(self, path: Path) -> bool:
        """Check if a module has top-level registry.register() calls."""
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception:
            return False
        for stmt in tree.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                func = stmt.value.func
                if (isinstance(func, ast.Attribute) and func.attr == "register"
                        and isinstance(func.value, ast.Name)
                        and func.value.id in ("ao", "registry")):
                    return True
        return False

    def discover_tools(self, tools_dir: Optional[Path] = None) -> List[str]:
        """Auto-import all self-registering tool modules.

        Args:
            tools_dir: Directory to scan (defaults to laap/tools/)

        Returns:
            List of successfully imported module names
        """
        td = tools_dir or Path(__file__).resolve().parent
        modules = [
            f"laap.tools.{p.stem}" for p in sorted(td.glob("*.py"))
            if p.name not in {"__init__.py", "registry.py", "toolsets.py",
                              "base.py", "tool_registry.py", "hermes_adapter.py"}
            and self._has_registration(p)
        ]
        imported = []
        for mod in modules:
            try:
                importlib.import_module(mod)
                imported.append(mod)
                logger.info(f"Discovered tool module: {mod}")
            except Exception as e:
                logger.warning(f"Tool module {mod}: {e}")
        self._discovered = True
        return imported

    # ── Queries ────────────────────────────────────────────────

    def get(self, name: str) -> Optional[ToolEntry]:
        """Get a tool entry by name."""
        with self._lock:
            return self._entries.get(name)

    def get_all(self) -> Dict[str, ToolEntry]:
        """Get all registered tools."""
        with self._lock:
            return dict(self._entries)

    def get_names(self) -> List[str]:
        """Get all registered tool names."""
        with self._lock:
            return list(self._entries.keys())

    def get_available(self, toolsets: Optional[List[str]] = None) -> List[str]:
        """Get names of available (callable) tools, optionally filtered by toolsets.

        Args:
            toolsets: If provided, only return tools matching these toolsets

        Returns:
            Alphabetically sorted list of available tool names
        """
        from laap.tools.toolsets import resolve_multiple

        with self._lock:
            if toolsets:
                allowed = set(resolve_multiple(toolsets))
                entries = {n: e for n, e in self._entries.items() if n in allowed}
            else:
                entries = dict(self._entries)

            result = []
            for name, entry in entries.items():
                if entry.is_available():
                    result.append(name)
            return sorted(result)

    def get_tool_definitions(self, toolsets: Optional[List[str]] = None) -> List[dict]:
        """Get OpenAI-compatible tool definitions for enabled/available tools.

        Args:
            toolsets: Optional toolset filter

        Returns:
            List of OpenAI-compatible function tool schemas
        """
        available = set(self.get_available(toolsets))
        return [
            entry.to_openai_schema()
            for name, entry in self._entries.items()
            if name in available
        ]

    # ── Dispatch ───────────────────────────────────────────────

    def dispatch(self, name: str, args: dict) -> str:
        """Execute a tool by name with the given arguments.

        Supports both Hermes-style (handler takes single `args` dict)
        and LAAP-style (handler takes **kwargs).

        Args:
            name: Tool name
            args: Tool arguments dict

        Returns:
            String result of tool execution

        Raises:
            KeyError: If tool not found
            ValueError: If tool is not available
        """
        entry = self.get(name)
        if not entry:
            return json.dumps({"error": f"Tool '{name}' not registered", "status": "error"})

        if not entry.is_available():
            return json.dumps({"error": f"Tool '{name}' not available", "status": "error"})

        try:
            handler = entry.handler
            import inspect
            sig = inspect.signature(handler)
            params = list(sig.parameters.values())
            # Detect Hermes-style (single `args` or `kwargs` dict param)
            hermes_style = (
                len(params) == 1
                and params[0].name in ("args", "kwargs")
                and (
                    params[0].annotation in (dict, 'dict', Any, inspect.Parameter.empty)
                    or (isinstance(params[0].annotation, str) and params[0].annotation == 'dict')
                )
            )

            if hermes_style:
                result = handler(args)
            elif entry.is_async:
                loop = _get_tool_loop()
                result = loop.run_until_complete(handler(**args))
            else:
                result = handler(**args)

            if not isinstance(result, str):
                try:
                    result = json.dumps(result, ensure_ascii=False)
                except (TypeError, ValueError):
                    result = str(result)
            return result

        except Exception as e:
            logger.error(f"Tool '{name}' error: {e}", exc_info=True)
            return json.dumps({"error": str(e), "status": "error"})

    # ── Bulk Operations ────────────────────────────────────────

    def unregister(self, name: str) -> bool:
        """Remove a tool from the registry."""
        with self._lock:
            return self._entries.pop(name, None) is not None

    def clear(self):
        """Remove all registered tools."""
        with self._lock:
            self._entries.clear()

    def count(self) -> int:
        """Return number of registered tools."""
        with self._lock:
            return len(self._entries)



    # ── Backward-Compatible Shims ─────────────────────────────

    def get_entry(self, name: str) -> Optional[ToolEntry]:
        """Backward compatible: alias for get()."""
        return self.get(name)

    def get_definitions(self, toolsets: Optional[List[str]] = None) -> List[dict]:
        """Backward compatible: alias for get_tool_definitions()."""
        return self.get_tool_definitions(toolsets)

    def get_all_names(self) -> List[str]:
        """Backward compatible: alias for get_names()."""
        return self.get_names()

    def register(self, name: str, schema: dict = None, handler: Callable = None,
                 toolset: str = "core", description: str = "",
                 check_fn: Optional[Callable] = None,
                 requires_env: Optional[List[str]] = None,
                 is_async: bool = False, emoji: str = "",
                 max_concurrency: int = 0, timeout: int = 300,
                 override: bool = False) -> bool:
        """Register a tool with backward-compatible override support."""
        # Handle override: unregister first if name exists
        if override and name in self._entries:
            self.unregister(name)
        # Create schema from kwargs if not provided
        actual_schema = schema if schema is not None else {}
        actual_handler = handler if handler is not None else (lambda **kw: "")
        return self._register(
            name=name, schema=actual_schema, handler=actual_handler,
            toolset=toolset, description=description,
            check_fn=check_fn, requires_env=requires_env,
            is_async=is_async, emoji=emoji,
            max_concurrency=max_concurrency, timeout=timeout,
        )

    def tool_result(self, data: Any = None, error: Optional[str] = None,
                    success: Any = None, value: Any = None, **kwargs) -> str:
        """Backward compatible: format tool result.

        Supports multiple calling conventions:
            tool_result(data={"ok": True})  -> {"ok": True}
            tool_result(success=True, value=42)  -> {"success": True, "value": 42}
        """
        d = {}
        if data is not None and isinstance(data, dict):
            d = data
        elif data is not None:
            d = {"result": data}
        else:
            if success is not None:
                d["success"] = success
            if value is not None:
                d["value"] = value
            if error:
                d["error"] = error
        d.update(kwargs)
        return json.dumps(d)


    def get_names_for_toolset(self, toolset: str) -> List[str]:
        """Backward compatible: get tool names in a specific toolset.

        Filters by the tool's declared `toolset` attribute.
        """
        with self._lock:
            return sorted([
                n for n, e in self._entries.items()
                if e.toolset == toolset
            ])

    def tool_error(self, message: str, **kwargs) -> str:
        """Backward compatible: format tool error with extra fields."""
        d = {"error": message, "status": "error"}
        d.update(kwargs)
        return json.dumps(d)

# ── Singleton ────────────────────────────────────────────────────

ao = AoRegistry()
"""The global Ao (AO-tool) registry instance.

Usage:
    from laap.tools.registry import ao

    # Register a tool
    ao.register("my_tool", schema, handler, toolset="core")

    # Auto-discover tools
    ao.discover_tools()

    # Get available tools
    tools = ao.get_available(toolsets=["coding"])
"""


# ── Convenience re-exports ───────────────────────────────────────

register = ao.register
discover_tools = ao.discover_tools
get_available = ao.get_available
