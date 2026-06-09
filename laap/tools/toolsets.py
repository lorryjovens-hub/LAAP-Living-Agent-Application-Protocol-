"""
LAAP — Toolsets Module (ported from Hermes Agent)

Composable tool groups with built-in toolsets for all common scenarios.
Individual tools can belong to multiple toolsets for flexible composition.
"""

from __future__ import annotations
import time
from typing import Dict, List, Set, Optional


# ── Core Tools ────────────────────────────────────────────────────
_LAAP_CORE_TOOLS = [
    "read_file", "write_file", "patch", "search_files",
    "terminal", "shell",
    "web_search", "web_extract",
    "todo", "memory", "clarify",
    "skill_view", "skills_list",
    "execute_code",
]

# ── Toolset Definitions ──────────────────────────────────────────

_TOOLSETS: Dict[str, List[str]] = {
    "core": _LAAP_CORE_TOOLS,
    "terminal": ["terminal", "shell", "process"],
    "file": ["read_file", "write_file", "patch", "search_files"],
    "web": ["web_search", "web_extract", "web_browse"],
    "browser": [
        "browser_navigate", "browser_snapshot", "browser_click",
        "browser_type", "browser_scroll", "browser_back",
        "browser_press", "browser_get_images", "browser_console",
    ],
    "vision": ["vision_analyze", "image_generate"],
    "delegation": ["delegate_task", "execute_code"],
    "cron": ["cronjob"],
    "messaging": ["send_message"],
    "session": ["session_search"],

    # Composed toolsets
    "research": ["core", "web", "file", "vision"],
    "coding": ["core", "terminal", "file", "delegation", "vision"],
    "full_stack": ["core", "terminal", "file", "web", "browser", "delegation", "vision"],
    "devops": ["core", "terminal", "file", "web"],
    "data_science": ["core", "terminal", "file", "web", "vision"],
    "writing": ["core", "file", "web"],
    "minimal": ["core"],
    "all": ["core", "terminal", "file", "web", "browser", "vision",
            "delegation", "cron", "messaging", "session"],
}

_RESOLVE_CACHE: Dict[str, tuple[float, List[str]]] = {}
_CACHE_TTL = 30.0


def get_all_toolsets() -> Dict[str, List[str]]:
    """Return all defined toolsets."""
    return dict(_TOOLSETS)


def get_toolset(name: str) -> List[str]:
    """Return tools for a single toolset (raw, no recursion)."""
    return list(_TOOLSETS.get(name, []))


def resolve_toolset(name: str, _depth: int = 0) -> List[str]:
    """Recursively resolve a toolset to a flat list of tool names."""
    if _depth > 10:
        return []
    now = time.monotonic()
    cached = _RESOLVE_CACHE.get(name)
    if cached and now - cached[0] < _CACHE_TTL:
        return list(cached[1])
    raw = _TOOLSETS.get(name, [])
    if not raw:
        return []
    result: List[str] = []
    seen: Set[str] = set()
    for item in raw:
        if item in _TOOLSETS and item != name:
            for t in resolve_toolset(item, _depth + 1):
                if t not in seen:
                    result.append(t)
                    seen.add(t)
        else:
            if item not in seen:
                result.append(item)
                seen.add(item)
    _RESOLVE_CACHE[name] = (now, list(result))
    return result


def validate_toolset(name: str, available_tools: Set[str]) -> List[str]:
    """Validate a toolset: return tools that exist in available_tools."""
    tools = resolve_toolset(name)
    return [t for t in tools if t in available_tools]


def define_toolset(name: str, tools: List[str], overwrite: bool = False) -> bool:
    """Define a new toolset or overwrite an existing one."""
    if name in _TOOLSETS and not overwrite:
        return False
    _TOOLSETS[name] = list(tools)
    _RESOLVE_CACHE.pop(name, None)
    return True


def invalidate_cache() -> None:
    """Clear all resolved toolset caches."""
    _RESOLVE_CACHE.clear()


def resolve_multiple(names: List[str]) -> List[str]:
    """Resolve multiple toolsets into a single flat list (deduplicated)."""
    seen: Set[str] = set()
    result: List[str] = []
    for name in names:
        for tool in resolve_toolset(name):
            if tool not in seen:
                result.append(tool)
                seen.add(tool)
    return result
