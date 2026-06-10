"""UI Component Library"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

class ComponentType(str, Enum):
    CONTAINER = "container"
    TEXT = "text"
    IMAGE = "image"
    BUTTON = "button"
    INPUT = "input"
    PROGRESS = "progress"
    CHART = "chart"
    LIST = "list"
    FORM = "form"
    TABLE = "table"
    MODAL = "modal"
    STATUS_BAR = "status_bar"
    PANEL = "panel"
    TAB_VIEW = "tab_view"
    TREE = "tree"

@dataclass
class Style:
    width: str = ""
    height: str = ""
    color: str = ""
    bg_color: str = ""
    font_size: str = ""
    font_weight: str = ""
    padding: str = ""
    margin: str = ""
    border: str = ""
    border_radius: str = ""
    display: str = ""
    flex: str = ""
    opacity: float = 1.0

@dataclass
class Component:
    id: str = ""
    type: ComponentType = ComponentType.CONTAINER
    props: Dict = field(default_factory=dict)
    style: Style = field(default_factory=Style)
    children: List["Component"] = field(default_factory=list)
    events: Dict[str, str] = field(default_factory=dict)

class ComponentFactory:
    @staticmethod
    def text(content: str, style: Style = None) -> Component:
        return Component(id=f"txt_{id(content)}", type=ComponentType.TEXT,
                        props={"content": content}, style=style or Style())
    @staticmethod
    def button(label: str, action: str = "", style: Style = None) -> Component:
        return Component(id=f"btn_{id(label)}", type=ComponentType.BUTTON,
                        props={"label": label, "action": action}, style=style or Style(),
                        events={"click": action})
    @staticmethod
    def progress(value: float, label: str = "") -> Component:
        return Component(id=f"prog_{int(id(label))}", type=ComponentType.PROGRESS,
                        props={"value": min(1.0, max(0.0, value)), "label": label})
    @staticmethod
    def panel(title: str, children: List[Component] = None) -> Component:
        return Component(id=f"pan_{id(title)}", type=ComponentType.PANEL,
                        props={"title": title}, children=children or [])
    @staticmethod
    def status_bar(items: Dict[str, Any]) -> Component:
        return Component(id="status_bar", type=ComponentType.STATUS_BAR, props={"items": items})
    @staticmethod
    def chart(data: List[Dict], chart_type: str = "bar") -> Component:
        return Component(id=f"chart_{int(time.time())}", type=ComponentType.CHART,
                        props={"data": data, "chart_type": chart_type})
