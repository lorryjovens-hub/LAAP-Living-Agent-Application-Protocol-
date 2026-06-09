"""
LAAP — Hermes Tool Adapter
Bridges the Hermes-style Ao Tool Registry (registry.py) with the
LAAP ToolRegistry (tool_registry.py) used by the Agent class.

This adapter enables:
- Hermes-curated skills to be exposed as LAAP tools
- Bidirectional tool discovery across both registries
- Sync patterns: pull (import from Ao) and push (export to Ao)
"""
from __future__ import annotations
import json, logging
from typing import Any, Callable, Dict, List, Optional

from laap.tools.tool_registry import ToolRegistry, Tool
from laap.tools.registry import ao as ao_registry
from laap.tools.base import infer_json_schema

logger = logging.getLogger("laap.tools.hermes_adapter")


class HermesAdapter:
    """Adapts Hermes Ao tools to LAAP ToolRegistry format.

    Usage:
        adapter = HermesAdapter(laap_registry)
        adapter.sync_from_ao()           # import all Ao tools as LAAP tools
        adapter.push_to_ao("my_tool")    # export a LAAP tool back to Ao
    """

    def __init__(self, laap_registry: ToolRegistry):
        self._laap = laap_registry
        self._sync_count = 0
        self._mapping: Dict[str, str] = {}  # ao_name -> laap_name

    # ── Sync: Ao → LAAP ──────────────────────────────────────

    def sync_from_ao(self, toolset_filter: Optional[str] = None,
                     overwrite: bool = False) -> int:
        """Import all Ao-registered tools into the LAAP ToolRegistry.

        Args:
            toolset_filter: If set, only sync tools from this toolset
            overwrite: Overwrite existing LAAP tools with same name

        Returns:
            Number of tools imported
        """
        count = 0
        for name in ao_registry.get_all_names():
            if toolset_filter and name not in ao_registry.get_names_for_toolset(toolset_filter):
                continue
            entry = ao_registry.get_entry(name)
            if not entry:
                continue

            # Build a LAAP Tool from the Ao entry
            handler = self._make_laap_handler(entry.name)
            schema = entry.schema or {}
            tool = Tool(
                name=entry.name,
                description=entry.description or schema.get("description", ""),
                parameters={
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", []),
                },
                handler=handler,
                category=entry.toolset or "hermes",
                metadata={
                    "source": "hermes_ao",
                    "toolset": entry.toolset,
                    "requires_env": entry.requires_env,
                    "is_async": entry.is_async,
                },
            )
            if self._laap.register(tool, overwrite=overwrite):
                self._mapping[entry.name] = entry.name
                count += 1
                logger.debug("Synced Ao tool -> LAAP: %s", entry.name)

        self._sync_count += count
        return count

    def _make_laap_handler(self, name: str) -> Callable:
        """Wrap an Ao tool dispatch as a LAAP handler function."""
        def handler(**kwargs) -> str:
            return ao_registry.dispatch(name, kwargs or {})
        handler.__name__ = f"_ao_{name}"
        handler.__doc__ = f"Hermes Ao tool: {name}"
        return handler

    # ── Push: LAAP → Ao ──────────────────────────────────────

    def push_to_ao(self, laap_name: str, toolset: str = "laap",
                   overwrite: bool = False) -> bool:
        """Export a LAAP-registered tool into the Ao registry.

        Args:
            laap_name: Tool name in the LAAP registry
            toolset: Ao toolset to register under
            overwrite: Overwrite existing Ao entry

        Returns:
            True if registered successfully
        """
        laap_tool = self._laap.get(laap_name)
        if not laap_tool:
            logger.warning("Push failed: LAAP tool '%s' not found", laap_name)
            return False

        def ao_handler(args: dict) -> str:
            try:
                return laap_tool.handler(**args) if laap_tool.handler else ""
            except Exception as e:
                return json.dumps({"error": f"{type(e).__name__}: {e}"})

        ao_registry.register(
            name=laap_tool.name,
            toolset=toolset,
            schema={
                "name": laap_tool.name,
                "description": laap_tool.description,
                "parameters": laap_tool.parameters,
            },
            handler=ao_handler,
            description=laap_tool.description,
            override=overwrite,
        )
        self._mapping[laap_tool.name] = laap_tool.name
        logger.info("Pushed LAAP tool -> Ao: %s [%s]", laap_tool.name, toolset)
        return True

    def push_all_to_ao(self, toolset: str = "laap",
                       category_filter: Optional[str] = None,
                       overwrite: bool = False) -> int:
        """Export all LAAP tools matching a category into the Ao registry."""
        count = 0
        for tool in self._laap.list(category=category_filter):
            if self.push_to_ao(tool.name, toolset=toolset, overwrite=overwrite):
                count += 1
        return count

    # ── Query ────────────────────────────────────────────────

    def list_adapter_tools(self) -> List[Dict[str, Any]]:
        """List all tools known to the adapter with their sources."""
        result = []
        for laap_name, ao_name in self._mapping.items():
            laap_tool = self._laap.get(laap_name)
            ao_entry = ao_registry.get_entry(ao_name)
            result.append({
                "laap_name": laap_name,
                "ao_name": ao_name,
                "laap_category": laap_tool.category if laap_tool else None,
                "ao_toolset": ao_entry.toolset if ao_entry else None,
            })
        return result

    @property
    def mapped_count(self) -> int:
        return len(self._mapping)

    @property
    def sync_count(self) -> int:
        return self._sync_count


def sync_default(laap_registry: ToolRegistry, toolset: str = "default",
                 overwrite: bool = False) -> int:
    """Convenience: sync all default Ao tools into a LAAP registry.

    Used during agent initialization to bring in Ao-curated tools.

    Example:
        from laap.tools.hermes_adapter import sync_default
        sync_default(agent.tool_registry)
    """
    adapter = HermesAdapter(laap_registry)
    return adapter.sync_from_ao(toolset_filter=toolset, overwrite=overwrite)


# ── Ao-compatible tool decorator ─────────────────────────────

def ao_tool(name: str, toolset: str = "default", description: str = "",
            check_fn: Optional[Callable] = None,
            requires_env: Optional[List[str]] = None,
            is_async: bool = False):
    """Decorator to register a function as an Ao tool (Hermes-compatible).

    This is an alternative to @registry.tool(...) that works directly
    with the Ao registry, for tools that need Hermes-level features
    (condition checks, env requirements, async dispatch).

    The decorated function receives a single ``args`` dict parameter
    (Hermes convention) rather than keyword arguments.

    Example:
        @ao_tool(name="my_tool", toolset="custom", description="Does stuff")
        def my_tool(args: dict) -> str:
            return json.dumps({"result": args.get("key")})
    """
    def decorator(fn: Callable):
        import inspect
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())

        # Check if handler takes single "args" dict (Hermes style)
        # or expanded kwargs (LAAP style); wrap accordingly
        hermes_style = len(params) == 1 and params[0].name in ("args", "kwargs")

        if hermes_style:
            handler = fn
        else:
            def handler(args: dict) -> str:
                return fn(**args)
            handler.__name__ = fn.__name__

        ao_registry.register(
            name=name,
            toolset=toolset,
            schema={"name": name, "description": description},
            handler=handler,
            description=description,
            check_fn=check_fn,
            requires_env=requires_env or [],
            is_async=is_async,
        )
        return fn
    return decorator
