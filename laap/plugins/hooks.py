"""
LAAP — Plugin Hook System

Pre/post hooks for all lifecycle events.
Inspired by claw-code's hook system with bash script support.
"""

from __future__ import annotations
import logging, os, subprocess, time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
from pathlib import Path

logger = logging.getLogger("laap.plugins.hooks")


class HookEvent(Enum):
    # Agent lifecycle
    AGENT_START = "agent:start"
    AGENT_STOP = "agent:stop"
    AGENT_ERROR = "agent:error"

    # Session lifecycle
    SESSION_START = "session:start"
    SESSION_END = "session:end"
    SESSION_COMPACT = "session:compact"

    # Tool execution
    TOOL_PRE = "tool:pre"
    TOOL_POST = "tool:post"
    TOOL_ERROR = "tool:error"

    # LLM calls
    LLM_PRE = "llm:pre"
    LLM_POST = "llm:post"

    # File operations
    FILE_WRITE = "file:write"
    FILE_DELETE = "file:delete"

    # System
    SYSTEM_BOOT = "system:boot"
    SYSTEM_SHUTDOWN = "system:shutdown"


@dataclass
class Hook:
    """A single hook registration"""
    event: HookEvent
    handler: Callable
    name: str = ""
    priority: int = 0
    once: bool = False          # Run only once then auto-remove
    timeout: int = 30
    script_path: Optional[str] = None  # Alternative: bash script path

    def __post_init__(self):
        if not self.name:
            self.name = getattr(self.handler, "__name__", str(id(self.handler)))


@dataclass
class HookResult:
    """Result of hook execution"""
    hook_name: str
    event: str
    success: bool
    duration: float
    error: Optional[str] = None
    output: Optional[str] = None


class HookManager:
    """Manages hook registrations and executions"""

    def __init__(self):
        self._hooks: Dict[HookEvent, List[Hook]] = {}

    def register(self, event: HookEvent, handler: Callable,
                 name: str = "", priority: int = 0,
                 once: bool = False, timeout: int = 30):
        hook = Hook(
            event=event, handler=handler, name=name,
            priority=priority, once=once, timeout=timeout,
        )
        self._hooks.setdefault(event, []).append(hook)
        self._hooks[event].sort(key=lambda h: h.priority, reverse=True)
        logger.debug(f"Hook registered: {name or handler.__name__} for {event.value}")

    def register_script(self, event: HookEvent, script_path: str,
                         name: str = "", priority: int = 0):
        """Register a bash script as a hook."""
        hook = Hook(
            event=event, handler=self._run_script_hook,
            name=name or os.path.basename(script_path),
            priority=priority, script_path=script_path, timeout=30,
        )
        self._hooks.setdefault(event, []).append(hook)

    def _run_script_hook(self, context: Dict = None) -> Dict:
        """Execute a bash script hook."""
        hook = self._current_hook
        if not hook or not hook.script_path:
            return {"success": False, "error": "No script path"}
        try:
            result = subprocess.run(
                [hook.script_path],
                input=json.dumps(context or {}),
                capture_output=True, text=True, timeout=hook.timeout,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Script timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, event: HookEvent, context: Optional[Dict] = None,
                raise_on_error: bool = False) -> List[HookResult]:
        """Execute all hooks for an event."""
        import json
        hooks = self._hooks.get(event, [])
        results = []

        for hook in hooks:
            t0 = time.time()
            try:
                self._current_hook = hook
                output = hook.handler(context or {})
                duration = time.time() - t0
                results.append(HookResult(
                    hook_name=hook.name, event=event.value,
                    success=True, duration=duration,
                    output=str(output)[:200] if output else None,
                ))
            except Exception as e:
                duration = time.time() - t0
                logger.error(f"Hook '{hook.name}' failed for {event.value}: {e}")
                results.append(HookResult(
                    hook_name=hook.name, event=event.value,
                    success=False, duration=duration, error=str(e),
                ))
                if raise_on_error:
                    raise
            finally:
                self._current_hook = None

            # Auto-remove once hooks
            if hook.once:
                self._hooks[event] = [h for h in self._hooks[event] if h is not hook]

        return results

    def unregister(self, event: HookEvent, name: str):
        if event in self._hooks:
            self._hooks[event] = [
                h for h in self._hooks[event] if h.name != name
            ]

    def clear(self, event: Optional[HookEvent] = None):
        if event:
            self._hooks[event] = []
        else:
            self._hooks.clear()

    @property
    def status(self) -> dict:
        return {
            event.value: len(hooks)
            for event, hooks in self._hooks.items()
        }


# Global hook manager
hooks = HookManager()
