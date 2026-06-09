"""Shared test fixtures for LAAP tests"""
import sys
sys.path.insert(0, r"D:\LAAP")

from pathlib import Path
from laap.agent.base import Agent, AgentConfig
from laap.store.session import AoDB
from laap.llm.provider import StreamEvent


class MockLLM:
    """Mock LLM that returns predefined responses — no API key needed"""
    def __init__(self, responses=None):
        self.responses = responses or ["Mock response"]
        self._call_count = 0
        self.supports_tools = False

    def chat_stream(self, messages, tools=None):
        response = self.responses[self._call_count % len(self.responses)]
        self._call_count += 1
        yield StreamEvent(type="token", content=response)
        ev = StreamEvent(type="done", done=True)
        ev._content = response
        yield ev


class MockFactory:
    def __init__(self, responses=None):
        self._responses = responses
    def get(self, name="", model=""):
        return MockLLM(self._responses)


def create_test_agent(with_llm=False):
    """Create minimal Agent without API keys"""
    config = AgentConfig(name="TestAgent", verbose=False, tools_enabled=False)
    agent = Agent(config=config)
    if with_llm:
        agent.llm = MockLLM()
    return agent


def create_test_db(tmp_path: Path) -> AoDB:
    """Create a temporary AoDB"""
    return AoDB(db_path=tmp_path / "test_state.db")
