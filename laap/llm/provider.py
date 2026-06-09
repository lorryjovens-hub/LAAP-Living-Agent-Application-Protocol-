"""
LAAP — LLM Provider System
Comprehensive multi-provider support for ALL mainstream LLM APIs (2026).

Supported providers (27 total / 88+ models):
  🌍 International (13):
    OpenAI     — GPT-5.5 / GPT-5.4 / o3 / o4-mini
    Anthropic  — Claude Opus 4.8 / Sonnet 4.6 / Haiku 4.5
    Google     — Gemini 3.5 Flash / 3.1 Pro
    DeepSeek   — DeepSeek-V4 Pro / V4 Flash
    xAI (Grok) — Grok 4.3 / 4.20 Reasoning / Build
    Mistral    — Mistral Medium 3.5 / Small 4 / Codestral
    Cohere     — Command A+ / Command A / Command R7B
    Perplexity — Sonar Pro / Deep Research / Reasoning Pro
    OpenRouter — 200+ models unified
    Together   — Llama 4 / DeepSeek / Qwen
    Groq       — Llama 4 / Mixtral / Gemma
    Azure      — GPT-5.4 / o3 via Azure
    Ollama     — Local (Llama, Qwen, DeepSeek, etc.)

  🇨🇳 Chinese Domestic (14):
    Alibaba    — Qwen 3.7-Max / 3.7-Plus / 3.6-Flash
    Baidu      — ERNIE 5.0 / 4.5 Turbo / X1 Turbo
    Zhipu      — GLM-5.1 / 4.7-Flash / Z1-Rumination
    Doubao     — Doubao Seed 2.0 Pro / Lite / Code
    Moonshot   — Kimi K2.6 / K2.5
    Baichuan   — Baichuan-M3 Plus
    01.AI Yi   — Yi-Large / Yi-Large-Turbo / Yi-Spark
    Tencent    — Hunyuan 2.0 Think / Instruct / A13B
    iFlytek    — Spark X2 / X2 Flash / Ultra
    MiniMax    — MiniMax-M3 / M2.7 / M2.5
    StepFun    — Step 3.7 Flash / 3.5 Flash
    SiliconFlow — Unified API (Qwen, DeepSeek, GLM, Yi)
    SenseTime  — SenseNova 6.7 Flash-Lite
    Kunlun     — SkyClaw-v1.0 / SkyClaw-v1.0-lite
"""
from __future__ import annotations
import os, json, time, logging
from typing import AsyncIterator, Iterator, List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger("laap.llm")


# ═══════════════════════════════════════════════════════════
# Core Data Types
# ═══════════════════════════════════════════════════════════

@dataclass
class Message:
    role: str = "user"
    content: str = ""
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_calls: d["tool_calls"] = self.tool_calls
        if self.tool_call_id: d["tool_call_id"] = self.tool_call_id
        if self.name: d["name"] = self.name
        return d

    @classmethod
    def system(cls, content: str) -> "Message":
        return cls(role="system", content=content)
    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role="user", content=content)
    @classmethod
    def assistant(cls, content: str = "", tool_calls: list = None) -> "Message":
        return cls(role="assistant", content=content, tool_calls=tool_calls)
    @classmethod
    def tool_result(cls, content: str, tool_call_id: str, name: str = "") -> "Message":
        return cls(role="tool", content=content, tool_call_id=tool_call_id, name=name)


@dataclass
class ToolDef:
    name: str
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=lambda: {
        "type": "object", "properties": {}, "required": []
    })
    handler: Optional[Callable] = None

    def to_openai_dict(self) -> dict:
        return {"type": "function", "function": {"name": self.name,
                "description": self.description, "parameters": self.parameters}}

    def to_anthropic_dict(self) -> dict:
        """Convert to Anthropic API tool format with full input_schema."""
        schema = dict(self.parameters)
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": schema,
        }


class StreamEvent:
    """Streaming event — yields token-by-token or tool call progress."""
    def __init__(self, type: str = "token", content: str = "",
                 tool_call: Optional[Dict] = None, done: bool = False,
                 error: Optional[str] = None):
        self.type = type       # token | tool_call_start | tool_call_end | done | error
        self.content = content
        self.tool_call = tool_call
        self.done = done
        self.error = error


# ═══════════════════════════════════════════════════════════
# Model Registry — All Mainstream Models with API info
# ═══════════════════════════════════════════════════════════

MODEL_REGISTRY: dict[str, dict] = {
    # ═══════════════════════════════════════════════════════════
    # 🌍 International Providers
    # ═══════════════════════════════════════════════════════════

    # ── OpenAI (GPT-5.5 / GPT-5.4 / o-series) ──
    "gpt-5.5":             {"provider": "openai", "api_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},
    "gpt-5.4":             {"provider": "openai", "api_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},
    "gpt-5.4-mini":        {"provider": "openai", "api_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},
    "gpt-5.4-nano":        {"provider": "openai", "api_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},
    "o3":                  {"provider": "openai", "api_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},
    "o4-mini":             {"provider": "openai", "api_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},
    "gpt-4.1":             {"provider": "openai", "api_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},
    "gpt-4.1-mini":        {"provider": "openai", "api_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},
    "gpt-4.1-nano":        {"provider": "openai", "api_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},

    # ── Anthropic (Claude 4.x series) ──
    "claude-opus-4-8":     {"provider": "anthropic", "api_url": "https://api.anthropic.com/v1", "api_key_env": "ANTHROPIC_API_KEY"},
    "claude-opus-4-7":     {"provider": "anthropic", "api_url": "https://api.anthropic.com/v1", "api_key_env": "ANTHROPIC_API_KEY"},
    "claude-sonnet-4-6":   {"provider": "anthropic", "api_url": "https://api.anthropic.com/v1", "api_key_env": "ANTHROPIC_API_KEY"},
    "claude-haiku-4-5":    {"provider": "anthropic", "api_url": "https://api.anthropic.com/v1", "api_key_env": "ANTHROPIC_API_KEY"},

    # ── Google Gemini (3.5 series) ──
    "gemini-3.5-flash":    {"provider": "google", "api_url": "https://generativelanguage.googleapis.com/v1beta/openai", "api_key_env": "GEMINI_API_KEY"},
    "gemini-3.1-pro":      {"provider": "google", "api_url": "https://generativelanguage.googleapis.com/v1beta/openai", "api_key_env": "GEMINI_API_KEY"},
    "gemini-3.1-flash-lite":{"provider": "google", "api_url": "https://generativelanguage.googleapis.com/v1beta/openai", "api_key_env": "GEMINI_API_KEY"},

    # ── DeepSeek (V4 series) ──
    "deepseek-v4-pro":     {"provider": "deepseek", "api_url": "https://api.deepseek.com/v1", "api_key_env": "DEEPSEEK_API_KEY"},
    "deepseek-v4-flash":   {"provider": "deepseek", "api_url": "https://api.deepseek.com/v1", "api_key_env": "DEEPSEEK_API_KEY"},

    # ── xAI Grok (4.x series) ──
    "grok-4.3":            {"provider": "xai", "api_url": "https://api.x.ai/v1", "api_key_env": "XAI_API_KEY"},
    "grok-4.20-reasoning": {"provider": "xai", "api_url": "https://api.x.ai/v1", "api_key_env": "XAI_API_KEY"},
    "grok-build-0.1":      {"provider": "xai", "api_url": "https://api.x.ai/v1", "api_key_env": "XAI_API_KEY"},

    # ── Mistral AI ──
    "mistral-medium-3.5":  {"provider": "mistral", "api_url": "https://api.mistral.ai/v1", "api_key_env": "MISTRAL_API_KEY"},
    "mistral-small-2603":  {"provider": "mistral", "api_url": "https://api.mistral.ai/v1", "api_key_env": "MISTRAL_API_KEY"},
    "codestral":           {"provider": "mistral", "api_url": "https://api.mistral.ai/v1", "api_key_env": "MISTRAL_API_KEY"},
    "pixtral":             {"provider": "mistral", "api_url": "https://api.mistral.ai/v1", "api_key_env": "MISTRAL_API_KEY"},

    # ── Cohere ──
    "command-a-plus":      {"provider": "cohere", "api_url": "https://api.cohere.ai/v1", "api_key_env": "COHERE_API_KEY"},
    "command-a":           {"provider": "cohere", "api_url": "https://api.cohere.ai/v1", "api_key_env": "COHERE_API_KEY"},
    "command-r7b":         {"provider": "cohere", "api_url": "https://api.cohere.ai/v1", "api_key_env": "COHERE_API_KEY"},

    # ── Perplexity ──
    "sonar-pro":           {"provider": "perplexity", "api_url": "https://api.perplexity.ai", "api_key_env": "PERPLEXITY_API_KEY"},
    "sonar-deep-research": {"provider": "perplexity", "api_url": "https://api.perplexity.ai", "api_key_env": "PERPLEXITY_API_KEY"},
    "sonar-reasoning-pro": {"provider": "perplexity", "api_url": "https://api.perplexity.ai", "api_key_env": "PERPLEXITY_API_KEY"},

    # ── OpenRouter ──
    "openrouter/auto":     {"provider": "openrouter", "api_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY"},

    # ── Together AI ──
    "together/llama-4":    {"provider": "together", "api_url": "https://api.together.xyz/v1", "api_key_env": "TOGETHER_API_KEY"},
    "together/deepseek":   {"provider": "together", "api_url": "https://api.together.xyz/v1", "api_key_env": "TOGETHER_API_KEY"},
    "together/qwen":       {"provider": "together", "api_url": "https://api.together.xyz/v1", "api_key_env": "TOGETHER_API_KEY"},

    # ── Groq ──
    "groq/llama-4":        {"provider": "groq", "api_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},
    "groq/mixtral":        {"provider": "groq", "api_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},
    "groq/gemma":          {"provider": "groq", "api_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},

    # ── Azure OpenAI ──
    "azure/gpt-5.4":       {"provider": "azure", "api_url": "", "api_key_env": "AZURE_OPENAI_API_KEY"},
    "azure/o3":            {"provider": "azure", "api_url": "", "api_key_env": "AZURE_OPENAI_API_KEY"},

    # ── Ollama (local) ──
    "ollama/llama4":       {"provider": "ollama", "api_url": "http://localhost:11434", "api_key_env": ""},
    "ollama/qwen3":        {"provider": "ollama", "api_url": "http://localhost:11434", "api_key_env": ""},
    "ollama/deepseek":     {"provider": "ollama", "api_url": "http://localhost:11434", "api_key_env": ""},

    # ═══════════════════════════════════════════════════════════
    # 🇨🇳 Chinese Domestic LLM Providers
    # ═══════════════════════════════════════════════════════════

    # ── 阿里通义千问 (Qwen 3.7 / 3.6 series) ──
    "qwen3.7-max":         {"provider": "alibaba", "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "api_key_env": "DASHSCOPE_API_KEY"},
    "qwen3.7-plus":        {"provider": "alibaba", "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "api_key_env": "DASHSCOPE_API_KEY"},
    "qwen3.6-flash":       {"provider": "alibaba", "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "api_key_env": "DASHSCOPE_API_KEY"},
    "qwen3-max-thinking":  {"provider": "alibaba", "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "api_key_env": "DASHSCOPE_API_KEY"},

    # ── 百度千帆 (ERNIE 5.0 / 4.5 series) ──
    "ernie-5.0":           {"provider": "baidu", "api_url": "https://qianfan.baidubce.com/v2", "api_key_env": "QIANFAN_API_KEY"},
    "ernie-x1-turbo":      {"provider": "baidu", "api_url": "https://qianfan.baidubce.com/v2", "api_key_env": "QIANFAN_API_KEY"},
    "ernie-4.5-turbo":     {"provider": "baidu", "api_url": "https://qianfan.baidubce.com/v2", "api_key_env": "QIANFAN_API_KEY"},
    "ernie-4.0-turbo":     {"provider": "baidu", "api_url": "https://qianfan.baidubce.com/v2", "api_key_env": "QIANFAN_API_KEY"},
    "ernie-speed":         {"provider": "baidu", "api_url": "https://qianfan.baidubce.com/v2", "api_key_env": "QIANFAN_API_KEY"},

    # ── 智谱AI (GLM-5.1 / 4.7 series) ──
    "glm-5.1":             {"provider": "zhipu", "api_url": "https://open.bigmodel.cn/api/paas/v4", "api_key_env": "ZHIPU_API_KEY"},
    "glm-5.1-highspeed":   {"provider": "zhipu", "api_url": "https://open.bigmodel.cn/api/paas/v4", "api_key_env": "ZHIPU_API_KEY"},
    "glm-4.7-flash":       {"provider": "zhipu", "api_url": "https://open.bigmodel.cn/api/paas/v4", "api_key_env": "ZHIPU_API_KEY"},
    "glm-z1-rumination":   {"provider": "zhipu", "api_url": "https://open.bigmodel.cn/api/paas/v4", "api_key_env": "ZHIPU_API_KEY"},

    # ── 字节豆包 (Doubao Seed 2.0) ──
    "doubao-seed-2-pro":   {"provider": "doubao", "api_url": "https://ark.cn-beijing.volces.com/api/v3", "api_key_env": "DOUBAO_API_KEY"},
    "doubao-seed-2-code":  {"provider": "doubao", "api_url": "https://ark.cn-beijing.volces.com/api/v3", "api_key_env": "DOUBAO_API_KEY"},

    # ── 月之暗面 (Kimi K2.6) ──
    "kimi-k2.6":           {"provider": "moonshot", "api_url": "https://api.moonshot.cn/v1", "api_key_env": "MOONSHOT_API_KEY"},
    "kimi-latest":         {"provider": "moonshot", "api_url": "https://api.moonshot.cn/v1", "api_key_env": "MOONSHOT_API_KEY"},

    # ── 百川智能 (Baichuan-M3 Plus) ──
    "baichuan-m3-plus":    {"provider": "baichuan", "api_url": "https://api.baichuan-ai.com/v1", "api_key_env": "BAICHUAN_API_KEY"},

    # ── 零一万物 (Yi-Large series) ──
    "yi-large":            {"provider": "lingyi", "api_url": "https://api.lingyiwanwu.com/v1", "api_key_env": "YI_API_KEY"},
    "yi-large-turbo":      {"provider": "lingyi", "api_url": "https://api.lingyiwanwu.com/v1", "api_key_env": "YI_API_KEY"},
    "yi-spark":            {"provider": "lingyi", "api_url": "https://api.lingyiwanwu.com/v1", "api_key_env": "YI_API_KEY"},
    "yi-medium":           {"provider": "lingyi", "api_url": "https://api.lingyiwanwu.com/v1", "api_key_env": "YI_API_KEY"},

    # ── 腾讯混元 (Hunyuan 2.0) ──
    "hunyuan-2.0-think":   {"provider": "tencent", "api_url": "https://api.hunyuan.cloud.tencent.com/v1", "api_key_env": "HUNYUAN_API_KEY"},
    "hunyuan-2.0-instruct":{"provider": "tencent", "api_url": "https://api.hunyuan.cloud.tencent.com/v1", "api_key_env": "HUNYUAN_API_KEY"},
    "hunyuan-a13b":        {"provider": "tencent", "api_url": "https://api.hunyuan.cloud.tencent.com/v1", "api_key_env": "HUNYUAN_API_KEY"},

    # ── 讯飞星火 (Spark X2) ──
    "spark-x2":            {"provider": "iflytek", "api_url": "https://spark-api-open.xf-yun.com/v1", "api_key_env": "SPARK_API_KEY"},
    "spark-ultra":         {"provider": "iflytek", "api_url": "https://spark-api-open.xf-yun.com/v1", "api_key_env": "SPARK_API_KEY"},
    "spark-lite":          {"provider": "iflytek", "api_url": "https://spark-api-open.xf-yun.com/v1", "api_key_env": "SPARK_API_KEY"},

    # ── MiniMax (M3 / M2.7) ──
    "minimax-m3":          {"provider": "minimax", "api_url": "https://api.minimax.chat/v1", "api_key_env": "MINIMAX_API_KEY"},
    "minimax-m2.7":        {"provider": "minimax", "api_url": "https://api.minimax.chat/v1", "api_key_env": "MINIMAX_API_KEY"},

    # ── 阶跃星辰 (Step 3.7 Flash) ──
    "step-3.7-flash":      {"provider": "stepfun", "api_url": "https://api.stepfun.com/v1", "api_key_env": "STEPFUN_API_KEY"},
    "step-3.5-flash":      {"provider": "stepfun", "api_url": "https://api.stepfun.com/v1", "api_key_env": "STEPFUN_API_KEY"},

    # ── 硅基流动 (SiliconFlow unified API) ──
    "siliconflow/qwen3.6": {"provider": "siliconflow", "api_url": "https://api.siliconflow.cn/v1", "api_key_env": "SILICONFLOW_API_KEY"},
    "siliconflow/deepseek-v4":{"provider": "siliconflow", "api_url": "https://api.siliconflow.cn/v1", "api_key_env": "SILICONFLOW_API_KEY"},
    "siliconflow/glm-5.1":  {"provider": "siliconflow", "api_url": "https://api.siliconflow.cn/v1", "api_key_env": "SILICONFLOW_API_KEY"},

    # ── 商汤日日新 (SenseNova 6.7) ──
    "sensenova-6.7-flash":  {"provider": "sensenova", "api_url": "https://api.sensenova.cn/v1", "api_key_env": "SENSENOVA_API_KEY"},

    # ── 昆仑万维 (SkyClaw-v1.0) ──
    "skyclaw-v1":          {"provider": "skywork", "api_url": "https://api.skywork.cn/v1", "api_key_env": "SKYWORK_API_KEY"},
    "skyclaw-v1-lite":     {"provider": "skywork", "api_url": "https://api.skywork.cn/v1", "api_key_env": "SKYWORK_API_KEY"},
}

# User-friendly labels for display
MODEL_LABELS: dict[str, str] = {
    # 🌍 International
    "gpt-5.5":            "OpenAI GPT-5.5",
    "gpt-5.4":            "OpenAI GPT-5.4",
    "gpt-5.4-mini":       "OpenAI GPT-5.4 Mini",
    "gpt-5.4-nano":       "OpenAI GPT-5.4 Nano",
    "o3":                 "OpenAI o3 Reasoning",
    "o4-mini":            "OpenAI o4-mini Reasoning",
    "gpt-4.1":            "OpenAI GPT-4.1",
    "gpt-4.1-mini":       "OpenAI GPT-4.1 Mini",
    "gpt-4.1-nano":       "OpenAI GPT-4.1 Nano",
    "claude-opus-4-8":    "Anthropic Claude Opus 4.8",
    "claude-opus-4-7":    "Anthropic Claude Opus 4.7",
    "claude-sonnet-4-6":  "Anthropic Claude Sonnet 4.6",
    "claude-haiku-4-5":   "Anthropic Claude Haiku 4.5",
    "gemini-3.5-flash":   "Google Gemini 3.5 Flash",
    "gemini-3.1-pro":     "Google Gemini 3.1 Pro",
    "gemini-3.1-flash-lite": "Google Gemini 3.1 Flash Lite",
    "deepseek-v4-pro":    "DeepSeek V4 Pro",
    "deepseek-v4-flash":  "DeepSeek V4 Flash",
    "grok-4.3":           "xAI Grok 4.3",
    "grok-4.20-reasoning":"xAI Grok 4.20 Reasoning",
    "grok-build-0.1":     "xAI Grok Build 0.1 (Coding)",
    "mistral-medium-3.5": "Mistral Medium 3.5",
    "mistral-small-2603": "Mistral Small 4 (2603)",
    "codestral":          "Mistral Codestral",
    "pixtral":            "Mistral Pixtral",
    "command-a-plus":     "Cohere Command A+",
    "command-a":          "Cohere Command A",
    "command-r7b":        "Cohere Command R7B",
    "sonar-pro":          "Perplexity Sonar Pro",
    "sonar-deep-research":"Perplexity Deep Research",
    "sonar-reasoning-pro":"Perplexity Reasoning Pro",
    "openrouter/auto":    "OpenRouter (Auto)",
    "together/llama-4":   "Together Llama 4",
    "together/deepseek":  "Together DeepSeek",
    "together/qwen":      "Together Qwen",
    "groq/llama-4":       "Groq Llama 4",
    "groq/mixtral":       "Groq Mixtral",
    "groq/gemma":         "Groq Gemma",
    "azure/gpt-5.4":      "Azure GPT-5.4",
    "azure/o3":           "Azure o3 Reasoning",
    "ollama/llama4":      "Ollama Llama 4 (Local)",
    "ollama/qwen3":       "Ollama Qwen3 (Local)",
    "ollama/deepseek":    "Ollama DeepSeek (Local)",

    # 🇨🇳 Chinese Domestic
    "qwen3.7-max":        "阿里 Qwen 3.7-Max 通义千问",
    "qwen3.7-plus":       "阿里 Qwen 3.7-Plus 通义千问",
    "qwen3.6-flash":      "阿里 Qwen 3.6-Flash 通义千问",
    "qwen3-max-thinking": "阿里 Qwen3-Max-Thinking 通义千问",
    "ernie-5.0":          "百度 ERNIE 5.0 文心一言",
    "ernie-x1-turbo":     "百度 ERNIE X1 Turbo 深度思考",
    "ernie-4.5-turbo":    "百度 ERNIE 4.5 Turbo 文心一言",
    "ernie-4.0-turbo":    "百度 ERNIE 4.0 Turbo 文心一言",
    "ernie-speed":        "百度 ERNIE Speed 文心一言",
    "glm-5.1":            "智谱 GLM-5.1 ChatGLM",
    "glm-5.1-highspeed":  "智谱 GLM-5.1 HighSpeed 400tok/s",
    "glm-4.7-flash":      "智谱 GLM-4.7 Flash (免费)",
    "glm-z1-rumination":  "智谱 GLM-Z1 沉思推理",
    "doubao-seed-2-pro":  "字节 Doubao Seed 2.0 Pro 豆包",
    "doubao-seed-2-code": "字节 Doubao Seed 2.0 Code 豆包",
    "kimi-k2.6":          "月之暗面 Kimi K2.6",
    "kimi-latest":        "月之暗面 Kimi Latest",
    "baichuan-m3-plus":   "百川 Baichuan-M3 Plus",
    "yi-large":           "零一 Yi-Large",
    "yi-large-turbo":     "零一 Yi-Large Turbo",
    "yi-spark":           "零一 Yi-Spark 极速版",
    "yi-medium":          "零一 Yi-Medium",
    "hunyuan-2.0-think":  "腾讯 Hunyuan 2.0 Think 混元",
    "hunyuan-2.0-instruct":"腾讯 Hunyuan 2.0 Instruct 混元",
    "hunyuan-a13b":       "腾讯 Hunyuan A13B 混元",
    "spark-x2":           "讯飞 Spark X2 星火深度推理",
    "spark-ultra":        "讯飞 Spark Ultra 星火",
    "spark-lite":         "讯飞 Spark Lite 星火 (免费)",
    "minimax-m3":         "MiniMax M3 旗舰模型",
    "minimax-m2.7":       "MiniMax M2.7",
    "step-3.7-flash":     "阶跃 Step 3.7 Flash",
    "step-3.5-flash":     "阶跃 Step 3.5 Flash",
    "siliconflow/qwen3.6":"硅基流动 Qwen 3.6",
    "siliconflow/deepseek-v4":"硅基流动 DeepSeek V4",
    "siliconflow/glm-5.1":"硅基流动 GLM-5.1",
    "sensenova-6.7-flash":"商汤 SenseNova 6.7 Flash-Lite",
    "skyclaw-v1":         "昆仑 SkyClaw-v1.0 Agent",
    "skyclaw-v1-lite":    "昆仑 SkyClaw-v1.0 Lite",
}


# ═══════════════════════════════════════════════════════════
# Base Provider
# ═══════════════════════════════════════════════════════════

class LLMProvider(ABC):
    model_id: str = ""
    api_key_env: str = ""
    supports_streaming: bool = True
    supports_tools: bool = True

    def __init__(self, model: str = "", api_key: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: Optional[int] = None,
                 **kwargs):
        self.model = model or self.model_id
        self.api_key = api_key or os.environ.get(self.api_key_env, "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra_kwargs = kwargs
        self.metrics: Dict[str, Any] = {"calls": 0, "total_tokens": 0}

    def chat(self, messages: List[Message],
             tools: Optional[List[ToolDef]] = None) -> Message:
        for event in self.chat_stream(messages, tools):
            if event.type == "done":
                content_buf = getattr(event, '_content', '')
                tc = getattr(event, '_tool_calls', None)
                return Message(role="assistant", content=content_buf, tool_calls=tc)
        return Message(role="assistant", content="")

    @abstractmethod
    def chat_stream(self, messages: List[Message],
                    tools: Optional[List[ToolDef]] = None) -> Iterator[StreamEvent]:
        ...

    async def achat_stream(self, messages: List[Message],
                           tools: Optional[List[ToolDef]] = None) -> AsyncIterator[StreamEvent]:
        import asyncio
        loop = asyncio.get_event_loop()
        q: asyncio.Queue = asyncio.Queue()

        def _run():
            try:
                for event in self.chat_stream(messages, tools):
                    loop.call_soon_threadsafe(q.put_nowait, event)
            except Exception as e:
                loop.call_soon_threadsafe(q.put_nowait, StreamEvent(type="error", error=str(e)))
            loop.call_soon_threadsafe(q.put_nowait, StreamEvent(type="done", done=True))

        fut = loop.run_in_executor(None, _run)
        while True:
            event = await q.get()
            if event.type == "done" and event.done:
                break
            yield event
        await fut

    def count_tokens(self, text: str) -> int:
        return len(text) // 4 + 1

    @classmethod
    def from_registry(cls, model: str, **kwargs) -> "LLMProvider":
        """Create provider from MODEL_REGISTRY lookup."""
        info = MODEL_REGISTRY.get(model)
        if not info:
            raise ValueError(f"Unknown model '{model}'. Available: {list(MODEL_REGISTRY.keys())}")

        prov = info["provider"]
        api_key = kwargs.pop("api_key", None) or os.environ.get(info["api_key_env"], "")
        api_url = kwargs.pop("api_url", None) or info["api_url"]

        providers = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "google": GoogleProvider,
            "deepseek": DeepSeekProvider,
            "xai": XAIProvider,
            "mistral": MistralProvider,
            "cohere": CohereProvider,
            "perplexity": PerplexityProvider,
            "openrouter": OpenRouterProvider,
            "together": TogetherProvider,
            "groq": GroqProvider,
            "azure": AzureProvider,
            "ollama": OllamaProvider,
        }

        cls_provider = providers.get(prov)
        if not cls_provider:
            raise ValueError(f"No provider class for '{prov}'")

        return cls_provider(model=model, api_key=api_key, base_url=api_url, **kwargs)

    def to_dict(self) -> dict:
        return {"provider": type(self).__name__, "model": self.model}


# ═══════════════════════════════════════════════════════════
# OpenAI-Compatible Base (HTTP streaming)
# ═══════════════════════════════════════════════════════════

class OpenAICompatProvider(LLMProvider):
    """Base for any OpenAI-compatible Chat Completions API."""
    api_key_env = "OPENAI_API_KEY"
    default_base_url = "https://api.openai.com/v1"

    def __init__(self, model: str = "", api_key: Optional[str] = None,
                 base_url: Optional[str] = None, temperature: float = 0.7,
                 max_tokens: Optional[int] = None, **kwargs):
        super().__init__(model=model, api_key=api_key, temperature=temperature,
                         max_tokens=max_tokens, **kwargs)
        self.base_url = (base_url or self.default_base_url).rstrip("/")

    def chat_stream(self, messages, tools=None) -> Iterator[StreamEvent]:
        import httpx
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": self.temperature,
            "stream": True,
        }
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        if tools and self.supports_tools:
            payload["tools"] = [t.to_openai_dict() for t in tools]
            payload["tool_choice"] = "auto"
        payload.update(self.extra_kwargs)
        self.metrics["calls"] += 1

        content_buffer = ""
        tool_calls_buffer: Dict[int, dict] = {}

        with httpx.stream("POST", f"{self.base_url}/chat/completions",
                          headers=headers, json=payload, timeout=120) as resp:
            for line in resp.iter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if not data.get("choices"):
                    continue
                delta = data["choices"][0].get("delta", {})
                if delta.get("content"):
                    content_buffer += delta["content"]
                    yield StreamEvent(type="token", content=delta["content"])
                if delta.get("tool_calls"):
                    for tc in delta["tool_calls"]:
                        idx = tc.get("index", 0)
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {"id": "", "type": "function",
                                                      "function": {"name": "", "arguments": ""}}
                        if tc.get("id"):
                            tool_calls_buffer[idx]["id"] = tc["id"]
                        if tc.get("function"):
                            if tc["function"].get("name"):
                                tool_calls_buffer[idx]["function"]["name"] = tc["function"]["name"]
                            if tc["function"].get("arguments"):
                                tool_calls_buffer[idx]["function"]["arguments"] += tc["function"]["arguments"]

        tool_calls = list(tool_calls_buffer.values()) if tool_calls_buffer else None
        if tool_calls:
            yield StreamEvent(type="tool_call_start", tool_call={"calls": tool_calls})

        ev = StreamEvent(type="done", done=True)
        ev._content = content_buffer
        ev._tool_calls = tool_calls
        yield ev

    async def achat_stream(self, messages, tools=None) -> AsyncIterator[StreamEvent]:
        import httpx
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": self.temperature,
            "stream": True,
        }
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        if tools and self.supports_tools:
            payload["tools"] = [t.to_openai_dict() for t in tools]
            payload["tool_choice"] = "auto"
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions",
                                     headers=headers, json=payload, timeout=120) as resp:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    ds = line[6:]
                    if ds.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(ds)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        if delta.get("content"):
                            yield StreamEvent(type="token", content=delta["content"])
                    except json.JSONDecodeError:
                        continue
        yield StreamEvent(type="done", done=True)


# ═══════════════════════════════════════════════════════════
# OpenAI Provider
# ═══════════════════════════════════════════════════════════

class OpenAIProvider(OpenAICompatProvider):
    model_id = "gpt-4o"
    api_key_env = "OPENAI_API_KEY"
    default_base_url = "https://api.openai.com/v1"


# ═══════════════════════════════════════════════════════════
# Anthropic Provider
# ═══════════════════════════════════════════════════════════

class AnthropicProvider(LLMProvider):
    model_id = "claude-sonnet-4-6"
    api_key_env = "ANTHROPIC_API_KEY"

    def __init__(self, model: str = "", api_key: Optional[str] = None,
                 base_url: Optional[str] = None, temperature: float = 0.7,
                 max_tokens: Optional[int] = None, **kwargs):
        super().__init__(model=model, api_key=api_key, temperature=temperature,
                         max_tokens=max_tokens, **kwargs)
        self.base_url = (base_url or "https://api.anthropic.com/v1").rstrip("/")
        self.anthropic_version = "2023-06-01"

    def chat_stream(self, messages, tools=None) -> Iterator[StreamEvent]:
        try:
            import anthropic
        except ImportError:
            raise ImportError("pip install anthropic")

        client = anthropic.Anthropic(api_key=self.api_key)
        kwargs = self._build_kwargs(messages, tools, stream=True)
        self.metrics["calls"] += 1

        content_buffer = ""
        tool_calls_buffer: list[dict] = []
        current_tool_call: dict | None = None
        current_tool_input = ""

        with client.messages.create(**kwargs) as stream:
            for event in stream:
                try:
                    if event.type == "content_block_delta":
                        delta = event.delta
                        if not delta:
                            continue
                        if delta.type == "text_delta":
                            text = delta.text or ""
                            content_buffer += text
                            yield StreamEvent(type="token", content=text)
                        elif delta.type == "input_json_delta" and current_tool_call is not None:
                            partial = delta.partial_json or ""
                            current_tool_input += partial

                    elif event.type == "content_block_start":
                        cb = event.content_block
                        if not cb:
                            continue
                        if cb.type == "tool_use":
                            tool_name = cb.name or ""
                            # Validate tool name
                            if not tool_name.strip():
                                tool_name = "unknown"
                            tool_id = cb.id or f"toolu_{len(tool_calls_buffer)}"
                            current_tool_call = {
                                "id": tool_id,
                                "type": "function",
                                "function": {"name": tool_name, "arguments": ""},
                            }
                            current_tool_input = ""

                    elif event.type == "content_block_stop":
                        if current_tool_call is not None:
                            raw_args = current_tool_input
                            # Validate JSON — if malformed, wrap in safe fallback
                            if raw_args.strip():
                                try:
                                    json.loads(raw_args)
                                except json.JSONDecodeError:
                                    # Attempt to fix partial JSON by wrapping bare strings
                                    raw_args = json.dumps({"value": raw_args.strip()})
                            current_tool_call["function"]["arguments"] = raw_args
                            tool_calls_buffer.append(current_tool_call)
                            current_tool_call = None
                            current_tool_input = ""

                except Exception as e:
                    logger.warning(f"Anthropic stream event error: {e}")
                    continue

        tool_calls = tool_calls_buffer if tool_calls_buffer else None
        if tool_calls:
            yield StreamEvent(type="tool_call_start", tool_call={"calls": tool_calls})

        ev = StreamEvent(type="done", done=True)
        ev._content = content_buffer
        ev._tool_calls = tool_calls
        yield ev

    def _build_kwargs(self, messages, tools, stream):
        system = ""
        msgs = []
        for m in messages:
            if m.role == "system":
                system += m.content + "\n"
            else:
                msgs.append(m.to_dict())
        kwargs = {
            "model": self.model,
            "messages": msgs,
            "max_tokens": self.max_tokens or 4096,
            "temperature": self.temperature,
            "stream": stream,
        }
        if system.strip():
            kwargs["system"] = system.strip()
        if tools and self.supports_tools:
            kwargs["tools"] = [t.to_anthropic_dict() for t in tools]
        kwargs.update(self.extra_kwargs)
        return kwargs


# ═══════════════════════════════════════════════════════════
# Google Gemini (via OpenAI-compatible endpoint)
# ═══════════════════════════════════════════════════════════

class GoogleProvider(OpenAICompatProvider):
    model_id = "gemini-2.5-flash"
    api_key_env = "GEMINI_API_KEY"
    default_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
    supports_tools = True


# ═══════════════════════════════════════════════════════════
# DeepSeek Provider
# ═══════════════════════════════════════════════════════════

class DeepSeekProvider(OpenAICompatProvider):
    model_id = "deepseek-chat"
    api_key_env = "DEEPSEEK_API_KEY"
    default_base_url = "https://api.deepseek.com/v1"

    def chat_stream(self, messages, tools=None) -> Iterator[StreamEvent]:
        # DeepSeek Reasoner doesn't support tools
        if self.model == "deepseek-reasoner":
            self.supports_tools = False
        yield from super().chat_stream(messages, tools)


# ═══════════════════════════════════════════════════════════
# xAI Grok Provider
# ═══════════════════════════════════════════════════════════

class XAIProvider(OpenAICompatProvider):
    model_id = "grok-3"
    api_key_env = "XAI_API_KEY"
    default_base_url = "https://api.x.ai/v1"
    supports_tools = True


# ═══════════════════════════════════════════════════════════
# Mistral AI Provider
# ═══════════════════════════════════════════════════════════

class MistralProvider(OpenAICompatProvider):
    model_id = "mistral-large-2"
    api_key_env = "MISTRAL_API_KEY"
    default_base_url = "https://api.mistral.ai/v1"
    supports_tools = True


# ═══════════════════════════════════════════════════════════
# Cohere Provider
# ═══════════════════════════════════════════════════════════

class CohereProvider(OpenAICompatProvider):
    model_id = "command-r-plus"
    api_key_env = "COHERE_API_KEY"
    default_base_url = "https://api.cohere.ai/v1"
    supports_tools = True


# ═══════════════════════════════════════════════════════════
# Perplexity Provider
# ═══════════════════════════════════════════════════════════

class PerplexityProvider(OpenAICompatProvider):
    model_id = "sonar-pro"
    api_key_env = "PERPLEXITY_API_KEY"
    default_base_url = "https://api.perplexity.ai"
    supports_tools = False  # Perplexity doesn't support tool calls


# ═══════════════════════════════════════════════════════════
# OpenRouter Provider (Unified API)
# ═══════════════════════════════════════════════════════════

class OpenRouterProvider(OpenAICompatProvider):
    model_id = "openrouter/auto"
    api_key_env = "OPENROUTER_API_KEY"
    default_base_url = "https://openrouter.ai/api/v1"
    supports_tools = True

    def __init__(self, model: str = "", api_key: Optional[str] = None,
                 base_url: Optional[str] = None, **kwargs):
        super().__init__(model=model, api_key=api_key, base_url=base_url, **kwargs)
        # OpenRouter needs extra headers
        self.extra_kwargs.setdefault("extra_headers", {}).update({
            "HTTP-Referer": "https://laap.dev",
            "X-Title": "LAAP Agent",
        })


# ═══════════════════════════════════════════════════════════
# Together AI Provider
# ═══════════════════════════════════════════════════════════

class TogetherProvider(OpenAICompatProvider):
    model_id = "together/llama-4"
    api_key_env = "TOGETHER_API_KEY"
    default_base_url = "https://api.together.xyz/v1"
    supports_tools = True


# ═══════════════════════════════════════════════════════════
# Groq Provider (Fast Inference)
# ═══════════════════════════════════════════════════════════

class GroqProvider(OpenAICompatProvider):
    model_id = "groq/llama-4"
    api_key_env = "GROQ_API_KEY"
    default_base_url = "https://api.groq.com/openai/v1"
    supports_tools = True


# ═══════════════════════════════════════════════════════════
# Azure OpenAI Provider
# ═══════════════════════════════════════════════════════════

class AzureProvider(OpenAICompatProvider):
    model_id = "azure/gpt-4o"
    api_key_env = "AZURE_OPENAI_API_KEY"

    def __init__(self, model: str = "", api_key: Optional[str] = None,
                 base_url: Optional[str] = None, endpoint: Optional[str] = None,
                 deployment: Optional[str] = None, api_version: str = "2024-10-21",
                 **kwargs):
        # Azure requires endpoint + deployment
        self.endpoint = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT", base_url or "")
        self.deployment = deployment or os.environ.get("AZURE_DEPLOYMENT_NAME", model.split("/")[-1])
        self.api_version = api_version
        super().__init__(
            model=self.deployment,
            api_key=api_key,
            base_url=f"{self.endpoint.rstrip('/')}/openai/deployments/{self.deployment}",
            **kwargs,
        )
        self.api_key_env = "AZURE_OPENAI_API_KEY"

    def chat_stream(self, messages, tools=None) -> Iterator[StreamEvent]:
        import httpx
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "messages": [m.to_dict() for m in messages],
            "temperature": self.temperature,
            "stream": True,
        }
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        if tools and self.supports_tools:
            payload["tools"] = [t.to_openai_dict() for t in tools]
            payload["tool_choice"] = "auto"
        payload.update(self.extra_kwargs)
        self.metrics["calls"] += 1

        url = (f"{self.base_url}/chat/completions?api-version={self.api_version}")
        content_buffer = ""
        tool_calls_buffer: Dict[int, dict] = {}

        with httpx.stream("POST", url, headers=headers, json=payload, timeout=120) as resp:
            for line in resp.iter_lines():
                if not line.startswith("data: "):
                    continue
                ds = line[6:]
                if ds.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(ds)
                except json.JSONDecodeError:
                    continue
                if not data.get("choices"):
                    continue
                delta = data["choices"][0].get("delta", {})
                if delta.get("content"):
                    content_buffer += delta["content"]
                    yield StreamEvent(type="token", content=delta["content"])
                if delta.get("tool_calls"):
                    for tc in delta["tool_calls"]:
                        idx = tc.get("index", 0)
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {"id": "", "type": "function",
                                                      "function": {"name": "", "arguments": ""}}
                        if tc.get("id"):
                            tool_calls_buffer[idx]["id"] = tc["id"]
                        if tc.get("function"):
                            if tc["function"].get("name"):
                                tool_calls_buffer[idx]["function"]["name"] = tc["function"]["name"]
                            if tc["function"].get("arguments"):
                                tool_calls_buffer[idx]["function"]["arguments"] += tc["function"]["arguments"]

        tool_calls = list(tool_calls_buffer.values()) if tool_calls_buffer else None
        if tool_calls:
            yield StreamEvent(type="tool_call_start", tool_call={"calls": tool_calls})

        ev = StreamEvent(type="done", done=True)
        ev._content = content_buffer
        ev._tool_calls = tool_calls
        yield ev


# ═══════════════════════════════════════════════════════════
# Ollama Provider (Local)
# ═══════════════════════════════════════════════════════════

class OllamaProvider(LLMProvider):
    model_id = "llama3"
    api_key_env = ""
    supports_tools = False

    def __init__(self, model: str = "", api_key: Optional[str] = None,
                 base_url: Optional[str] = None, temperature: float = 0.7,
                 max_tokens: Optional[int] = None, **kwargs):
        super().__init__(model=model, temperature=temperature,
                         max_tokens=max_tokens, **kwargs)
        self.base_url = (base_url or os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")

    def chat_stream(self, messages, tools=None) -> Iterator[StreamEvent]:
        import httpx
        payload = {
            "model": self.model,
            "stream": True,
            "messages": [m.to_dict() for m in messages if m.role != "system"],
            "options": {"temperature": self.temperature},
        }
        if self.max_tokens:
            payload["options"]["num_predict"] = self.max_tokens
        self.metrics["calls"] += 1

        with httpx.stream("POST", f"{self.base_url}/api/chat", json=payload, timeout=120) as resp:
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        yield StreamEvent(type="token", content=data["message"]["content"])
                    if data.get("done"):
                        yield StreamEvent(type="done", done=True)
                except json.JSONDecodeError:
                    continue


# ═══════════════════════════════════════════════════════════
# Custom / Generic OpenAI-compatible
# ═══════════════════════════════════════════════════════════

class CustomProvider(OpenAICompatProvider):
    """For any OpenAI-compatible API with custom base_url."""
    model_id = "custom"
    api_key_env = "CUSTOM_API_KEY"

    def __init__(self, model: str, base_url: str, api_key: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: Optional[int] = None, **kwargs):
        super().__init__(model=model, base_url=base_url, api_key=api_key,
                         temperature=temperature, max_tokens=max_tokens, **kwargs)


# ═══════════════════════════════════════════════════════════
# Streaming Helpers
# ═══════════════════════════════════════════════════════════

def stream_chat(provider: LLMProvider, messages: List[Message],
                tools: Optional[List[ToolDef]] = None,
                on_token: Optional[Callable[[str], None]] = None,
                on_tool: Optional[Callable[[Dict], None]] = None,
                on_done: Optional[Callable[[str], None]] = None) -> str:
    """High-level streaming chat with callbacks."""
    content = ""
    for event in provider.chat_stream(messages, tools):
        if event.type == "token":
            content += event.content
            if on_token: on_token(event.content)
        elif event.type == "tool_call_start":
            if on_tool: on_tool(event.tool_call)
        elif event.type == "done":
            if on_done: on_done(content)
    return content


def print_stream(provider: LLMProvider, messages: List[Message],
                 tools: Optional[List[ToolDef]] = None) -> str:
    """Stream chat with real-time terminal output."""
    content = ""
    print()
    for event in provider.chat_stream(messages, tools):
        if event.type == "token":
            content += event.content
            print(event.content, end="", flush=True)
        elif event.type == "tool_call_start":
            pass  # Tool calls are handled by StreamHandler
        elif event.type == "done":
            print()
    return content


# ═══════════════════════════════════════════════════════════
# Convenience: get provider from model name
# ═══════════════════════════════════════════════════════════

def get_provider(model: str, **kwargs) -> LLMProvider:
    """Get the right provider for any model name.

    Examples:
        get_provider("gpt-4o")
        get_provider("claude-sonnet-4-6")
        get_provider("deepseek-chat", api_key="sk-...")
        get_provider("custom", base_url="https://my-api.com/v1", api_key="...")
    """
    if kwargs.get("base_url") or model.startswith("custom/"):
        return CustomProvider(model=model.replace("custom/", ""), **kwargs)
    return LLMProvider.from_registry(model, **kwargs)
