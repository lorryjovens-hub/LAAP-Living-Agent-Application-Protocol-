"""LAAP Gateway — Multi-Platform Messaging Gateway

Start with: laap gateway [--platform telegram] [--token xxx]
"""

from laap.gateway.engine import GatewayEngine, SessionStore, PlatformRegistry, SessionEntry
from laap.gateway.base import BaseAdapter
from laap.gateway.events import GatewayEvent, MessageChunk, MessageStop, ToolCallChunk

__all__ = [
    "GatewayEngine", "SessionStore", "PlatformRegistry", "SessionEntry",
    "BaseAdapter",
    "GatewayEvent", "MessageChunk", "MessageStop", "ToolCallChunk",
]
