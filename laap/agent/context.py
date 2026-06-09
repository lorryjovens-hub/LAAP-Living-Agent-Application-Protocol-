"""
LAAP — Context Compression (ported from Hermes Agent)

Sliding-window context compression for long conversations.
Keeps system prompt + first N turns + last M turns, compresses middle.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("laap.agent.context")


def compress_messages(
    messages: List[Dict[str, Any]],
    keep_first: int = 3,
    keep_last: int = 8,
    max_before_compress: int = 20,
) -> List[Dict[str, Any]]:
    """Compress conversation messages using sliding window.

    Keeps:
      - System message(s)
      - First `keep_first` user/assistant turns
      - Last `keep_last` user/assistant/tool turns
    Collapses the middle into a single summary message.

    Args:
        messages: List of message dicts with 'role' and 'content'
        keep_first: Number of initial messages to keep (after system)
        keep_last: Number of final messages to keep
        max_before_compress: Max messages before compression triggers

    Returns:
        Compressed message list
    """
    if len(messages) <= max_before_compress:
        return messages

    # Separate system messages
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    if not non_system:
        return messages

    # Keep first N and last M
    first_batch = non_system[:keep_first]
    last_batch = non_system[-keep_last:]
    middle = non_system[keep_first:-keep_last]

    if not middle:
        return messages

    # Create summary message from middle
    summary = _summarize_middle(middle)

    result = list(system_msgs) + first_batch + [summary] + last_batch
    logger.info(
        f"Context compressed: {len(messages)} → {len(result)} "
        f"(dropped {len(middle)} middle messages)"
    )
    return result


def _summarize_middle(middle: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a summary message from the middle section.

    Extracts key information: tool calls made, files changed, decisions.
    """
    tool_calls = []
    file_changes = []
    decisions = []
    total_tokens = 0

    for m in middle:
        role = m.get("role", "")
        content = m.get("content", "")
        tc = m.get("tool_calls")

        if tc:
            for t in (tc if isinstance(tc, list) else []):
                fn = t.get("function", {}).get("name", "")
                if fn:
                    tool_calls.append(fn)

        if role == "tool":
            total_tokens += len(content)

        # Detect file changes
        if "write_file" in content or "patch" in content:
            file_changes.append("[file operation]")
        if "decision" in content.lower() or "conclusion" in content.lower():
            decisions.append(content[:100])

    # Deduplicate
    tool_calls = list(dict.fromkeys(tool_calls))

    summary_parts = [
        f"[Compressed: {len(middle)} messages with {len(tool_calls)} tool types omitted]",
    ]
    if tool_calls:
        summary_parts.append(f"Tools used: {', '.join(tool_calls[:10])}")
    if file_changes:
        summary_parts.append(f"File operations performed")
    if total_tokens > 1000:
        summary_parts.append(f"~{total_tokens} tokens of tool output")

    return {
        "role": "system",
        "content": " | ".join(summary_parts),
    }


class ContextManager:
    """Manages conversation context with automatic compression.

    Usage:
        ctx = ContextManager(max_rounds=20)
        ctx.add_message(Message.user("hello"))
        ctx.add_message(Message.assistant("hi"))
        # When limit is reached, automatically compresses
        messages = ctx.get_messages()
    """

    def __init__(self, max_rounds: int = 20,
                 keep_first: int = 3, keep_last: int = 8):
        self.max_rounds = max_rounds
        self.keep_first = keep_first
        self.keep_last = keep_last
        self._messages: List[Dict[str, Any]] = []
        self._compression_count = 0

    def add_message(self, msg: Dict[str, Any]):
        """Add a message and auto-compress if needed."""
        self._messages.append(msg)
        if len(self._messages) > self.max_rounds:
            self.compress()

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages (compressed if needed)."""
        return list(self._messages)

    def compress(self):
        """Force compression now."""
        before = len(self._messages)
        self._messages = compress_messages(
            self._messages,
            keep_first=self.keep_first,
            keep_last=self.keep_last,
            max_before_compress=self.max_rounds,
        )
        self._compression_count += 1
        logger.debug(f"Compressed {before} → {len(self._messages)} (round {self._compression_count})")

    @property
    def compression_count(self) -> int:
        return self._compression_count

    def reset(self):
        """Clear all messages."""
        self._messages = []
        self._compression_count = 0
