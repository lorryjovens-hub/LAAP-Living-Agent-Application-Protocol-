"""
LAAP — Configuration Manager
API 配置管理：多提供商、自定义 URL、持久化、即时生效
"""

from __future__ import annotations
import os, json, sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from pathlib import Path

# Config file locations
CONFIG_DIR = Path.home() / ".laap"
CONFIG_FILE = CONFIG_DIR / "config.json"
ENV_FILE = Path.home() / ".laap.env"

DEFAULT_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
        "models": "gpt-4o, gpt-4o-mini, o3, o4-mini, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano",
        "docs": "https://platform.openai.com/api-keys",
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "base_url": "https://api.anthropic.com/v1",
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-6",
        "models": "claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5, claude-3-5-sonnet, claude-3-opus",
        "docs": "https://console.anthropic.com/settings/keys",
    },
    "google": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
        "models": "gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash",
        "docs": "https://aistudio.google.com/app/apikey",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "models": "deepseek-chat (V3), deepseek-reasoner (R1)",
        "docs": "https://platform.deepseek.com/api_keys",
    },
    "xai": {
        "name": "xAI Grok",
        "base_url": "https://api.x.ai/v1",
        "env_key": "XAI_API_KEY",
        "default_model": "grok-3",
        "models": "grok-3, grok-3-mini",
        "docs": "https://console.x.ai",
    },
    "mistral": {
        "name": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "env_key": "MISTRAL_API_KEY",
        "default_model": "mistral-large-2",
        "models": "mistral-large-2, mistral-small-3, codestral, pixtral, ministral-8b",
        "docs": "https://console.mistral.ai/api-keys",
    },
    "cohere": {
        "name": "Cohere",
        "base_url": "https://api.cohere.ai/v1",
        "env_key": "COHERE_API_KEY",
        "default_model": "command-r-plus",
        "models": "command-r-plus, command-r, command-a",
        "docs": "https://dashboard.cohere.com/api-keys",
    },
    "perplexity": {
        "name": "Perplexity",
        "base_url": "https://api.perplexity.ai",
        "env_key": "PERPLEXITY_API_KEY",
        "default_model": "sonar-pro",
        "models": "sonar-pro, sonar-reasoning, sonar",
        "docs": "https://docs.perplexity.ai",
    },
    "openrouter": {
        "name": "OpenRouter (200+ models)",
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "default_model": "openrouter/auto",
        "models": "Any model via openrouter.ai",
        "docs": "https://openrouter.ai/keys",
    },
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "env_key": "TOGETHER_API_KEY",
        "default_model": "together/llama-4",
        "models": "Llama 4, DeepSeek, Qwen, Mistral, etc.",
        "docs": "https://api.together.xyz/settings/api-keys",
    },
    "groq": {
        "name": "Groq (Fast Inference)",
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "default_model": "groq/llama-4",
        "models": "Llama 4, Mixtral, Gemma, etc.",
        "docs": "https://console.groq.com/keys",
    },
    "azure": {
        "name": "Azure OpenAI",
        "base_url": "",
        "env_key": "AZURE_OPENAI_API_KEY",
        "default_model": "azure/gpt-4o",
        "models": "Any Azure deployment",
        "docs": "https://portal.azure.com",
    },
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434",
        "env_key": "",
        "default_model": "llama3",
        "models": "Any local model (llama3, qwen, deepseek, etc.)",
        "docs": "https://ollama.ai/download",
    },

    # 🇨🇳 阿里通义千问
    "alibaba": {
        "name": "阿里通义千问 (Qwen)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_key": "DASHSCOPE_API_KEY",
        "default_model": "qwen-max",
        "models": "qwen-max, qwen-plus, qwen-turbo, qwen3, qwen2.5-72b",
        "docs": "https://help.aliyun.com/zh/model-studio/",
    },
    # 🇨🇳 百度千帆
    "baidu": {
        "name": "百度千帆 (ERNIE)",
        "base_url": "https://qianfan.baidubce.com/v2",
        "env_key": "QIANFAN_API_KEY",
        "default_model": "ernie-4.5",
        "models": "ernie-4.5, ernie-4.0, ernie-3.5, ernie-speed",
        "docs": "https://console.bce.baidu.com/qianfan/",
    },
    # 🇨🇳 智谱AI
    "zhipu": {
        "name": "智谱AI (GLM/ChatGLM)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "env_key": "ZHIPU_API_KEY",
        "default_model": "glm-4-plus",
        "models": "glm-5, glm-4-plus, glm-4, glm-4-flash",
        "docs": "https://open.bigmodel.cn/usercenter/apikeys",
    },
    # 🇨🇳 字节豆包
    "doubao": {
        "name": "字节豆包 (Doubao)",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "env_key": "DOUBAO_API_KEY",
        "default_model": "doubao-pro-32k",
        "models": "doubao-pro-32k, doubao-pro-128k, doubao-lite-32k, doubao-1.5-pro",
        "docs": "https://console.volcengine.com/ark/",
    },
    # 🇨🇳 月之暗面
    "moonshot": {
        "name": "月之暗面 (Kimi)",
        "base_url": "https://api.moonshot.cn/v1",
        "env_key": "MOONSHOT_API_KEY",
        "default_model": "kimi-k2",
        "models": "kimi-k2, kimi-k2.5, moonshot-v1-8k, moonshot-v1-32k",
        "docs": "https://platform.moonshot.cn/console/api-keys",
    },
    # 🇨🇳 百川智能
    "baichuan": {
        "name": "百川智能 (Baichuan)",
        "base_url": "https://api.baichuan-ai.com/v1",
        "env_key": "BAICHUAN_API_KEY",
        "default_model": "baichuan4-turbo",
        "models": "baichuan4-turbo, baichuan4, baichuan3",
        "docs": "https://platform.baichuan-ai.com/console/apikey",
    },
    # 🇨🇳 零一万物
    "lingyi": {
        "name": "零一万物 (01.AI Yi)",
        "base_url": "https://api.lingyiwanwu.com/v1",
        "env_key": "YI_API_KEY",
        "default_model": "yi-lightning",
        "models": "yi-lightning, yi-large, yi-medium",
        "docs": "https://platform.lingyiwanwu.com/apikeys",
    },
    # 🇨🇳 腾讯混元
    "tencent": {
        "name": "腾讯混元 (Hunyuan)",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "env_key": "HUNYUAN_API_KEY",
        "default_model": "hunyuan-turbo",
        "models": "hunyuan-turbo, hunyuan-pro, hunyuan-standard",
        "docs": "https://console.cloud.tencent.com/hunyuan",
    },
    # 🇨🇳 讯飞星火
    "iflytek": {
        "name": "讯飞星火 (Spark)",
        "base_url": "https://spark-api-open.xf-yun.com/v1",
        "env_key": "SPARK_API_KEY",
        "default_model": "spark-4.0",
        "models": "spark-4.0, spark-3.5, spark-3.0",
        "docs": "https://console.xfyun.cn/services/bm3",
    },
    # 🇨🇳 MiniMax
    "minimax": {
        "name": "MiniMax",
        "base_url": "https://api.minimax.chat/v1",
        "env_key": "MINIMAX_API_KEY",
        "default_model": "minimax-text-01",
        "models": "minimax-text-01, minimax-pro",
        "docs": "https://platform.minimax.chat/user-center/api-key",
    },
    # 🇨🇳 阶跃星辰
    "stepfun": {
        "name": "阶跃星辰 (StepFun)",
        "base_url": "https://api.stepfun.com/v1",
        "env_key": "STEPFUN_API_KEY",
        "default_model": "step-2",
        "models": "step-2, step-1, step-1-flash",
        "docs": "https://platform.stepfun.com/",
    },
    # 🇨🇳 硅基流动
    "siliconflow": {
        "name": "硅基流动 (SiliconFlow)",
        "base_url": "https://api.siliconflow.cn/v1",
        "env_key": "SILICONFLOW_API_KEY",
        "default_model": "siliconflow/qwen",
        "models": "Qwen, DeepSeek, GLM, Yi 等",
        "docs": "https://cloud.siliconflow.cn/account/ak",
    },
    # 🇨🇳 商汤日日新
    "sensenova": {
        "name": "商汤日日新 (SenseNova)",
        "base_url": "https://api.sensenova.cn/v1",
        "env_key": "SENSENOVA_API_KEY",
        "default_model": "sensechat-6",
        "models": "sensechat-6, sensechat-5.5",
        "docs": "https://console.sensenova.cn/home",
    },
    # 🇨🇳 昆仑万维
    "skywork": {
        "name": "昆仑万维 (Skywork)",
        "base_url": "https://api.skywork.cn/v1",
        "env_key": "SKYWORK_API_KEY",
        "default_model": "skywork-2",
        "models": "skywork-2, skywork-moe",
        "docs": "https://platform.skywork.cn/",
    },
}


@dataclass
class ProviderConfig:
    """单个提供商配置"""
    name: str = ""
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    custom: bool = False  # True if user-defined custom provider


@dataclass
class LAAPConfig:
    """全局 LAAP 配置"""
    active_provider: str = "openai"
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    first_run: bool = True

    def to_dict(self) -> dict:
        return {
            "active_provider": self.active_provider,
            "providers": {k: asdict(v) for k, v in self.providers.items()},
            "first_run": self.first_run,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LAAPConfig":
        cfg = cls()
        cfg.active_provider = d.get("active_provider", "openai")
        cfg.first_run = d.get("first_run", True)
        for k, v in d.get("providers", {}).items():
            cfg.providers[k] = ProviderConfig(**v)
        return cfg


class ConfigManager:
    """管理所有 LLM API 配置"""

    def __init__(self):
        self.config = LAAPConfig()
        self._env_loaded = False
        self._load()

    def _load(self):
        """Load config from disk"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Load JSON config
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                self.config = LAAPConfig.from_dict(data)
            except (json.JSONDecodeError, Exception):
                self.config = LAAPConfig()

        # Load env vars (highest priority)
        self._load_env_file()
        self._load_env_vars()

    def _load_env_file(self):
        """Load ~/.laap.env"""
        if ENV_FILE.exists():
            with open(ENV_FILE, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        if not os.environ.get(k):
                            os.environ[k] = v

    def _load_env_vars(self):
        """Detect API keys from environment variables"""
        for provider_id, info in DEFAULT_PROVIDERS.items():
            env_key = info["env_key"]
            api_key = os.environ.get(env_key, "")
            base_url = os.environ.get(f"{env_key}_BASE_URL", info["base_url"])
            model = os.environ.get(f"{env_key}_MODEL", info["default_model"])

            if provider_id not in self.config.providers:
                self.config.providers[provider_id] = ProviderConfig(
                    name=info["name"],
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                )
            else:
                p = self.config.providers[provider_id]
                p.name = info["name"]
                if api_key:
                    p.api_key = api_key
                p.base_url = base_url
                if not p.model:
                    p.model = model

    def save(self):
        """Persist config to disk"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(self.config.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # Also save env vars for subprocess compat
        self._save_env()

    def _save_env(self):
        """Save active provider credentials to .env"""
        active = self.get_active()
        if not active:
            return
        existing = {}
        if ENV_FILE.exists():
            with open(ENV_FILE, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        existing[k] = v

        info = DEFAULT_PROVIDERS.get(self.config.active_provider, {})
        if info:
            existing[info["env_key"]] = active.api_key
            if info.get("env_model"):
                existing[info["env_model"]] = active.model

        with open(ENV_FILE, "w", encoding="utf-8") as f:
            for k, v in existing.items():
                f.write(f"{k}={v}\n")
            if active.custom:
                f.write(f"CUSTOM_API_BASE={active.base_url}\n")

    def get_active(self) -> Optional[ProviderConfig]:
        """Get the active provider config"""
        return self.config.providers.get(self.config.active_provider)

    def set_provider(self, provider_id: str, api_key: str = "",
                     base_url: str = "", model: str = "",
                     name: str = ""):
        """Configure a provider"""
        if provider_id in DEFAULT_PROVIDERS:
            info = DEFAULT_PROVIDERS[provider_id]
            p = ProviderConfig(
                name=info["name"],
                base_url=base_url or info["base_url"],
                api_key=api_key,
                model=model or info["default_model"],
            )
        else:
            # Custom provider
            p = ProviderConfig(
                name=name or provider_id,
                base_url=base_url,
                api_key=api_key,
                model=model,
                custom=True,
            )
        self.config.providers[provider_id] = p
        self.config.active_provider = provider_id
        self.config.first_run = False

        # Set env vars immediately
        os.environ["LAAP_PROVIDER"] = provider_id
        os.environ["LAAP_API_KEY"] = api_key
        os.environ["LAAP_BASE_URL"] = base_url
        os.environ["LAAP_MODEL"] = model

        # Set standard env vars
        info = DEFAULT_PROVIDERS.get(provider_id)
        if info:
            os.environ[info["env_key"]] = api_key

        self.save()

    def add_custom_provider(self, name: str, base_url: str,
                            api_key: str = "", model: str = "",
                            provider_id: str = "") -> str:
        """Add a custom OpenAI-compatible provider"""
        pid = provider_id or f"custom_{len(self.config.providers)}"
        self.config.providers[pid] = ProviderConfig(
            name=name,
            base_url=base_url,
            api_key=api_key,
            model=model or "gpt-4o",
            custom=True,
        )
        return pid

    def test_connection(self, provider_id: Optional[str] = None) -> tuple[bool, str]:
        """Test if a provider connection works"""
        pid = provider_id or self.config.active_provider
        p = self.config.providers.get(pid)
        if not p:
            return False, f"Provider '{pid}' not configured"

        if not p.api_key and pid != "ollama":
            return False, f"No API key for {p.name}"

        try:
            from openai import OpenAI
            base = p.base_url.rstrip("/")
            client = OpenAI(api_key=p.api_key, base_url=f"{base}" if "openai" in pid.lower() or pid == "openrouter" or p.custom else base)
            models = client.models.list()
            count = len(list(models)[:5])
            return True, f"Connected! {count} models available"
        except ImportError:
            return True, "openai package not installed (run: pip install openai)"
        except Exception as e:
            return False, f"Connection failed: {str(e)[:100]}"

    def get_provider_list(self) -> List[tuple[str, str, bool]]:
        """Get list of (id, name, configured)"""
        result = []
        for pid, p in self.config.providers.items():
            configured = bool(p.api_key) or pid == "ollama"
            display = f"{p.name} ({p.model})" if p.model else p.name
            result.append((pid, display, configured))
        return result

    def is_configured(self) -> bool:
        """Check if any provider has API key configured"""
        for p in self.config.providers.values():
            if p.api_key:
                return True
        return "ollama" in self.config.providers  # Ollama is always "configured"

    def apply_to_environment(self):
        """Apply config to os.environ so LLMFactory picks it up"""
        active = self.get_active()
        if not active:
            return
        os.environ["LAAP_PROVIDER"] = self.config.active_provider
        if active.api_key:
            os.environ["LAAP_API_KEY"] = active.api_key
        if active.base_url:
            os.environ["LAAP_BASE_URL"] = active.base_url
        if active.model:
            os.environ["LAAP_MODEL"] = active.model

        info = DEFAULT_PROVIDERS.get(self.config.active_provider)
        if info:
            if active.api_key:
                os.environ[info["env_key"]] = active.api_key

    def interactive_setup(self) -> bool:
        """Full interactive setup wizard — returns True if configured"""
        from laap.cli.skins import GOLD, GOLD_BRIGHT, GOLD_DIM, RESET, BOLD, SYM

        print(f"\n  {GOLD}{'='*54}{RESET}")
        print(f"  {GOLD_BRIGHT}{BOLD}LAAP API 配置向导{RESET}")
        print(f"  {GOLD_DIM}配置 LLM 提供商以启用 AI 对话功能{RESET}")
        print(f"  {GOLD}{'='*54}{RESET}\n")

        # Step 1: Choose setup mode
        print(f"  {GOLD}1{RESET}) 使用预设提供商 (OpenAI/Anthropic/DeepSeek/OpenRouter/Ollama)")
        print(f"  {GOLD}2{RESET}) 自定义 API (兼容 OpenAI 格式)")
        print(f"  {GOLD}3{RESET}) 跳过 (本地模式)\n")

        choice = input(f"  选择 [1]: ").strip() or "1"

        if choice == "3":
            print(f"\n  {SYM['warn']} 跳过配置，使用本地模式")
            self.config.first_run = False
            self.save()
            return False

        if choice == "2":
            return self._setup_custom()

        return self._setup_preset()

    def _setup_preset(self) -> bool:
        """Preset provider setup"""
        from laap.cli.skins import GOLD, GOLD_BRIGHT, GOLD_DIM, RESET, SYM

        print(f"\n  {GOLD}可选提供商:{RESET}")
        providers = [
            ("1", "openai", "OpenAI GPT-4o"),
            ("2", "anthropic", "Anthropic Claude"),
            ("3", "deepseek", "DeepSeek"),
            ("4", "openrouter", "OpenRouter (多模型)"),
            ("5", "ollama", "Ollama (本地部署)"),
        ]
        for num, pid, name in providers:
            info = DEFAULT_PROVIDERS[pid]
            configured = bool(self.config.providers.get(pid, ProviderConfig()).api_key)
            status = f"{SYM['ok']} 已配置" if configured else "  "
            print(f"  {GOLD}{num}{RESET}) {name:30s} {status}")

        provider_choice = input(f"\n  选择提供商 [1]: ").strip() or "1"
        provider_map = dict((n, pid) for n, pid, _ in providers)
        provider_id = provider_map.get(provider_choice, "openai")
        info = DEFAULT_PROVIDERS[provider_id]

        # API Key
        current_p = self.config.providers.get(provider_id)
        current_key = current_p.api_key if current_p else ""
        current_model = current_p.model if current_p else info["default_model"]

        print(f"\n  {GOLD}提供商{RESET}: {info['name']}")
        print(f"  {GOLD}默认端点{RESET}: {info['base_url']}")
        print(f"  {GOLD_DIM}  如需自定义端点，请选择「自定义 API」模式{RESET}\n")

        key_prompt = f"  API Key ({'当前已设置' if current_key else '留空跳过'}): "
        api_key = input(key_prompt).strip() or current_key

        model_prompt = f"  模型 [{current_model}]: "
        model = input(model_prompt).strip() or current_model

        if api_key or provider_id == "ollama":
            self.set_provider(provider_id, api_key=api_key, model=model)

            print(f"\n  {SYM['ok']} {GOLD_BRIGHT}配置成功!{RESET}")
            print(f"  Provider: {info['name']}")
            print(f"  Model:    {model}")
            print(f"  Endpoint: {info['base_url']}")

            # Test connection
            test = input(f"\n  测试连接? [Y/n]: ").strip().lower()
            if test != "n":
                ok, msg = self.test_connection()
                print(f"  {SYM['ok'] if ok else SYM['err']} {msg}")

            return True
        else:
            print(f"\n  {SYM['warn']} 未提供 API Key")
            return False

    def _setup_custom(self) -> bool:
        """Custom OpenAI-compatible endpoint setup"""
        from laap.cli.skins import GOLD, GOLD_BRIGHT, GOLD_DIM, RESET, SYM

        print(f"\n  {GOLD}自定义 API 配置{RESET}")
        print(f"  {GOLD_DIM}支持任何 OpenAI 兼容接口 (OneAPI, LocalLLM, 中转, 代理...){RESET}\n")

        name = input(f"  显示名称 [MyAPI]: ").strip() or "MyAPI"
        base_url = input(f"  API 端点 URL (https://...): ").strip()
        while not base_url:
            base_url = input(f"  API 端点 URL (必填): ").strip()

        api_key = input(f"  API Key (可留空): ").strip()
        model = input(f"  模型 [gpt-4o]: ").strip() or "gpt-4o"

        pid = self.add_custom_provider(name=name, base_url=base_url,
                                       api_key=api_key, model=model)
        self.config.active_provider = pid
        self.config.first_run = False
        self.save()

        # Set env
        os.environ["LAAP_PROVIDER"] = pid
        os.environ["LAAP_API_KEY"] = api_key
        os.environ["LAAP_BASE_URL"] = base_url
        os.environ["LAAP_MODEL"] = model

        print(f"\n  {SYM['ok']} {GOLD_BRIGHT}自定义 API 配置成功!{RESET}")
        print(f"  Name:     {name}")
        print(f"  Endpoint: {base_url}")
        print(f"  Model:    {model}")

        test = input(f"\n  测试连接? [Y/n]: ").strip().lower()
        if test != "n":
            ok, msg = self.test_connection(pid)
            print(f"  {SYM['ok'] if ok else SYM['err']} {msg}")

        return True

    def switch_interactive(self):
        """Interactive provider switch"""
        from laap.cli.skins import GOLD, GOLD_BRIGHT, GOLD_DIM, RESET, SYM

        providers = self.get_provider_list()
        if not providers:
            print(f"  {SYM['warn']} No providers configured")
            return

        print(f"\n  {GOLD}已配置的提供商:{RESET}")
        for i, (pid, display, configured) in enumerate(providers, 1):
            status = SYM['ok'] if configured else " "
            active = "← 当前" if pid == self.config.active_provider else ""
            print(f"  {GOLD}{i}{RESET}) {display:35s} {status} {GOLD_DIM}{active}{RESET}")

        print(f"  {GOLD}a{RESET}) 添加自定义 API")

        choice = input(f"\n  选择 [1]: ").strip() or "1"
        if choice.lower() == "a":
            self._setup_custom()
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(providers):
                pid, _, _ = providers[idx]
                self.config.active_provider = pid
                p = self.config.providers[pid]
                self.set_provider(pid, api_key=p.api_key, base_url=p.base_url, model=p.model)
                print(f"  {SYM['ok']} 已切换到: {p.name}")
        except (ValueError, IndexError):
            print(f"  {SYM['err']} 无效选择")


# Global singleton
config_manager = ConfigManager()
