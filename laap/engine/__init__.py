"""LAAP Engine Layer — 核心引擎层"""
from typing import Dict, Any

class EngineRegistry:
    """引擎注册中心"""
    _engines: Dict[str, Any] = {}
    
    @classmethod
    def register(cls, name: str, engine: Any):
        cls._engines[name] = engine
    
    @classmethod
    def get(cls, name: str):
        return cls._engines.get(name)
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        return dict(cls._engines)
    
    @classmethod
    def start_all(cls):
        for name, engine in cls._engines.items():
            if hasattr(engine, "start"):
                engine.start()
    
    @classmethod
    def stop_all(cls):
        for name, engine in reversed(list(cls._engines.items())):
            if hasattr(engine, "stop"):
                engine.stop()
