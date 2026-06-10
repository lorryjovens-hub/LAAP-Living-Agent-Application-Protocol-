"""ConfigManager — 完整配置管理(YAML/JSON/环境变量/热加载)"""
from __future__ import annotations
import os, json, logging, threading, time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("agent_core.config")

DEFAULT_CONFIG = {
    "agent": {"name": "LAAP-Agent", "temperature": 0.7, "max_tokens": 128000},
    "llm": {"provider": "deepseek", "model": "deepseek-v4-flash"},
    "memory": {"enabled": True, "type": "hybrid"},
    "tools": {"enabled": True},
    "platforms": {},
    "plugins": {},
    "cron": {"enabled": True},
}

class ConfigManager:
    """配置管理器 — 支持JSON/YAML/环境变量/多profile/热加载"""
    
    def __init__(self, config_dir: str = ""):
        self.config_dir = config_dir or os.path.expanduser("~/.laap")
        self._config: Dict = dict(DEFAULT_CONFIG)
        self._profiles: Dict[str, Dict] = {}
        self._current_profile: str = "default"
        self._watchers: List[Callable] = []
        self._lock = threading.RLock()
        os.makedirs(self.config_dir, exist_ok=True)
        self._load()
    
    def _load(self):
        """加载所有配置"""
        # 1. 默认配置
        self._config = dict(DEFAULT_CONFIG)
        
        # 2. 主配置文件
        main_path = os.path.join(self.config_dir, "config.json")
        if os.path.exists(main_path):
            try:
                with open(main_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                self._deep_merge(self._config, cfg)
                logger.info(f"Loaded config: {main_path}")
            except Exception as e:
                logger.error(f"Config load error: {e}")
        
        # 3. Profile配置文件
        profiles_dir = os.path.join(self.config_dir, "profiles")
        if os.path.isdir(profiles_dir):
            for f in os.listdir(profiles_dir):
                if f.endswith(('.json', '.yaml', '.yml')):
                    profile_name = f.rsplit('.', 1)[0]
                    try:
                        with open(os.path.join(profiles_dir, f), 'r', encoding='utf-8') as pf:
                            self._profiles[profile_name] = json.load(pf)
                    except: pass
        
        # 4. 环境变量覆盖
        env_map = {
            "LAAP_LLM_PROVIDER": ("llm", "provider"),
            "LAAP_LLM_MODEL": ("llm", "model"),
            "LAAP_LLM_API_KEY": ("llm", "api_key"),
            "LAAP_API_BASE": ("llm", "api_base"),
            "LAAP_AGENT_NAME": ("agent", "name"),
            "LAAP_TEMPERATURE": ("agent", "temperature"),
        }
        for env_key, (section, key) in env_map.items():
            val = os.environ.get(env_key)
            if val:
                self._config.setdefault(section, {})[key] = val
    
    def _deep_merge(self, base: Dict, override: Dict):
        for key, val in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(val, dict):
                self._deep_merge(base[key], val)
            else:
                base[key] = val
    
    def get(self, *keys, default=None):
        """获取配置值: config.get('llm','model')"""
        val = self._config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
                if val is None: return default
            else: return default
        return val if val is not None else default
    
    def set(self, key_path: str, value: Any):
        """设置配置: config.set('llm.model', 'gpt-4')"""
        keys = key_path.split('.')
        with self._lock:
            target = self._config
            for k in keys[:-1]:
                target = target.setdefault(k, {})
            target[keys[-1]] = value
            self._save()
    
    def _save(self):
        path = os.path.join(self.config_dir, "config.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Config save error: {e}")
    
    def use_profile(self, name: str):
        """切换profile"""
        profile = self._profiles.get(name)
        if profile:
            with self._lock:
                self._config = dict(DEFAULT_CONFIG)
                self._deep_merge(self._config, profile)
                self._current_profile = name
                logger.info(f"Switched to profile: {name}")
    
    def list_profiles(self) -> List[str]:
        return list(self._profiles.keys())
    
    def watch(self, callback: Callable):
        self._watchers.append(callback)
    
    def to_dict(self) -> dict:
        return dict(self._config)
    
    def get_stats(self) -> dict:
        return {"profile": self._current_profile, "profiles": len(self._profiles),
                "config_keys": len(self._config)}
