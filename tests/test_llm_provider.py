"""Test LLM Provider implementations"""
import sys
sys.path.insert(0, r"D:\LAAP")
from laap.llm.provider import (
    AnthropicProvider, OpenAICompatProvider,
    Message, ToolDef, StreamEvent,
)


def test_anthropic_provider_import():
    p = AnthropicProvider(model="claude-sonnet-4-6", api_key="test-key")
    assert p.model == "claude-sonnet-4-6"
    assert p.api_key == "test-key"


def test_message_system():
    msg = Message.system("You are a helpful assistant.")
    assert msg.role == "system"
    assert msg.content == "You are a helpful assistant."


def test_message_user():
    msg = Message.user("Hello!")
    assert msg.role == "user"


def test_message_tool_result():
    msg = Message.tool_result(content="Success", tool_call_id="call_123", name="test_tool")
    assert msg.role == "tool"
    assert msg.tool_call_id == "call_123"


def test_tool_def_to_anthropic():
    td = ToolDef(name="test_tool", description="A test tool",
                 parameters={"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]})
    ad = td.to_anthropic_dict()
    assert ad["name"] == "test_tool"


def test_tool_def_to_openai():
    td = ToolDef(name="test_tool", description="A test tool",
                 parameters={"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]})
    od = td.to_openai_dict()
    assert od["function"]["name"] == "test_tool"


def test_stream_event_types():
    ev = StreamEvent(type="token", content="hello")
    assert ev.type == "token"
    assert not ev.done
    ev = StreamEvent(type="done", done=True)
    assert ev.done


def test_openai_compat_tool_support():
    p = OpenAICompatProvider(model="gpt-4o", api_key="test")
    assert p.supports_tools
