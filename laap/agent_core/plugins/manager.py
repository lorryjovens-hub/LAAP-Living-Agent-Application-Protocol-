"""PluginManager — 统一插件管理"""
from __future__ import annotations
import os, json, logging, threading
from typing import Any, Callable, Dict, List, Optional
from laap.agent_core.plugins.loader import PluginLoader, PluginInfo
from laap.agent_core.plugins.hooks import HookRegistry, HookPoint, HookContext

logger = logging.getLogger("agent_core.plugins.manager")

class PluginManager:
    def __init__(self, plugin_dir: str = ""):
        self.plugin_dir = plugin_dir or os.path.join(os.path.dirname(__file__))
        self.loader = PluginLoader([self.plugin_dir])
        self._config: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._load_config()
    
    def _load_config(self):
        cfg_path = os.path.join(self.plugin_dir, "plugins.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except: pass
    
    def discover(self) -> List[PluginInfo]:
        return self.loader.discover()
    
    def enable(self, name: str):
        with self._lock:
            self._config[name] = self._config.get(name, {})
            self._config[name]["enabled"] = True
        self._save_config()
    
    def disable(self, name: str):
        with self._lock:
            self._config[name] = self._config.get(name, {})
            self._config[name]["enabled"] = False
        self.loader.unload(name)
        self._save_config()
    
    def _save_config(self):
        cfg_path = os.path.join(self.plugin_dir, "plugins.json")
        try:
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
        except: pass
    
    def init_plugins(self, agent=None) -> int:
        """初始化所有启用的插件"""
        count = 0
        for info in self.discover():
            cfg = self._config.get(info.name, {})
            if cfg.get("enabled", info.enabled):
                mod = self.loader.load(info.name)
                if mod and hasattr(mod, "init_plugin"):
                    try:
                        mod.init_plugin(agent=agent, config=cfg)
                        count += 1
                    except Exception as e:
                        logger.error(f"Plugin init failed: {info.name}: {e}")
        HookRegistry.trigger(HookPoint.PLUGIN_LOAD, {"count": count})
        return count
    
    def shutdown(self):
        HookRegistry.trigger(HookPoint.SHUTDOWN)
        for name in self.loader.get_loaded():
            self.loader.unload(name)
    
    def get_stats(self) -> dict:
        return {"plugins": len(self.loader.get_loaded()), "discovered": len(self.discover())}
