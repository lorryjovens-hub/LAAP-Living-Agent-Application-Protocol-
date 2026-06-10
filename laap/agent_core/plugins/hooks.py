"""Plugin Hooks — 插件生命周期钩子"""
from __future__ import annotations
import time, logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("agent_core.plugins.hooks")

class HookPoint(str, Enum):
    AGENT_INIT = "agent_init"
    BEFORE_CHAT = "before_chat"
    AFTER_CHAT = "after_chat"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    TOOL_RESULT = "tool_result"
    MEMORY_LOAD = "memory_load"
    MEMORY_SAVE = "memory_save"
    PLUGIN_LOAD = "plugin_load"
    PLUGIN_UNLOAD = "plugin_unload"
    ERROR = "error"
    SHUTDOWN = "shutdown"

@dataclass
class HookContext:
    hook_point: HookPoint = HookPoint.AGENT_INIT
    data: Any = None
    result: Any = None
    plugin_name: str = ""
    timestamp: float = field(default_factory=time.time)
    stop_propagation: bool = False

class HookRegistry:
    _hooks: Dict[str, List[Callable]] = {}
    
    @classmethod
    def register(cls, hook_point: HookPoint, handler: Callable, plugin: str = ""):
        key = f"{hook_point.value}"
        if key not in cls._hooks:
            cls._hooks[key] = []
        cls._hooks[key].append((handler, plugin))
        logger.debug(f"Hook registered: {hook_point.value} by {plugin or 'system'}")
    
    @classmethod
    def unregister(cls, hook_point: HookPoint, handler: Callable):
        key = hook_point.value
        if key in cls._hooks:
            cls._hooks[key] = [(h, p) for h, p in cls._hooks[key] if h != handler]
    
    @classmethod
    def trigger(cls, hook_point: HookPoint, data: Any = None) -> HookContext:
        ctx = HookContext(hook_point=hook_point, data=data)
        for handler, plugin in cls._hooks.get(hook_point.value, []):
            if ctx.stop_propagation:
                break
            try:
                ctx.plugin_name = plugin
                result = handler(ctx)
                if result is not None:
                    ctx.result = result
            except Exception as e:
                logger.error(f"Hook {hook_point.value} failed in {plugin}: {e}")
        return ctx
    
    @classmethod
    def clear(cls):
        cls._hooks.clear()
