"""
LAAP LLM Provider — 多模型提供者抽象层
支持 OpenAI / Anthropic / DeepSeek / 本地模型
"""
from __future__ import annotations
import time, json, logging, os, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, AsyncIterator
import urllib.request
import urllib.error

logger = logging.getLogger("agent_core.llm")

@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: str = ""
    api_base: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9
    timeout: int = 60

@dataclass
class LLMResponse:
    content: str = ""
    finish_reason: str = "stop"
    usage: Dict = field(default_factory=dict)
    model: str = ""
    latency_ms: float = 0.0
    
    def to_dict(self) -> dict:
        return {"content": self.content[:200], "finish_reason": self.finish_reason,
                "usage": self.usage, "model": self.model, "latency_ms": self.latency_ms}

class TokenBucket:
    """令牌桶限流器"""
    def __init__(self, rate: float = 10, capacity: int = 20):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.RLock()
    
    def acquire(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.time()
            refill = (now - self.last_refill) * self.rate
            self.tokens = min(self.capacity, self.tokens + refill)
            self.last_refill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class LLMProvider:
    """LLM提供者 — 支持OpenAI/Anthropic/DeepSeek格式"""
    
    PROVIDERS = {
        "openai": {"base": "https://api.openai.com/v1", "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]},
        "deepseek": {"base": "https://api.deepseek.com/v1", "models": ["deepseek-chat", "deepseek-coder"]},
        "anthropic": {"base": "https://api.anthropic.com/v1", "models": ["claude-3-opus", "claude-3-sonnet"]},
        "openrouter": {"base": "https://openrouter.ai/api/v1", "models": ["*"]},
    }
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self._ratelimiter = TokenBucket()
        self._callbacks: Dict[str, Callable] = {}
        self._stats = {"total_calls": 0, "total_tokens": 0, "total_latency": 0.0}
    
    def on(self, event: str, callback: Callable):
        self._callbacks[event] = callback
    
    def chat(self, messages: List[dict], tools: List[dict] = None,
             stream: bool = False) -> LLMResponse:
        """调用LLM聊天补全"""
        start = time.time()
        self._stats["total_calls"] += 1
        
        # 模拟响应 — 真实环境会调用网络API
        response = self._simulate_chat(messages, tools)
        
        latency = (time.time() - start) * 1000
        response.latency_ms = latency
        self._stats["total_latency"] += latency
        self._stats["total_tokens"] += response.usage.get("total_tokens", 0)
        
        if "response" in self._callbacks:
            self._callbacks["response"](response)
        
        return response
    
    def _simulate_chat(self, messages: List[dict], tools: List[dict] = None) -> LLMResponse:
        """调用真实LLM API — 支持DeepSeek/OpenAI格式"""
        import urllib.request, urllib.error, json as _json
        
        api_key = self.config.api_key
        if not api_key:
            # 无API key时回退到模拟模式
            last = messages[-1] if messages else {}
            content = last.get("content", "")
            return LLMResponse(
                content=f"【模拟】收到: {content[:100]}...",
                finish_reason="stop",
                usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
                model=self.config.model,
            )
        
        api_base = self.config.api_base or "https://api.deepseek.com/v1"
        url = f"{api_base.rstrip('/')}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        
        # 构建请求体
        body = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
            "stream": False,
        }
        
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        
        try:
            data = _json.dumps(body).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                result = _json.loads(resp.read().decode('utf-8'))
            
            choice = result["choices"][0]
            message = choice["message"]
            content = message.get("content", "") or ""
            finish = choice.get("finish_reason", "stop")
            
            # 工具调用
            tool_calls = message.get("tool_calls", [])
            
            usage = result.get("usage", {})
            
            return LLMResponse(
                content=content,
                finish_reason=finish,
                usage={"prompt_tokens": usage.get("prompt_tokens", 0),
                       "completion_tokens": usage.get("completion_tokens", 0),
                       "total_tokens": usage.get("total_tokens", 0)},
                model=result.get("model", self.config.model),
            )
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')[:500]
            logger.error(f"LLM API HTTP {e.code}: {error_body}")
            return LLMResponse(
                content=f"【API错误 {e.code}】: {error_body}",
                finish_reason="error",
                model=self.config.model,
            )
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return LLMResponse(
                content=f"【错误】: {str(e)[:200]}",
                finish_reason="error",
                model=self.config.model,
            )
    

    def stream_chat(self, messages, tools=None):
        """流式调用LLM，yield每个token"""
        import urllib.request, json as _json, time
        api_key = self.config.api_key
        if not api_key:
            yield "【模拟】"
            return
        api_base = self.config.api_base or "https://api.deepseek.com/v1"
        url = f"{api_base.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        body = {"model": self.config.model, "messages": messages,
                "temperature": self.config.temperature, "max_tokens": self.config.max_tokens,
                "stream": True}
        data = _json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=self.config.timeout)
            buffer = ""
            for chunk_bytes in iter(lambda: resp.read(1), b''):
                buffer += chunk_bytes.decode('utf-8', errors='replace')
                while chr(10) in buffer:
                    line, buffer = buffer.split(chr(10), 1)
                    if line.startswith('data: '):
                        data_str = line[6:].strip()
                        if data_str == '[DONE]':
                            return
                        try:
                            chunk = _json.loads(data_str)
                            delta = chunk.get('choices', [{}])[0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield content
                        except:
                            pass
        except Exception as e:
            yield f"【错误:{e}】"
    def count_tokens(self, text: str) -> int:
        return len(text) // 2 + len(text.split())
    
    def get_stats(self) -> dict:
        avg_latency = self._stats["total_latency"] / max(self._stats["total_calls"], 1)
        return {**self._stats, "avg_latency_ms": round(avg_latency, 2), "model": self.config.model}


class LLMFactory:
    """LLM工厂 — 按配置创建Provider"""
    
    @staticmethod
    def create(provider: str = "openai", model: str = "gpt-4",
               api_key: str = "", **kwargs) -> LLMProvider:
        config = LLMConfig(provider=provider, model=model, api_key=api_key, **kwargs)
        
        # 自动补全API base
        if provider in LLMProvider.PROVIDERS and not config.api_base:
            config.api_base = LLMProvider.PROVIDERS[provider]["base"]
        
        return LLMProvider(config)
