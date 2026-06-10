"""
LAAP-UI v1.0 — 渲染协议

数字生命体前端渲染协议，定义组件树、布局、主题、事件绑定和差分更新机制。

协议标准: https://laap.ai/protocol/ui/v1
"""

from __future__ import annotations
import enum
import json
import logging
import math
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union, Set, Callable

logger = logging.getLogger("laap.protocol.ui")

class LayoutType(str, Enum):
    FLEX = "flex"
    GRID = "grid"
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    FIXED = "fixed"
    STICKY = "sticky"
    FLOW = "flow"
    COLUMN = "column"
    ROW = "row"
    WRAP = "wrap"
    STACK = "stack"
    SCROLL = "scroll"
    RESPONSIVE = "responsive"
    MASONRY = "masonry"
    TABS = "tabs"
    SPLITTER = "splitter"
    DOCK = "dock"
    OVERLAY = "overlay"
    MODAL = "modal"
    CAROUSEL = "carousel"
    ACCORDION = "accordion"

class ComponentType(str, Enum):
    ROOT = "root"
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
    SLIDER = "slider"
    ICON = "icon"
    LINK = "link"
    VIDEO = "video"
    AUDIO = "audio"
    CARD = "card"
    BADGE = "badge"
    TOOLTIP = "tooltip"
    DROPDOWN = "dropdown"
    NAVIGATION = "navigation"
    FOOTER = "footer"
    HEADER = "header"
    SIDEBAR = "sidebar"
    MODAL_WINDOW = "modal_window"
    TOAST = "toast"
    SPINNER = "spinner"
    AVATAR = "avatar"
    DIVIDER = "divider"
    SPACE = "space"
    IFRAME = "iframe"
    CANVAS = "canvas"
    SVG = "svg"
    HTML = "html"

@dataclass
class TextStyle:
    font_family: Optional[str] = None
    font_size: Optional[str] = None
    font_weight: Optional[str] = None
    font_style: Optional[str] = None
    font_variant: Optional[str] = None
    line_height: Optional[str] = None
    letter_spacing: Optional[str] = None
    word_spacing: Optional[str] = None
    text_align: Optional[str] = None
    text_decoration: Optional[str] = None
    text_transform: Optional[str] = None
    text_indent: Optional[str] = None
    text_shadow: Optional[str] = None
    color: Optional[str] = None
    white_space: Optional[str] = None
    word_break: Optional[str] = None
    overflow_wrap: Optional[str] = None
    vertical_align: Optional[str] = None
    direction: Optional[str] = None
    writing_mode: Optional[str] = None

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class FlexStyle:
    flex_direction: Optional[str] = None
    flex_wrap: Optional[str] = None
    justify_content: Optional[str] = None
    align_items: Optional[str] = None
    align_content: Optional[str] = None
    align_self: Optional[str] = None
    flex_grow: Optional[float] = None
    flex_shrink: Optional[float] = None
    flex_basis: Optional[str] = None
    gap: Optional[str] = None
    row_gap: Optional[str] = None
    column_gap: Optional[str] = None
    order: Optional[int] = None

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class GridStyle:
    grid_template_columns: Optional[str] = None
    grid_template_rows: Optional[str] = None
    grid_template_areas: Optional[str] = None
    grid_auto_columns: Optional[str] = None
    grid_auto_rows: Optional[str] = None
    grid_auto_flow: Optional[str] = None
    grid_column: Optional[str] = None
    grid_row: Optional[str] = None
    grid_column_start: Optional[int] = None
    grid_column_end: Optional[int] = None
    grid_row_start: Optional[int] = None
    grid_row_end: Optional[int] = None
    grid_area: Optional[str] = None
    gap: Optional[str] = None
    row_gap: Optional[str] = None
    column_gap: Optional[str] = None
    justify_items: Optional[str] = None
    align_items: Optional[str] = None
    justify_content: Optional[str] = None
    align_content: Optional[str] = None

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class TextProperties:
    content: str = ""
    html: Optional[str] = None
    max_lines: Optional[int] = None
    selectable: bool = True
    editable: bool = False
    style: Optional[TextStyle] = None

@dataclass
class ImageProperties:
    src: str = ""
    alt: str = ""
    object_fit: str = "cover"
    object_position: str = "center"
    lazy_load: bool = True
    placeholder: Optional[str] = None
    fallback: Optional[str] = None
    loading_effect: str = "blur"

@dataclass
class ButtonProperties:
    text: str = ""
    variant: str = "primary"
    size: str = "md"
    disabled: bool = False
    loading: bool = False
    icon: Optional[str] = None
    icon_position: str = "left"
    full_width: bool = False
    href: Optional[str] = None
    type: str = "button"
    aria_label: Optional[str] = None

@dataclass
class InputProperties:
    name: str = ""
    value: str = ""
    placeholder: str = ""
    label: Optional[str] = None
    type: str = "text"
    disabled: bool = False
    readonly: bool = False
    required: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    pattern: Optional[str] = None
    autocomplete: Optional[str] = None
    autofocus: bool = False
    error_message: Optional[str] = None
    help_text: Optional[str] = None
    icon: Optional[str] = None
    clearable: bool = False
    size: str = "md"

@dataclass
class ProgressProperties:
    value: float = 0.0
    max_value: float = 100.0
    variant: str = "determinate"
    color: Optional[str] = None
    track_color: Optional[str] = None
    thickness: int = 4
    show_label: bool = True
    label_format: str = "{percent}%"
    animated: bool = False
    striped: bool = False

@dataclass
class ChartProperties:
    chart_type: str = "bar"
    labels: List[str] = field(default_factory=list)
    datasets: List[Dict[str, Any]] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)
    width: str = "100%"
    height: str = "400px"
    responsive: bool = True
    animate: bool = True
    legend: bool = True
    tooltip: bool = True
    grid_lines: bool = True
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None

@dataclass
class ListProperties:
    items: List[Any] = field(default_factory=list)
    item_template: Optional[str] = None
    list_type: str = "unordered"
    dense: bool = False
    dividers: bool = True
    selectable: bool = False
    multiple: bool = False
    selected_values: List[Any] = field(default_factory=list)
    virtual_scroll: bool = False
    item_height: Optional[int] = None
    max_height: Optional[str] = None
    empty_text: str = "暂无数据"

@dataclass
class FormProperties:
    name: str = ""
    method: str = "post"
    action: Optional[str] = None
    validate: bool = True
    validation_mode: str = "submit"
    autocomplete: Optional[str] = None
    novalidate: bool = False
    enc_type: str = "application/x-www-form-urlencoded"
    fields: Dict[str, Any] = field(default_factory=dict)
    initial_values: Dict[str, Any] = field(default_factory=dict)
    submit_text: str = "提交"
    reset_text: str = "重置"

@dataclass
class TableProperties:
    columns: List[Dict[str, Any]] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    bordered: bool = True
    striped: bool = False
    hoverable: bool = True
    compact: bool = False
    sticky_header: bool = False
    sticky_columns: Optional[List[int]] = None
    sortable: bool = False
    filterable: bool = False
    pageable: bool = False
    page_size: int = 20
    current_page: int = 1
    total: Optional[int] = None
    selection: Optional[str] = None
    selected_rows: List[Any] = field(default_factory=list)
    expandable: bool = False
    tree: bool = False
    max_height: Optional[str] = None

@dataclass
class SliderProperties:
    name: str = ""
    value: Union[float, Tuple[float, float]] = 0.0
    min_value: float = 0.0
    max_value: float = 100.0
    step: float = 1.0
    range_mode: bool = False
    vertical: bool = False
    disabled: bool = False
    show_value: bool = True
    value_format: str = "{value}"
    marks: Optional[Dict[float, str]] = None
    track_color: Optional[str] = None
    thumb_color: Optional[str] = None
    size: str = "md"

class EventType(str, Enum):
    CLICK = "click"
    DBLCLICK = "dblclick"
    MOUSE_DOWN = "mousedown"
    MOUSE_UP = "mouseup"
    MOUSE_ENTER = "mouseenter"
    MOUSE_LEAVE = "mouseleave"
    MOUSE_MOVE = "mousemove"
    MOUSE_OVER = "mouseover"
    MOUSE_OUT = "mouseout"
    CONTEXT_MENU = "contextmenu"
    WHEEL = "wheel"
    FOCUS = "focus"
    BLUR = "blur"
    KEY_DOWN = "keydown"
    KEY_UP = "keyup"
    KEY_PRESS = "keypress"
    CHANGE = "change"
    INPUT_EVENT = "input"
    SUBMIT = "submit"
    RESET = "reset"
    SCROLL = "scroll"
    RESIZE = "resize"
    TOUCH_START = "touchstart"
    TOUCH_MOVE = "touchmove"
    TOUCH_END = "touchend"
    TOUCH_CANCEL = "touchcancel"
    DRAG_START = "dragstart"
    DRAG = "drag"
    DRAG_END = "dragend"
    DRAG_ENTER = "dragenter"
    DRAG_OVER = "dragover"
    DRAG_LEAVE = "dragleave"
    DROP = "drop"
    HOVER = "hover"
    LOAD = "load"
    ERROR = "error"
    ANIMATION_START = "animationstart"
    ANIMATION_END = "animationend"
    ANIMATION_ITERATION = "animationiteration"
    TRANSITION_START = "transitionstart"
    TRANSITION_END = "transitionend"
    CUSTOM = "custom"

@dataclass
class EventBinding:
    event_type: EventType
    handler_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    debounce: Optional[int] = None
    throttle: Optional[int] = None
    prevent_default: bool = True
    stop_propagation: bool = True
    once: bool = False
    condition: Optional[str] = None
    priority: int = 0

    def to_dict(self):
        return {
            "event_type": self.event_type.value,
            "handler_id": self.handler_id,
            "payload": self.payload,
            "debounce": self.debounce,
            "throttle": self.throttle,
            "prevent_default": self.prevent_default,
            "stop_propagation": self.stop_propagation,
            "once": self.once,
            "condition": self.condition,
            "priority": self.priority,
        }

    @staticmethod
    def from_dict(data):
        return EventBinding(
            event_type=EventType(data.get("event_type", "click")),
            handler_id=data.get("handler_id", ""),
            payload=data.get("payload", {}),
            debounce=data.get("debounce"),
            throttle=data.get("throttle"),
            prevent_default=data.get("prevent_default", True),
            stop_propagation=data.get("stop_propagation", True),
            once=data.get("once", False),
            condition=data.get("condition"),
            priority=data.get("priority", 0),
        )

@dataclass
class ThemePalette:
    primary: str = "#1976D2"
    secondary: str = "#9C27B0"
    accent: str = "#FF4081"
    success: str = "#4CAF50"
    warning: str = "#FF9800"
    danger: str = "#F44336"
    info: str = "#2196F3"
    light: str = "#F5F5F5"
    dark: str = "#212121"
    background: str = "#FFFFFF"
    surface: str = "#FAFAFA"
    text_primary: str = "#212121"
    text_secondary: str = "#757575"
    text_disabled: str = "#BDBDBD"
    border: str = "#E0E0E0"
    divider: str = "#EEEEEE"
    overlay: str = "rgba(0,0,0,0.5)"

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        return ThemePalette(**{k: v for k, v in data.items() if k in ThemePalette.__dataclass_fields__})

    def dark_mode(self):
        return ThemePalette(
            primary=self.primary, secondary=self.secondary,
            accent=self.accent, success=self.success,
            warning=self.warning, danger=self.danger, info=self.info,
            light="#424242", dark="#E0E0E0",
            background="#121212", surface="#1E1E1E",
            text_primary="#E0E0E0", text_secondary="#9E9E9E",
            text_disabled="#616161", border="#333333",
            divider="#2C2C2C", overlay="rgba(0,0,0,0.7)",
        )

@dataclass
class TypographyConfig:
    font_family: str = "'Roboto', 'Helvetica', 'Arial', sans-serif"
    font_family_mono: str = "'Roboto Mono', 'Fira Code', monospace"
    font_size_xs: str = "10px"
    font_size_sm: str = "12px"
    font_size_md: str = "14px"
    font_size_lg: str = "16px"
    font_size_xl: str = "20px"
    font_size_xxl: str = "24px"
    font_size_h1: str = "32px"
    font_size_h2: str = "28px"
    font_size_h3: str = "24px"
    font_size_h4: str = "20px"
    font_size_h5: str = "16px"
    font_size_h6: str = "14px"
    line_height: float = 1.5
    letter_spacing_normal: str = "0.01em"
    letter_spacing_wide: str = "0.05em"

@dataclass
class SpacingConfig:
    unit: int = 8
    xs: str = "4px"
    sm: str = "8px"
    md: str = "16px"
    lg: str = "24px"
    xl: str = "32px"
    xxl: str = "48px"
    section: str = "64px"

@dataclass
class BorderRadiusConfig:
    none: str = "0"
    xs: str = "2px"
    sm: str = "4px"
    md: str = "8px"
    lg: str = "12px"
    xl: str = "16px"
    full: str = "9999px"

@dataclass
class ShadowConfig:
    none: str = "none"
    xs: str = "0 1px 2px rgba(0,0,0,0.05)"
    sm: str = "0 1px 3px rgba(0,0,0,0.1)"
    md: str = "0 4px 6px rgba(0,0,0,0.1)"
    lg: str = "0 10px 15px rgba(0,0,0,0.1)"
    xl: str = "0 20px 25px rgba(0,0,0,0.1)"
    xxl: str = "0 25px 50px rgba(0,0,0,0.25)"

@dataclass
class BreakpointConfig:
    xs: int = 0
    sm: int = 600
    md: int = 960
    lg: int = 1280
    xl: int = 1920
    xxl: int = 2560

@dataclass
class AnimationConfig:
    duration_fast: str = "150ms"
    duration_normal: str = "300ms"
    duration_slow: str = "500ms"
    easing_ease_in_out: str = "cubic-bezier(0.4, 0, 0.2, 1)"
    easing_ease_out: str = "cubic-bezier(0.0, 0, 0.2, 1)"
    easing_ease_in: str = "cubic-bezier(0.4, 0, 1, 1)"
    easing_sharp: str = "cubic-bezier(0.4, 0, 0.6, 1)"
    transition_default: str = "all 300ms cubic-bezier(0.4, 0, 0.2, 1)"

@dataclass
class ThemeConfig:
    name: str = "default"
    version: str = "1.0"
    dark: bool = False
    palette: ThemePalette = field(default_factory=ThemePalette)
    typography: TypographyConfig = field(default_factory=TypographyConfig)
    spacing: SpacingConfig = field(default_factory=SpacingConfig)
    border_radius: BorderRadiusConfig = field(default_factory=BorderRadiusConfig)
    shadows: ShadowConfig = field(default_factory=ShadowConfig)
    breakpoints: BreakpointConfig = field(default_factory=BreakpointConfig)
    animation: AnimationConfig = field(default_factory=AnimationConfig)
    custom_vars: Dict[str, str] = field(default_factory=dict)

    def to_dict(self):
        return {
            "name": self.name, "version": self.version, "dark": self.dark,
            "palette": self.palette.to_dict(),
            "typography": asdict(self.typography),
            "spacing": asdict(self.spacing),
            "border_radius": asdict(self.border_radius),
            "shadows": asdict(self.shadows),
            "breakpoints": asdict(self.breakpoints),
            "animation": asdict(self.animation),
            "custom_vars": self.custom_vars,
        }

    def as_css_variables(self, prefix: str = "laap"):
        vars = {}
        for k, v in asdict(self.palette).items():
            vars[f"--{prefix}-palette-{k}"] = v
        for k, v in asdict(self.typography).items():
            vars[f"--{prefix}-typography-{k}"] = v
        for k, v in asdict(self.spacing).items():
            vars[f"--{prefix}-spacing-{k}"] = v
        for k, v in asdict(self.border_radius).items():
            vars[f"--{prefix}-radius-{k}"] = v
        for k, v in self.custom_vars.items():
            vars[f"--{prefix}-{k}"] = v
        return vars

    def dark_mode(self):
        return ThemeConfig(
            name=f"{self.name}-dark", version=self.version, dark=True,
            palette=self.palette.dark_mode(),
            typography=self.typography, spacing=self.spacing,
            border_radius=self.border_radius, shadows=self.shadows,
            breakpoints=self.breakpoints, animation=self.animation,
            custom_vars=self.custom_vars,
        )

class ThemeDefinition:
    def __init__(self, config: Optional[ThemeConfig] = None):
        self.config = config or ThemeConfig()
        self._compiled_css: Dict[str, str] = {}

    def compile(self):
        self._compiled_css = self.config.as_css_variables()
        return self._compiled_css

    def to_json(self):
        return json.dumps(self.config.to_dict(), indent=2, ensure_ascii=False)

    @staticmethod
    def from_json(data: str):
        return ThemeDefinition(ThemeConfig(**json.loads(data)))

@dataclass
@dataclass
class StyleDefinition:
    """样式定义"""
    width: str = ""
    height: str = ""
    display: str = ""
    flex_direction: str = ""
    justify_content: str = ""
    align_items: str = ""
    padding: str = ""
    margin: str = ""
    border: str = ""
    border_radius: str = ""
    background_color: str = ""
    color: str = ""
    font_size: str = ""
    font_weight: str = ""
    text_align: str = ""
    opacity: float = 1.0
    overflow: str = ""
    position: str = ""
    top: str = ""
    left: str = ""
    right: str = ""
    bottom: str = ""
    z_index: int = 1
    min_width: str = ""
    min_height: str = ""
    max_width: str = ""
    max_height: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "StyleDefinition":
        return cls(**{k: data.get(k, "") for k in cls.__dataclass_fields__})

@dataclass
class Component:
    """LAAP-UI基础组件"""
    id: str = ""
    component_type: ComponentType = ComponentType.CONTAINER
    layout_type: LayoutType = LayoutType.FLEX
    style: Optional[StyleDefinition] = None
    flex_style: Optional[FlexStyle] = None
    grid_style: Optional[GridStyle] = None
    text_style: Optional[TextStyle] = None
    text_content: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    events: List[EventBinding] = field(default_factory=list)
    children: List[Component] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    data_attributes: Dict[str, str] = field(default_factory=dict)
    visible: bool = True
    disabled: bool = False
    loading: bool = False
    tooltip: Optional[str] = None
    aria_label: Optional[str] = None
    test_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"comp_{uuid.uuid4().hex[:8]}"

    def to_dict(self):
        return {
            "id": self.id,
            "component_type": self.component_type.value,
            "layout_type": self.layout_type.value,
            "style": self.style.to_dict() if self.style else None,
            "flex_style": self.flex_style.to_dict() if self.flex_style else None,
            "grid_style": self.grid_style.to_dict() if self.grid_style else None,
            "text_style": self.text_style.to_dict() if self.text_style else None,
            "text_content": self.text_content,
            "properties": self.properties,
            "events": [e.to_dict() for e in self.events],
            "children": [c.to_dict() for c in self.children],
            "classes": self.classes,
            "attributes": self.attributes,
            "data_attributes": self.data_attributes,
            "visible": self.visible,
            "disabled": self.disabled,
            "loading": self.loading,
            "tooltip": self.tooltip,
            "aria_label": self.aria_label,
            "test_id": self.test_id,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data):
        comp = Component(
            id=data.get("id", ""),
            component_type=ComponentType(data.get("component_type", "container")),
            layout_type=LayoutType(data.get("layout_type", "flex")),
            style=StyleDefinition.from_dict(data["style"]) if data.get("style") else None,
            flex_style=FlexStyle(**data["flex_style"]) if data.get("flex_style") else None,
            grid_style=GridStyle(**data["grid_style"]) if data.get("grid_style") else None,
            text_style=TextStyle(**data["text_style"]) if data.get("text_style") else None,
            text_content=data.get("text_content"),
            properties=data.get("properties"),
            events=[EventBinding.from_dict(e) for e in data.get("events", [])],
            classes=data.get("classes", []),
            attributes=data.get("attributes", {}),
            data_attributes=data.get("data_attributes", {}),
            visible=data.get("visible", True),
            disabled=data.get("disabled", False),
            loading=data.get("loading", False),
            tooltip=data.get("tooltip"),
            aria_label=data.get("aria_label"),
            test_id=data.get("test_id"),
            metadata=data.get("metadata", {}),
        )
        for child_data in data.get("children", []):
            comp.children.append(Component.from_dict(child_data))
        return comp

    def find_by_id(self, comp_id: str):
        if self.id == comp_id:
            return self
        for child in self.children:
            result = child.find_by_id(comp_id)
            if result:
                return result
        return None

    def find_all_by_type(self, comp_type: ComponentType):
        results = []
        if self.component_type == comp_type:
            results.append(self)
        for child in self.children:
            results.extend(child.find_all_by_type(comp_type))
        return results

    def add_child(self, child):
        self.children.append(child)
        return self

    def remove_child(self, child_id: str):
        for i, child in enumerate(self.children):
            if child.id == child_id:
                self.children.pop(i)
                return True
            if child.remove_child(child_id):
                return True
        return False

    def add_event(self, event):
        self.events.append(event)
        return self

    def set_style(self, key: str, value):
        if not self.style:
            self.style = StyleDefinition()
        if hasattr(self.style, key):
            setattr(self.style, key, value)
        return self

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def count_nodes(self):
        count = 1
        for child in self.children:
            count += child.count_nodes()
        return count

    def flatten(self):
        nodes = [self]
        for child in self.children:
            nodes.extend(child.flatten())
        return nodes

class LayoutTree:
    def __init__(self, root: Optional[Component] = None, metadata: Optional[Dict[str, Any]] = None):
        self.root = root or Component(
            id="root", component_type=ComponentType.ROOT,
            layout_type=LayoutType.FLEX,
            style=StyleDefinition(width="100%", height="100%", display="flex"),
        )
        self.metadata = metadata or {
            "version": "1.0", "created_at": time.time(), "updated_at": time.time(),
        }

    def to_dict(self):
        return {"root": self.root.to_dict(), "metadata": self.metadata}

    @staticmethod
    def from_dict(data):
        return LayoutTree(
            root=Component.from_dict(data["root"]),
            metadata=data.get("metadata", {}),
        )

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @staticmethod
    def from_json(data: str):
        return LayoutTree.from_dict(json.loads(data))

    def find_by_id(self, comp_id: str):
        return self.root.find_by_id(comp_id) if self.root else None

    def flatten(self):
        return self.root.flatten() if self.root else []

    def count_nodes(self):
        return self.root.count_nodes() if self.root else 0

    def get_max_depth(self):
        def _depth(node, d=0):
            if not node.children:
                return d
            return max(_depth(c, d + 1) for c in node.children)
        return _depth(self.root) if self.root else 0

    def breadth_first(self):
        if not self.root:
            return []
        nodes, queue = [], [self.root]
        while queue:
            node = queue.pop(0)
            nodes.append(node)
            queue.extend(node.children)
        return nodes

    def depth_first(self):
        return self.flatten()

class RenderOp(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    REPLACE = "replace"
    INSERT_BEFORE = "insert_before"
    INSERT_AFTER = "insert_after"
    APPEND_CHILD = "append_child"
    REPLACE_CHILDREN = "replace_children"
    UPDATE_STYLE = "update_style"
    UPDATE_TEXT = "update_text"
    UPDATE_PROPS = "update_props"
    ADD_EVENT = "add_event"
    REMOVE_EVENT = "remove_event"
    SET_ATTR = "set_attr"
    REMOVE_ATTR = "remove_attr"
    SHOW = "show"
    HIDE = "hide"
    ENABLE = "enable"
    DISABLE = "disable"
    SET_CLASS = "set_class"
    REMOVE_CLASS = "remove_class"
    SCROLL_TO = "scroll_to"
    FOCUS = "focus"
    ANIMATE = "animate"
    CUSTOM = "custom"

@dataclass
class RenderCommand:
    op: RenderOp
    target_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    sibling_id: Optional[str] = None
    index: Optional[int] = None
    component: Optional[Component] = None
    priority: int = 0
    async_exec: bool = False
    batch_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "op": self.op.value, "target_id": self.target_id,
            "payload": self.payload, "parent_id": self.parent_id,
            "sibling_id": self.sibling_id, "index": self.index,
            "component": self.component.to_dict() if self.component else None,
            "priority": self.priority, "async_exec": self.async_exec,
            "batch_key": self.batch_key, "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data):
        return RenderCommand(
            op=RenderOp(data["op"]), target_id=data["target_id"],
            payload=data.get("payload", {}),
            parent_id=data.get("parent_id"), sibling_id=data.get("sibling_id"),
            index=data.get("index"),
            component=Component.from_dict(data["component"]) if data.get("component") else None,
            priority=data.get("priority", 0), async_exec=data.get("async_exec", False),
            batch_key=data.get("batch_key"), metadata=data.get("metadata", {}),
        )

class DiffCalculator:
    def __init__(self):
        self._stats = {"creates": 0, "updates": 0, "deletes": 0, "moves": 0}

    def compute(self, old_tree, new_tree):
        commands = []
        self._stats = {"creates": 0, "updates": 0, "deletes": 0, "moves": 0}
        if old_tree is None:
            commands.extend(self._compute_initial(new_tree))
        else:
            commands.extend(self._diff_nodes(old_tree.root, new_tree.root, None))
        return commands

    def _compute_initial(self, tree):
        commands = []
        self._build_create_commands(tree.root, None, commands)
        return commands

    def _build_create_commands(self, node, parent_id, commands):
        cmd = RenderCommand(op=RenderOp.CREATE, target_id=node.id, parent_id=parent_id, component=node)
        commands.append(cmd)
        self._stats["creates"] += 1
        for child in node.children:
            self._build_create_commands(child, node.id, commands)

    def _diff_nodes(self, old, new, parent_id):
        commands = []
        if old is None:
            self._build_create_commands(new, parent_id, commands)
            return commands
        if old.component_type != new.component_type:
            self._build_create_commands(new, parent_id, commands)
            commands.append(RenderCommand(op=RenderOp.DELETE, target_id=old.id))
            self._stats["deletes"] += 1
            self._stats["creates"] += 1
            return commands
        props_changed = self._props_changed(old, new)
        if props_changed:
            commands.append(RenderCommand(op=RenderOp.UPDATE, target_id=new.id, payload={"changes": props_changed}))
            self._stats["updates"] += 1
        style_diff = self._style_diff(old.style, new.style)
        if style_diff:
            commands.append(RenderCommand(op=RenderOp.UPDATE_STYLE, target_id=new.id, payload={"style": style_diff}))
        if old.text_content != new.text_content:
            commands.append(RenderCommand(op=RenderOp.UPDATE_TEXT, target_id=new.id, payload={"text": new.text_content}))
        self._diff_children(old.children, new.children, new.id, commands)
        return commands

    def _props_changed(self, old, new):
        changes = {}
        for attr in ["visible", "disabled", "loading", "tooltip", "aria_label"]:
            if getattr(old, attr) != getattr(new, attr):
                changes[attr] = getattr(new, attr)
        if old.classes != new.classes:
            changes["classes"] = new.classes
        if old.attributes != new.attributes:
            changes["attributes"] = new.attributes
        if old.data_attributes != new.data_attributes:
            changes["data_attributes"] = new.data_attributes
        if old.properties != new.properties:
            changes["properties"] = new.properties
        return changes

    def _style_diff(self, old, new):
        if old is None and new is None:
            return {}
        if old is None:
            return new.to_dict() if new else {}
        if new is None:
            return {"_remove": True}
        changed = {}
        old_dict = old.to_dict()
        new_dict = new.to_dict()
        for key in set(old_dict.keys()) | set(new_dict.keys()):
            if old_dict.get(key) != new_dict.get(key):
                changed[key] = new_dict.get(key)
        return changed

    def _diff_children(self, old_children, new_children, parent_id, commands):
        old_map = {c.id: c for c in old_children}
        new_ids = {c.id for c in new_children}
        old_ids = set(old_map.keys())
        for child in new_children:
            if child.id in old_map:
                commands.extend(self._diff_nodes(old_map[child.id], child, parent_id))
            else:
                self._build_create_commands(child, parent_id, commands)
        for child_id in old_ids - new_ids:
            commands.append(RenderCommand(op=RenderOp.DELETE, target_id=child_id, parent_id=parent_id))
            self._stats["deletes"] += 1
        if len(old_children) != len(new_children):
            commands.append(RenderCommand(
                op=RenderOp.REPLACE_CHILDREN, target_id=parent_id,
                payload={"order": [c.id for c in new_children]},
            ))

    def get_stats(self):
        return dict(self._stats)

class ComponentFactory:
    @staticmethod
    def create_root(layout=LayoutType.FLEX):
        return Component(id="root", component_type=ComponentType.ROOT, layout_type=layout,
                         style=StyleDefinition(width="100%", height="100%"))

    @staticmethod
    def create_container(layout=LayoutType.FLEX, style=None, children=None):
        return Component(component_type=ComponentType.CONTAINER, layout_type=layout,
                         style=style, children=children or [])

    @staticmethod
    def create_text(content, style=None, text_align=None, color=None):
        ts = style or TextStyle()
        if text_align: ts.text_align = text_align
        if color: ts.color = color
        return Component(component_type=ComponentType.TEXT, text_content=content, text_style=ts)

    @staticmethod
    def create_image(src, alt="", **kwargs):
        props = ImageProperties(src=src, alt=alt)
        for k, v in kwargs.items():
            if hasattr(props, k): setattr(props, k, v)
        return Component(component_type=ComponentType.IMAGE, properties=asdict(props))

    @staticmethod
    def create_button(text, variant="primary", onClick=None, **kwargs):
        props = ButtonProperties(text=text, variant=variant)
        for k, v in kwargs.items():
            if hasattr(props, k): setattr(props, k, v)
        comp = Component(component_type=ComponentType.BUTTON, properties=asdict(props))
        if onClick:
            comp.add_event(EventBinding(event_type=EventType.CLICK, handler_id=onClick))
        return comp

    @staticmethod
    def create_input(name, **kwargs):
        props = InputProperties(name=name)
        for k, v in kwargs.items():
            if hasattr(props, k): setattr(props, k, v)
        return Component(component_type=ComponentType.INPUT, properties=asdict(props))

    @staticmethod
    def create_progress(value=0, max_value=100, **kwargs):
        props = ProgressProperties(value=value, max_value=max_value)
        for k, v in kwargs.items():
            if hasattr(props, k): setattr(props, k, v)
        return Component(component_type=ComponentType.PROGRESS, properties=asdict(props))

    @staticmethod
    def create_chart(chart_type="bar", labels=None, datasets=None, **kwargs):
        props = ChartProperties(chart_type=chart_type, labels=labels or [], datasets=datasets or [])
        for k, v in kwargs.items():
            if hasattr(props, k): setattr(props, k, v)
        return Component(component_type=ComponentType.CHART, properties=asdict(props))

    @staticmethod
    def create_list(items=None, **kwargs):
        props = ListProperties(items=items or [])
        for k, v in kwargs.items():
            if hasattr(props, k): setattr(props, k, v)
        return Component(component_type=ComponentType.LIST, properties=asdict(props))

    @staticmethod
    def create_form(name, fields=None, **kwargs):
        props = FormProperties(name=name, fields=fields or {})
        for k, v in kwargs.items():
            if hasattr(props, k): setattr(props, k, v)
        return Component(component_type=ComponentType.FORM, properties=asdict(props))

    @staticmethod
    def create_table(columns=None, rows=None, **kwargs):
        props = TableProperties(columns=columns or [], rows=rows or [])
        for k, v in kwargs.items():
            if hasattr(props, k): setattr(props, k, v)
        return Component(component_type=ComponentType.TABLE, properties=asdict(props))

    @staticmethod
    def create_slider(name, **kwargs):
        props = SliderProperties(name=name)
        for k, v in kwargs.items():
            if hasattr(props, k): setattr(props, k, v)
        return Component(component_type=ComponentType.SLIDER, properties=asdict(props))

    @staticmethod
    def create_card(title, content=None, style=None):
        children = []
        if title:
            children.append(ComponentFactory.create_text(title, TextStyle(font_weight="bold", font_size="16px")))
        if content:
            children.append(content)
        return Component(component_type=ComponentType.CARD, layout_type=LayoutType.COLUMN,
                         style=style or StyleDefinition(border="1px solid #E0E0E0", border_radius="8px", padding="16px"),
                         children=children)

    @staticmethod
    def create_badge(text, color="primary"):
        return Component(component_type=ComponentType.BADGE, text_content=text, properties={"variant": color})

    @staticmethod
    def create_divider():
        return Component(component_type=ComponentType.DIVIDER,
                         style=StyleDefinition(height="1px", background_color="#E0E0E0", margin="8px 0"))

    @staticmethod
    def create_spinner(size="md"):
        return Component(component_type=ComponentType.SPINNER, properties={"size": size})

    @staticmethod
    def create_icon(icon_name, size="24px"):
        return Component(component_type=ComponentType.ICON, properties={"icon": icon_name, "size": size})

    @staticmethod
    def create_toast(message, variant="info"):
        return Component(component_type=ComponentType.TOAST, properties={"message": message, "variant": variant})

    @staticmethod
    def create_link(text, href="#"):
        return Component(component_type=ComponentType.LINK, text_content=text, attributes={"href": href})

class RenderEngine:
    def __init__(self, theme=None):
        self.theme = theme or ThemeDefinition()
        self._diff_calculator = DiffCalculator()
        self._current_tree = None
        self._command_buffer = []
        self._render_count = 0

    def render(self, tree):
        commands = self._diff_calculator.compute(self._current_tree, tree)
        self._current_tree = tree
        self._render_count += 1
        self._command_buffer = commands
        return commands

    def render_with_theme(self, tree, theme):
        self.theme = theme
        return self.render(tree)

    def batch_render(self, tree, batch_size=50):
        commands = self.render(tree)
        return [commands[i:i+batch_size] for i in range(0, len(commands), batch_size)]

    def incremental_render(self, old_tree, new_tree):
        return self._diff_calculator.compute(old_tree, new_tree)

    def render_component(self, component):
        return self.render(LayoutTree(component))

    def get_current_tree(self):
        return self._current_tree

    def reset(self):
        self._current_tree = None
        self._command_buffer = []
        self._render_count = 0

    def get_render_stats(self):
        return {
            "render_count": self._render_count,
            "buffer_size": len(self._command_buffer),
            "diff_stats": self._diff_calculator.get_stats(),
            "theme": self.theme.config.name,
        }

    def optimize_commands(self, commands):
        if len(commands) < 2:
            return commands
        optimized = []
        update_map = {}
        for cmd in commands:
            if cmd.op == RenderOp.UPDATE:
                if cmd.target_id in update_map:
                    update_map[cmd.target_id].payload["changes"].update(cmd.payload.get("changes", {}))
                else:
                    update_map[cmd.target_id] = cmd
                    optimized.append(cmd)
            elif cmd.op == RenderOp.CREATE and cmd.target_id in update_map:
                optimized.append(cmd)
                optimized.append(update_map.pop(cmd.target_id))
            else:
                optimized.append(cmd)
        return optimized

def layout_from_json(data):
    return LayoutTree.from_json(data)

def layout_to_json(tree):
    return tree.to_json()

def merge_layouts(base, overlay):
    def _merge_nodes(bn, on):
        if on.style:
            bn.style = bn.style.merge(on.style) if bn.style else on.style
        if on.text_content:
            bn.text_content = on.text_content
        if on.properties:
            bn.properties = {**(bn.properties or {}), **on.properties}
        if on.classes:
            bn.classes = list(set(bn.classes + on.classes))
        if on.attributes:
            bn.attributes.update(on.attributes)
        if on.data_attributes:
            bn.data_attributes.update(on.data_attributes)
        oc_map = {c.id: c for c in on.children}
        for child in bn.children:
            if child.id in oc_map:
                _merge_nodes(child, oc_map[child.id])
        for oc in on.children:
            if not any(bc.id == oc.id for bc in bn.children):
                bn.children.append(oc)
        return bn
    _merge_nodes(base.root, overlay.root)
    return base

def validate_component(component):
    errors = []
    if not component.id:
        errors.append("Component missing id")
    if component.component_type == ComponentType.TEXT and not component.text_content:
        if not component.children:
            errors.append("Text component has no content")
    if component.component_type == ComponentType.IMAGE:
        props = component.properties or {}
        if not props.get("src"):
            errors.append("Image component missing src")
    if component.component_type == ComponentType.INPUT:
        props = component.properties or {}
        if not props.get("name"):
            errors.append("Input component missing name")
    for child in component.children:
        errors.extend(validate_component(child))
    return errors

__all__ = [
    "LayoutType", "ComponentType", "EventType", "RenderOp",
    "StyleDefinition", "TextStyle", "FlexStyle", "GridStyle",
    "TextProperties", "ImageProperties", "ButtonProperties",
    "InputProperties", "ProgressProperties", "ChartProperties",
    "ListProperties", "FormProperties", "TableProperties", "SliderProperties",
    "EventBinding", "ThemePalette", "TypographyConfig", "SpacingConfig",
    "BorderRadiusConfig", "ShadowConfig", "BreakpointConfig",
    "AnimationConfig", "ThemeConfig", "ThemeDefinition",
    "Component", "LayoutTree", "RenderCommand", "RenderEngine",
    "ComponentFactory", "DiffCalculator",
    "layout_from_json", "layout_to_json", "merge_layouts", "validate_component",
]
