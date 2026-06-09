"""Test LAAP Base Agent"""
import sys
sys.path.insert(0, r"D:\LAAP")
from laap.agent.base import Agent, AgentConfig
from laap.memory.hierarchical import HierarchicalMemory


def test_agent_init():
    a = Agent()
    assert a.alive
    assert a.step_count == 0
    assert a.id is not None


def test_agent_config():
    cfg = AgentConfig(name="TestAgent")
    a = Agent(config=cfg)
    assert a.config.name == "TestAgent"


def test_register_tool():
    a = Agent()
    a.register_tool("hello", lambda name: f"Hi {name}", "Say hello")
    assert a.tool_registry.get("hello") is not None
    assert a.tool_registry.count >= 1


def test_call_tool():
    a = Agent()
    a.register_tool("double", lambda x: x * 2, "Double value")
    result = a.call_tool("double", x=5)
    assert result == 10


def test_call_unknown_tool():
    a = Agent()
    result = a.call_tool("nonexistent")
    assert "not found" in str(result)


def test_die():
    a = Agent()
    a.die("test")
    assert not a.alive


def test_apply_modification():
    a = Agent()
    assert a.config.exploration_rate != 0.5
    ok = a.apply_modification({
        "type": "adjust_exploration",
        "params": {"value": 0.5},
    })
    assert ok
    assert a.config.exploration_rate == 0.5


def test_apply_invalid_modification():
    a = Agent()
    ok = a.apply_modification({"type": "invalid_type", "params": {}})
    assert not ok


def test_status():
    a = Agent()
    s = a.status()
    assert "id" in s
    assert "alive" in s
    assert "steps" in s


def test_memory():
    a = Agent()
    assert isinstance(a.memory, HierarchicalMemory)
    a.memory.perceive("test observation", importance=0.8)
    assert len(a.memory.wm) == 1


def test_no_duplicate_tool_registration():
    """Tools should not be registered more than once"""
    from laap.tools.tool_registry import ToolRegistry
    a = Agent()
    first_count = a.tool_registry.count
    # Manually trigger init again — should be idempotent
    a._init_tools()
    assert a.tool_registry.count == first_count, (
        f"Tool count changed from {first_count} to {a.tool_registry.count}"
    )


def test_tool_registry_no_overwrite():
    """register_tool should not silently overwrite existing tools"""
    from laap.tools.tool_registry import ToolRegistry
    from laap.tools.base import Tool
    tr = ToolRegistry()
    t1 = Tool(name="test_tool", description="first",
              parameters={"type": "object", "properties": {}},
              handler=lambda: "first")
    t2 = Tool(name="test_tool", description="second",
              parameters={"type": "object", "properties": {}},
              handler=lambda: "second")
    tr.register(t1)
    result = tr.register(t2)
    assert result is False, "Register should return False when skipping duplicate"
    retrieved = tr.get("test_tool")
    assert retrieved.description == "first", "Tool was silently overwritten"
