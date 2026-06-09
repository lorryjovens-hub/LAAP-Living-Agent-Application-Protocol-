"""Test LAAP Tools — Tool, ToolRegistry, HermesAdapter, Ao Registry"""
import sys
sys.path.insert(0, r"D:\LAAP")

import json
from typing import Optional

from laap.tools.base import Tool, infer_json_schema, _resolve_type
from laap.tools.tool_registry import ToolRegistry
from laap.tools.registry import ao as ao_registry
from laap.tools.hermes_adapter import HermesAdapter, ao_tool, sync_default


# ── Tool Base ────────────────────────────────────────────────

def test_tool_defaults():
    t = Tool(name="test")
    assert t.name == "test"
    assert t.description == ""
    assert t.parameters == {"type": "object", "properties": {}}
    assert t.handler is None
    assert t.category == "general"


def test_tool_full():
    def handler(): return "ok"
    t = Tool(name="full", description="desc",
             parameters={"type": "object", "properties": {"x": {"type": "int"}}},
             handler=handler, category="custom")
    assert t.name == "full"
    assert t.handler() == "ok"
    assert t.category == "custom"


def test_tool_to_dict():
    t = Tool(name="greet", description="Say hello", category="chat")
    d = t.to_dict()
    assert d["name"] == "greet"
    assert "description" in d
    assert "category" in d
    assert "parameters" in d


def test_tool_to_tool_def():
    t = Tool(name="calc", description="Calculator",
             parameters={"type": "object", "properties": {"x": {"type": "int"}}})
    td = t.to_tool_def()
    assert td.name == "calc"
    assert td.description == "Calculator"
    assert td.parameters == t.parameters


# ── infer_json_schema ────────────────────────────────────────

def test_infer_json_schema_basic():
    schema = infer_json_schema({"name": str, "count": int})
    assert schema["type"] == "object"
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["properties"]["count"]["type"] == "integer"
    assert "name" in schema["required"]
    assert "count" in schema["required"]


def test_infer_json_schema_with_descriptions():
    schema = infer_json_schema(
        {"name": str, "age": int},
        {"name": "The person's name", "age": "Their age in years"},
    )
    assert schema["properties"]["name"]["description"] == "The person's name"
    assert schema["properties"]["age"]["description"] == "Their age in years"


def test_infer_json_schema_optional():
    schema = infer_json_schema({"name": str, "nickname": Optional[str]})
    assert "name" in schema["required"]
    assert "nickname" not in schema["required"]


def test_infer_json_schema_strict():
    schema = infer_json_schema({"name": str}, strict=True)
    # In strict mode, everything is required
    assert schema["required"] == ["name"]


def test_infer_json_schema_empty():
    schema = infer_json_schema({})
    assert schema["type"] == "object"
    assert schema["properties"] == {}
    assert schema["required"] == []


# ── ToolRegistry ─────────────────────────────────────────────

def test_registry_init():
    tr = ToolRegistry()
    assert tr.count == 0
    assert tr.categories == []


def test_registry_register_and_get():
    tr = ToolRegistry()
    t = Tool(name="hello", description="Say hi", handler=lambda: "hi")
    assert tr.register(t) is True
    assert tr.get("hello") is t
    assert tr.count == 1


def test_registry_no_duplicate():
    tr = ToolRegistry()
    t1 = Tool(name="dup", handler=lambda: "first")
    t2 = Tool(name="dup", handler=lambda: "second")
    tr.register(t1)
    assert tr.register(t2) is False  # should reject duplicate
    assert tr.get("dup").handler() == "first"  # original preserved


def test_registry_overwrite():
    tr = ToolRegistry()
    t1 = Tool(name="over", handler=lambda: "old")
    t2 = Tool(name="over", handler=lambda: "new")
    tr.register(t1)
    tr.register(t2, overwrite=True)
    assert tr.get("over").handler() == "new"


def test_registry_call():
    tr = ToolRegistry()
    tr.register(Tool(name="double", handler=lambda x: x * 2))
    result = tr.call("double", x=5)
    assert result == 10


def test_registry_call_unknown():
    tr = ToolRegistry()
    result = tr.call("nonexistent")
    assert "error" in json.loads(result)
    assert "not found" in json.loads(result)["error"]


def test_registry_call_error():
    tr = ToolRegistry()
    def buggy(**kw):
        raise ValueError("oops")
    tr.register(Tool(name="buggy", handler=buggy))
    result = json.loads(tr.call("buggy"))
    assert "error" in result
    assert "ValueError" in result["error"]


def test_registry_list():
    tr = ToolRegistry()
    tr.register(Tool(name="a", category="cat1"))
    tr.register(Tool(name="b", category="cat2"))
    tr.register(Tool(name="c", category="cat1"))
    all_tools = tr.list()
    assert len(all_tools) == 3
    cat1 = tr.list(category="cat1")
    assert len(cat1) == 2
    assert cat1[0].name in ("a", "c")


def test_registry_list_invalid_category():
    tr = ToolRegistry()
    tr.register(Tool(name="x"))
    result = tr.list(category="nonexistent")
    assert result == []


def test_registry_categories():
    tr = ToolRegistry()
    tr.register(Tool(name="a", category="alpha"))
    tr.register(Tool(name="b", category="beta"))
    cats = tr.categories
    assert "alpha" in cats
    assert "beta" in cats


def test_registry_count_by_category():
    tr = ToolRegistry()
    tr.register(Tool(name="a", category="cat"))
    tr.register(Tool(name="b", category="cat"))
    counts = tr.count_by_category()
    assert counts.get("cat") == 2


def test_registry_register_fn():
    tr = ToolRegistry()
    ok = tr.register_fn(lambda who: f"Hi {who}", name="greet", description="Say hello")
    assert ok is True
    assert tr.get("greet") is not None
    result = tr.call("greet", who="World")
    assert result == "Hi World"


def test_registry_register_fn_no_name():
    """register_fn should default to function name."""
    tr = ToolRegistry()
    ok = tr.register_fn(lambda: "hello")
    assert ok is True


# ── ToolRegistry (from agent tests, extended) ────────────────

def test_registry_init_empty():
    tr = ToolRegistry()
    assert tr.count == 0


def test_registry_get_missing():
    tr = ToolRegistry()
    assert tr.get("nope") is None


# ── HermesAdapter ───────────────────────────────────────────

def test_hermes_adapter_init():
    tr = ToolRegistry()
    adapter = HermesAdapter(tr)
    assert adapter._laap is tr
    assert adapter.mapped_count == 0
    assert adapter.sync_count == 0


def test_hermes_adapter_sync_from_ao():
    """Sync tools from Ao registry into a LAAP ToolRegistry."""
    # Register a tool in Ao registry first
    ao_registry.register(
        name="ao_test_tool",
        toolset="test",
        schema={"name": "ao_test_tool", "description": "Test tool",
                "properties": {"x": {"type": "int"}}},
        handler=lambda args: json.dumps({"result": args.get("x", 0) * 2}),
        description="Test tool from Ao",
        override=True,
    )
    assert ao_registry.get_entry("ao_test_tool") is not None

    tr = ToolRegistry()
    adapter = HermesAdapter(tr)
    count = adapter.sync_from_ao(toolset_filter="test")
    assert count >= 1

    # Verify the tool was synced
    synced = tr.get("ao_test_tool")
    assert synced is not None
    assert synced.description == "Test tool from Ao"
    assert synced.category == "test"

    # Verify it works
    result = json.loads(tr.call("ao_test_tool", x=5))
    assert result["result"] == 10


def test_hermes_adapter_sync_with_overwrite():
    """sync_from_ao with overwrite=True should overwrite existing tools."""
    tr = ToolRegistry()
    tr.register(Tool(name="ao_test_tool", description="old", handler=lambda: "old"), overwrite=True)
    adapter = HermesAdapter(tr)
    adapter.sync_from_ao(toolset_filter="test", overwrite=True)
    synced = tr.get("ao_test_tool")
    assert synced is not None
    assert synced.description == "Test tool from Ao"  # overwritten


def test_hermes_adapter_push_to_ao():
    """Push a LAAP tool into the Ao registry."""
    tr = ToolRegistry()
    tr.register(Tool(name="laap_push_test", description="Pushed from LAAP",
                     handler=lambda x: x * 3))
    adapter = HermesAdapter(tr)
    ok = adapter.push_to_ao("laap_push_test", toolset="laap_tools")
    assert ok is True

    # Verify in Ao registry
    entry = ao_registry.get_entry("laap_push_test")
    assert entry is not None
    assert entry.toolset == "laap_tools"


def test_hermes_adapter_push_missing():
    """Push a nonexistent tool should return False."""
    tr = ToolRegistry()
    adapter = HermesAdapter(tr)
    ok = adapter.push_to_ao("nope")
    assert ok is False


def test_hermes_adapter_push_all():
    """Push all LAAP tools matching a category."""
    tr = ToolRegistry()
    tr.register(Tool(name="cat_a", category="group1", handler=lambda: "a"))
    tr.register(Tool(name="cat_b", category="group1", handler=lambda: "b"))
    tr.register(Tool(name="other",  category="group2", handler=lambda: "c"))
    adapter = HermesAdapter(tr)
    count = adapter.push_all_to_ao(toolset="pushed", category_filter="group1")
    assert count == 2
    assert ao_registry.get_entry("cat_a") is not None
    assert ao_registry.get_entry("cat_b") is not None


def test_hermes_adapter_list():
    """list_adapter_tools should return mapping info."""
    tr = ToolRegistry()
    adapter = HermesAdapter(tr)
    # Push one tool first to create entry
    tr.register(Tool(name="mapped_tool", handler=lambda: "x"))
    adapter.push_to_ao("mapped_tool")
    entries = adapter.list_adapter_tools()
    assert len(entries) >= 1
    entry = entries[0]
    assert "laap_name" in entry
    assert "ao_name" in entry


# ── @ao_tool decorator ───────────────────────────────────────

def test_ao_tool_decorator():
    """@ao_tool should register a function in the Ao registry."""
    @ao_tool(name="decorated_test", toolset="decorated", description="From decorator")
    def my_tool(args: dict) -> str:
        return json.dumps({"echo": args.get("msg", "")})

    entry = ao_registry.get_entry("decorated_test")
    assert entry is not None
    assert entry.toolset == "decorated"

    result = json.loads(ao_registry.dispatch("decorated_test", {"msg": "hello"}))
    assert result["echo"] == "hello"


def test_ao_tool_kwargs_style():
    """@ao_tool should also work with expanded kwargs."""
    @ao_tool(name="kwarg_tool", toolset="test", description="kwargs style")
    def kw_tool(x: int, y: int = 0) -> str:
        return json.dumps({"sum": x + y})

    entry = ao_registry.get_entry("kwarg_tool")
    assert entry is not None

    result = json.loads(ao_registry.dispatch("kwarg_tool", {"x": 3, "y": 4}))
    assert result["sum"] == 7


# ── sync_default convenience ─────────────────────────────────

def test_sync_default():
    """sync_default should work without error."""
    tr = ToolRegistry()
    count = sync_default(tr, toolset="test")
    assert isinstance(count, int)


# ── Ao Registry (direct) ─────────────────────────────────────

def test_ao_registry_get_definitions():
    """get_definitions should return OpenAI-format schemas."""
    defs = ao_registry.get_definitions({"ao_test_tool"})
    assert isinstance(defs, list)


def test_ao_registry_dispatch_unknown():
    result = json.loads(ao_registry.dispatch("nonexistent_tool", {}))
    assert "error" in result


def test_ao_registry_get_entry_missing():
    assert ao_registry.get_entry("__does_not_exist__") is None


def test_ao_registry_tool_error():
    result = json.loads(ao_registry.dispatch("ao_test_tool", {"x": "not_a_number"}))
    # Should handle gracefully — either error or result
    assert isinstance(result, dict)


# ── Tool Result / Error helpers ──────────────────────────────

def test_tool_result_helper():
    result = json.loads(ao_registry.tool_result(data={"ok": True}))
    assert result == {"ok": True}

    result = json.loads(ao_registry.tool_result(success=True, value=42))
    assert result["success"] is True
    assert result["value"] == 42


def test_tool_error_helper():
    result = json.loads(ao_registry.tool_error("Something broke", code=500))
    assert result["error"] == "Something broke"
    assert result["code"] == 500
