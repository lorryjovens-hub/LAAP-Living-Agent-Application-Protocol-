"""
LAAP — LLM 工厂与模型管理

统一管理所有主流 LLM 提供商实例，支持自动发现、配置回退、模型路由。
内置 2026 年全部主流模型的 API URL、模型 ID、认证方式。
"""

from __future__ import annotations
import os, logging
from typing import Dict, List, Optional, Type, Any, Union

from laap.llm.provider import (
    LLMProvider, OpenAIProvider, AnthropicProvider,
    DeepSeekProvider, XAIProvider, MistralProvider,
    CohereProvider, PerplexityProvider, OpenRouterProvider,
    TogetherProvider, GroqProvider, GoogleProvider,
    AzureProvider, OllamaProvider, CustomProvider,
    OpenAICompatProvider,
    Message, ToolDef, MODEL_REGISTRY, MODEL_LABELS,
)

logger = logging.getLogger("laap.llm.factory")


# ── Provider class mapping ──
PROVIDER_CLASSES: Dict[str, Type[LLMProvider]] = {
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
    # 🇨🇳 Chinese Domestic Providers (all OpenAI-compatible)
    "alibaba": OpenAICompatProvider,
    "baidu": OpenAICompatProvider,
    "zhipu": OpenAICompatProvider,
    "doubao": OpenAICompatProvider,
    "moonshot": OpenAICompatProvider,
    "baichuan": OpenAICompatProvider,
    "lingyi": OpenAICompatProvider,
    "tencent": OpenAICompatProvider,
    "iflytek": OpenAICompatProvider,
    "minimax": OpenAICompatProvider,
    "stepfun": OpenAICompatProvider,
    "siliconflow": OpenAICompatProvider,
    "sensenova": OpenAICompatProvider,
    "skywork": OpenAICompatProvider,
}


# ── API Key env vars per provider ──
PROVIDER_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "xai": "XAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cohere": "COHERE_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "together": "TOGETHER_API_KEY",
    "groq": "GROQ_API_KEY",
    "azure": "AZURE_OPENAI_API_KEY",
    # 🇨🇳 Chinese Domestic
    "alibaba": "DASHSCOPE_API_KEY",
    "baidu": "QIANFAN_API_KEY",
    "zhipu": "ZHIPU_API_KEY",
    "doubao": "DOUBAO_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "baichuan": "BAICHUAN_API_KEY",
    "lingyi": "YI_API_KEY",
    "tencent": "HUNYUAN_API_KEY",
    "iflytek": "SPARK_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "stepfun": "STEPFUN_API_KEY",
    "siliconflow": "SILICONFLOW_API_KEY",
    "sensenova": "SENSENOVA_API_KEY",
    "skywork": "SKYWORK_API_KEY",
}


class LLMFactory:
    """LLM 工厂：管理多提供商、自动发现、模型路由"""

    def __init__(self, default_provider: str = "openai",
                 default_model: Optional[str] = None):
        self.default_provider = default_provider
        self.default_model = default_model
        self.provider_registry: Dict[str, Type[LLMProvider]] = dict(PROVIDER_CLASSES)
        self.instances: Dict[str, LLMProvider] = {}
        self._auto_detect()

    def _auto_detect(self):
        """Auto-detect available API keys and pre-initialize providers."""

        # 1. LAAP_* env vars override everything
        laap_provider = os.environ.get("LAAP_PROVIDER", "").lower()
        laap_key = os.environ.get("LAAP_API_KEY", "")
        laap_base = os.environ.get("LAAP_BASE_URL", "")
        laap_model = os.environ.get("LAAP_MODEL", "")

        if laap_provider and laap_key:
            self._init_laap_config(laap_provider, laap_key, laap_base, laap_model)
            return

        # 2. Auto-detect by checking API keys
        for prov_name, key_env in PROVIDER_KEY_ENV.items():
            key = os.environ.get(key_env, "")
            if key:
                try:
                    model = os.environ.get(
                        f"{prov_name.upper()}_MODEL",
                        self._default_model_for(prov_name),
                    )
                    cls = self.provider_registry[prov_name]
                    self.instances[prov_name] = cls(model=model, api_key=key)
                    logger.info(f"已发现 {prov_name}: {model}")
                except Exception as e:
                    logger.debug(f"初始化 {prov_name} 失败: {e}")

        # 3. Fallback: create default provider even without key
        if self.default_provider not in self.instances:
            cls = self.provider_registry.get(self.default_provider)
            if cls:
                model = (self.default_model or
                         self._default_model_for(self.default_provider))
                self.instances[self.default_provider] = cls(model=model)

    def _init_laap_config(self, provider: str, api_key: str,
                          base_url: str, model: str):
        """Initialize from LAAP_* unified config vars."""
        if provider in self.provider_registry:
            cls = self.provider_registry[provider]
            model_name = model or self._default_model_for(provider)
            if base_url:
                self.instances[provider] = cls(
                    model=model_name, api_key=api_key, base_url=base_url,
                )
            else:
                self.instances[provider] = cls(
                    model=model_name, api_key=api_key,
                )
        else:
            # Custom provider
            model_name = model or "gpt-4o"
            self.instances[provider] = CustomProvider(
                model=model_name, base_url=base_url or "https://api.openai.com/v1",
                api_key=api_key,
            )
        logger.info(f"已配置: {provider} ({model_name})")

    def _default_model_for(self, provider: str) -> str:
        """Get the recommended default model for a provider."""
        defaults = {
            "openai": "gpt-4o",
            "anthropic": "claude-sonnet-4-6",
            "google": "gemini-2.5-flash",
            "deepseek": "deepseek-chat",
            "xai": "grok-3",
            "mistral": "mistral-large-2",
            "cohere": "command-r-plus",
            "perplexity": "sonar-pro",
            "openrouter": "openrouter/auto",
            "together": "together/llama-4",
            "groq": "groq/llama-4",
            "azure": "azure/gpt-4o",
            "ollama": "llama3",
            # 🇨🇳 Chinese Domestic
            "alibaba": "qwen-max",
            "baidu": "ernie-4.5",
            "zhipu": "glm-4-plus",
            "doubao": "doubao-pro-32k",
            "moonshot": "kimi-k2",
            "baichuan": "baichuan4-turbo",
            "lingyi": "yi-lightning",
            "tencent": "hunyuan-turbo",
            "iflytek": "spark-4.0",
            "minimax": "minimax-text-01",
            "stepfun": "step-2",
            "siliconflow": "siliconflow/qwen",
            "sensenova": "sensechat-6",
            "skywork": "skywork-2",
        }
        return defaults.get(provider, "gpt-4o")

    def register_provider(self, name: str, provider_cls: Type[LLMProvider]):
        """Register a custom provider class."""
        self.provider_registry[name] = provider_cls

    def get(self, name: Optional[str] = None,
            model: Optional[str] = None,
            temperature: float = 0.7,
            **kwargs) -> LLMProvider:
        """Get a provider instance by name or model."""
        name = name or self.default_provider

        # If model is in registry, use its provider
        if model and model in MODEL_REGISTRY:
            info = MODEL_REGISTRY[model]
            name = info["provider"]
            api_key = kwargs.pop("api_key", None) or os.environ.get(info["api_key_env"], "")
            cls = self.provider_registry.get(name)
            if cls:
                return cls(
                    model=model, api_key=api_key,
                    base_url=kwargs.pop("base_url", None) or info["api_url"],
                    temperature=temperature, **kwargs,
                )

        # Return cached instance if parameters match
        if name in self.instances and model is None and temperature == 0.7 and not kwargs:
            return self.instances[name]

        # Create new instance
        cls = self.provider_registry.get(name)
        if not cls:
            raise ValueError(
                f"未知提供商: {name}。可用: {list(self.provider_registry.keys())}"
            )

        if model:
            return cls(model=model, temperature=temperature, **kwargs)
        if name in self.instances:
            return self.instances[name]
        raise ValueError(f"提供商 {name} 未初始化（请设置 API Key）")

    def chat(self, messages: List[Message],
             tools: Optional[List[ToolDef]] = None,
             provider: Optional[str] = None,
             fallbacks: Optional[List[str]] = None,
             **kwargs) -> Union[Message, Any]:
        """Chat with automatic fallback across providers."""
        provider = provider or self.default_provider
        fallbacks = fallbacks or []
        all_providers = [provider] + fallbacks
        last_error = None

        for pname in all_providers:
            try:
                llm = self.get(pname, **kwargs)
                return llm.chat(messages, tools=tools)
            except Exception as e:
                logger.warning(f"提供者 {pname} 失败: {e}")
                last_error = e
                continue
        raise RuntimeError(f"所有提供商均失败: {last_error}")

    def list_models(self) -> List[Dict[str, str]]:
        """List all available models with labels."""
        return [
            {"id": mid, "label": MODEL_LABELS.get(mid, mid), "provider": info["provider"]}
            for mid, info in MODEL_REGISTRY.items()
        ]

    def list_available(self) -> List[str]:
        """List providers with configured API keys."""
        return list(self.instances.keys())

    @property
    def available(self) -> List[str]:
        return self.list_available()

    def to_dict(self) -> dict:
        return {
            "default": self.default_provider,
            "default_model": self.default_model,
            "available": self.available,
            "instances": {k: v.to_dict() for k, v in self.instances.items()},
            "total_models_in_registry": len(MODEL_REGISTRY),
        }


# Global factory instance
factory = LLMFactory()
