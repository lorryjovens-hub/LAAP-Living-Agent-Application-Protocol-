"""TUI Renderer — 终端渲染器"""
from __future__ import annotations
import time, logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from laap.engine.render.components import Component, ComponentType, ComponentFactory, Style
from laap.engine.render.theme import Theme, ThemeManager

logger = logging.getLogger("engine.render.tui")

class TUIRenderer:
    def __init__(self, theme_name: str = "golden_dragon"):
        self.theme = ThemeManager.get(theme_name)
        self._buffer: List[str] = []
    def render(self, component: Component, indent: int = 0) -> str:
        self._buffer = []
        self._render_component(component, indent)
        return "\n".join(self._buffer)
    def _render_component(self, comp: Component, indent: int):
        prefix = "  " * indent
        if comp.type == ComponentType.CONTAINER:
            self._buffer.append(f"{prefix}[Container {comp.id}]")
            for child in comp.children:
                self._render_component(child, indent + 1)
        elif comp.type == ComponentType.TEXT:
            content = comp.props.get("content", "")
            self._buffer.append(f"{prefix}{content}")
        elif comp.type == ComponentType.BUTTON:
            label = comp.props.get("label", "")
            self._buffer.append(f"{prefix}[{label}]")
        elif comp.type == ComponentType.PROGRESS:
            value = comp.props.get("value", 0)
            bar_len = 20
            filled = int(value * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            self._buffer.append(f"{prefix}[{bar}] {value:.0%}")
        elif comp.type == ComponentType.PANEL:
            title = comp.props.get("title", "")
            self._buffer.append(f"{prefix}┌─ {title} " + "─" * 40)
            for child in comp.children:
                self._render_component(child, indent + 1)
            self._buffer.append(f"{prefix}└" + "─" * 50)
        elif comp.type == ComponentType.STATUS_BAR:
            items = comp.props.get("items", {})
            parts = [f"{k}: {v}" for k, v in items.items()]
            self._buffer.append(f"{prefix}" + " | ".join(parts))
        elif comp.type == ComponentType.CHART:
            self._buffer.append(f"{prefix}[Chart: {comp.props.get('chart_type', 'bar')}]")
    def render_to_terminal(self, component: Component):
        output = self.render(component)
        print(output)
        return output
