"""PluginLoader — 插件发现与加载"""
from __future__ import annotations
import os, sys, json, logging, importlib, inspect
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger("agent_core.plugins.loader")

class PluginInfo:
    def __init__(self, name: str = "", version: str = "1.0", description: str = "",
                 module_path: str = "", enabled: bool = True):
        self.name = name
        self.version = version
        self.description = description
        self.module_path = module_path
        self.enabled = enabled

class PluginLoader:
    """插件加载器 — 从目录加载插件"""
    
    def __init__(self, plugin_dirs: List[str] = None):
        self.plugin_dirs = plugin_dirs or []
        self._loaded: Dict[str, Any] = {}
        self._infos: Dict[str, PluginInfo] = {}
    
    def add_directory(self, path: str):
        if os.path.isdir(path):
            self.plugin_dirs.append(path)
    
    def discover(self) -> List[PluginInfo]:
        """发现所有可用插件"""
        infos = []
        for pdir in self.plugin_dirs:
            if not os.path.isdir(pdir):
                continue
            for item in os.listdir(pdir):
                plugin_path = os.path.join(pdir, item)
                if os.path.isdir(plugin_path):
                    meta_path = os.path.join(plugin_path, "plugin.json")
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                meta = json.load(f)
                            info = PluginInfo(
                                name=meta.get("name", item),
                                version=meta.get("version", "1.0"),
                                description=meta.get("description", ""),
                                module_path=plugin_path,
                                enabled=meta.get("enabled", True),
                            )
                            infos.append(info)
                            self._infos[info.name] = info
                        except: pass
        return infos
    
    def load(self, plugin_name: str) -> Optional[Any]:
        """加载单个插件"""
        if plugin_name in self._loaded:
            return self._loaded[plugin_name]
        info = self._infos.get(plugin_name)
        if not info:
            return None
        try:
            sys.path.insert(0, os.path.dirname(info.module_path))
            mod = importlib.import_module(os.path.basename(info.module_path))
            self._loaded[plugin_name] = mod
            logger.info(f"Plugin loaded: {plugin_name} v{info.version}")
            return mod
        except Exception as e:
            logger.error(f"Plugin load failed: {plugin_name}: {e}")
            return None
    
    def load_all(self) -> Dict[str, Any]:
        """加载所有已发现的插件"""
        for name in self._infos:
            self.load(name)
        return dict(self._loaded)
    
    def unload(self, plugin_name: str):
        self._loaded.pop(plugin_name, None)
        for hook_point, handlers in __import__('laap.agent_core.plugins.hooks', fromlist=['HookRegistry']).HookRegistry._hooks.items():
            __import__('laap.agent_core.plugins.hooks', fromlist=['HookRegistry']).HookRegistry._hooks[hook_point] = [
                (h, p) for h, p in handlers if p != plugin_name
            ]
    
    def get_loaded(self) -> List[str]:
        return list(self._loaded.keys())
