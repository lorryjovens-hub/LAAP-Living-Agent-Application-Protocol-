"""LAAP — 工具基础：JSON Schema 推理、Tool 数据类与工具辅助函数"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import typing

# Python 3.13+ 兼容: get_type_origin / get_args 从 typing 中移除
try:
    from typing import get_type_origin, get_args  # type: ignore
except ImportError:
    def get_type_origin(tp):
        """简化版 get_type_origin"""
        return getattr(tp, '__origin__', None)
    def get_args(tp):
        """简化版 get_args"""
        return getattr(tp, '__args__', ())


_type_map = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    dict: "object",
    list: "array",
    type(None): "null",
}
for t in (str, int, float, bool, dict, list):
    _type_map[typing.Optional[t]] = _type_map[t]
    _type_map[typing.List[t]] = "array"
    _type_map[typing.Dict[str, t]] = "object"


def _resolve_type(tp) -> str:
    origin = get_type_origin(tp) if hasattr(tp, "__origin__") else None
    if origin is list or origin is List:
        return "array"
    if origin is dict or origin is Dict:
        return "object"
    if tp in _type_map:
        return _type_map[tp]
    if hasattr(tp, "__name__"):
        return _type_map.get(tp, "string")
    return "string"


def infer_json_schema(
    type_hints: Dict[str, Any],
    param_descriptions: Dict[str, str] = None,
    strict: bool = False,
) -> Dict[str, Any]:
    """从类型提示推断 JSON Schema"""
    param_descriptions = param_descriptions or {}
    properties = {}
    for name, hint in type_hints.items():
        ptype = _resolve_type(hint)
        prop = {"type": ptype}
        if name in param_descriptions and param_descriptions[name]:
            prop["description"] = param_descriptions[name]
        properties[name] = prop

    required = [
        name for name, hint in type_hints.items()
        if not _is_optional(hint)
    ]
    if strict:
        required = list(properties.keys())

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _is_optional(tp) -> bool:
    """检查类型是否 Optional"""
    origin = get_type_origin(tp) if hasattr(tp, "__origin__") else None
    if origin is typing.Union:
        args = get_args(tp)
        return type(None) in args
    return False


@dataclass
class Tool:
    """工具定义：名称、描述、参数 schema、执行函数"""
    name: str
    description: str = ""
    parameters: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    handler: Optional[Callable] = None
    category: str = "general"
    metadata: dict = field(default_factory=dict)

    def to_tool_def(self):
        """转换为 LLM provider 使用的 ToolDef 格式"""
        from laap.llm.provider import ToolDef
        return ToolDef(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description[:80],
            "category": self.category,
            "parameters": list(self.parameters.get("properties", {}).keys()),
        }
