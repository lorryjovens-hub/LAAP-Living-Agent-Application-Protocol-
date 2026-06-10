"""ContextCompressor — 智能上下文压缩(摘要/裁剪/关键信息保护)"""
from __future__ import annotations
import time, json, logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("agent_core.context_compressor")

class ContextCompressor:
    def __init__(self, max_tokens: int = 32000, compression_ratio: float = 0.5):
        self.max_tokens = max_tokens
        self.compression_ratio = compression_ratio
        self._callbacks: List[Callable] = []
    
    def estimate_tokens(self, messages: List[dict]) -> int:
        total = 0
        for msg in messages:
            total += len(msg.get("content", "")) // 2 + 50
        return total
    
    def compress(self, messages: List[dict]) -> List[dict]:
        if self.estimate_tokens(messages) <= self.max_tokens:
            return messages
        
        logger.info(f"Compressing {len(messages)} messages...")
        target_tokens = int(self.max_tokens * self.compression_ratio)
        
        # Strategy 1: Summarize old messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        recent_msgs = messages[-6:]  # Keep last 3 exchanges
        middle_msgs = messages[len(system_msgs):-6]
        
        if middle_msgs:
            summary = self._summarize_middle(middle_msgs)
            compressed = system_msgs + [{"role": "system", "content": f"[压缩摘要] {summary[:500]}"}] + recent_msgs
            logger.info(f"Compressed {len(messages)} -> {len(compressed)} messages")
            return compressed
        
        # Strategy 2: Truncate oldest
        while self.estimate_tokens(messages) > self.max_tokens and len(messages) > 4:
            messages.pop(1)
        
        return messages
    
    def _summarize_middle(self, messages: List[dict]) -> str:
        topics = set()
        key_points = []
        for msg in messages:
            content = msg.get("content", "")
            if msg["role"] == "user":
                key_points.append(f"U: {content[:80]}")
            elif msg["role"] == "assistant":
                key_points.append(f"A: {content[:80]}")
        return "; ".join(key_points[-10:])
    
    def on_compress(self, callback: Callable):
        self._callbacks.append(callback)
    
    def get_stats(self) -> dict:
        return {"max_tokens": self.max_tokens, "compression_ratio": self.compression_ratio}
