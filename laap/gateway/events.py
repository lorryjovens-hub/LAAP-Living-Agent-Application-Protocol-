"""LAAP Gateway — Stream Events

Typed events for real-time streaming of agent responses across platforms.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MessageChunk:
    """A chunk of streaming text from the agent."""
    text: str
    index: int = 0


@dataclass
class MessageStop:
    """Signal that the response stream is complete."""
    content: str
    tool_calls: Optional[List[Dict]] = None


@dataclass
class ToolCallChunk:
    """A tool call detected during streaming."""
    name: str
    args: Dict[str, Any]
    id: str = ""


@dataclass
class ToolCallResult:
    """Result of a tool execution."""
    name: str
    result: str
    duration: float
    success: bool = True


@dataclass
class GatewayEvent:
    """Unified gateway event wrapper."""
    type: str  # "message", "tool_call", "tool_result", "error", "done"
    data: Any = None
    session_id: str = ""
    platform: str = ""
    chat_id: str = ""
    user_id: str = ""
