"""Web Renderer — Web渲染器"""
from __future__ import annotations
import json, logging
from typing import Any, Dict, List, Optional
from laap.engine.render.components import Component, ComponentType, Style
from laap.engine.render.theme import ThemeManager

logger = logging.getLogger("engine.render.web")

class WebRenderer:
    def __init__(self, theme_name: str = "golden_dragon"):
        self.theme = ThemeManager.get(theme_name)
    def render_to_html(self, component: Component) -> str:
        html = self._render_html(component)
        css = self.theme.as_css_variables()
        return f"""<!DOCTYPE html>
<html><head><style>{css}</style></head><body>{html}</body></html>"""
    def _render_html(self, comp: Component) -> str:
        style = self._style_to_inline(comp.style)
        if comp.type == "container":
            children = "".join(self._render_html(c) for c in comp.children)
            return f'<div id="{comp.id}" style="{style}">{children}</div>'
        elif comp.type == "text":
            return f'<span id="{comp.id}" style="{style}">{comp.props.get("content","")}</span>'
        elif comp.type == "button":
            return f'<button id="{comp.id}" style="{style}" onclick="{comp.events.get("click","")}">{comp.props.get("label","")}</button>'
        elif comp.type == "progress":
            val = comp.props.get("value", 0) * 100
            return f'<div id="{comp.id}" style="{style}"><progress value="{val}" max="100"></progress></div>'
        return f'<div id="{comp.id}" style="{style}"></div>'
    def _style_to_inline(self, style: Style) -> str:
        parts = []
        if style.color: parts.append(f"color:{style.color}")
        if style.bg_color: parts.append(f"background:{style.bg_color}")
        if style.font_size: parts.append(f"font-size:{style.font_size}")
        if style.padding: parts.append(f"padding:{style.padding}")
        if style.margin: parts.append(f"margin:{style.margin}")
        if style.border_radius: parts.append(f"border-radius:{style.border_radius}")
        if style.opacity < 1: parts.append(f"opacity:{style.opacity}")
        return ";".join(parts)
    def render_to_json(self, component: Component) -> str:
        return json.dumps(self._component_to_dict(component), indent=2)
    def _component_to_dict(self, comp: Component) -> dict:
        return {"id": comp.id, "type": comp.type.value, "props": comp.props,
                "children": [self._component_to_dict(c) for c in comp.children]}
