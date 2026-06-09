"""
LAAP - Lifeform Autonomous Adaptive Protocol
自进化引擎意识生命体

超越传统 Agent 框架的新一代类生命智能体系统。
基于 Lifeform Autonomous Adaptive Protocol 协议规范。
"""

__version__ = "0.3.0"
__name__ = "LAAP"


def show_logo():
    return r"""
    ======================================================
    ||  L       A       A       P                       ||
    ||  L      A A     A A     P  P                     ||
    ||  L     A   A   A   A   P    P                    ||
    ||  L    AAAAAAA AAAAAAA P    P    Living Agent      ||
    ||  L   A       A       A PPPPP     Application      ||
    ||  LLL A       A       A P         Protocol         ||
    ======================================================
    """


def show_intro():
    return """  生命计算范式 | Living Computation Paradigm
  Psi 意识驱动 | 递归自我进化 | 环境感知 | 多体协同"""


_import_map = {
    "Agent": ("laap.agent.base", "Agent"),
    "LifelikeAgent": ("laap.agent.lifelike", "LifelikeAgent"),
    "CodexAgent": ("laap.agent.codex", "CodexAgent"),
    "NeedDriveSystem": ("laap.cognition.needs", "NeedDriveSystem"),
    "NeedType": ("laap.cognition.needs", "NeedType"),
    "EmotionGradient": ("laap.cognition.emotion", "EmotionGradient"),
    "AwarenessSystem": ("laap.cognition.awareness", "AwarenessSystem"),
    "HierarchicalMemory": ("laap.memory.hierarchical", "HierarchicalMemory"),
    "RSIEngine": ("laap.evolution.rsi", "RSIEngine"),
    "SymbolicRecursionLayer": ("laap.evolution.symbolic", "SymbolicRecursionLayer"),
    "Sandbox": ("laap.evolution.sandbox", "Sandbox"),
    "FitnessEvaluator": ("laap.evaluation.fitness", "FitnessEvaluator"),
    "Swarm": ("laap.orchestration.swarm", "Swarm"),
    "SharedStateBus": ("laap.orchestration.shared_state", "SharedStateBus"),
    "ToolRegistry": ("laap.tools.tool_registry", "ToolRegistry"),
    "LLMFactory": ("laap.llm.factory", "LLMFactory"),
    "RustTokenCounter": ("laap.laap_core", "TokenCounter"),
    "RustMemoryEngine": ("laap.laap_core", "MemoryEngine"),
    "RustExperienceGraph": ("laap.laap_core", "ExperienceGraph"),
    "RustKeywordSearch": ("laap.laap_core", "KeywordSearch"),
    "RustSessionManager": ("laap.laap_core", "SessionManager"),
}

_RUST_AVAILABLE = None


def rust_available() -> bool:
    global _RUST_AVAILABLE
    if _RUST_AVAILABLE is None:
        try:
            import laap.laap_core
            _RUST_AVAILABLE = True
        except Exception:
            _RUST_AVAILABLE = False
    return _RUST_AVAILABLE


def __getattr__(name):
    if name in _import_map:
        module_name, attr_name = _import_map[name]
        import importlib
        mod = importlib.import_module(module_name)
        return getattr(mod, attr_name)
    import importlib
    try:
        return importlib.import_module(f".{name}", __name__)
    except ImportError:
        pass
    if name.startswith("_"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    try:
        import importlib.util as _util
        if _util.find_spec(f"{__name__}.{name}"):
            return importlib.import_module(f".{name}", __name__)
    except (ImportError, ModuleNotFoundError, ValueError):
        pass
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return list(_import_map.keys()) + ["__version__", "__name__", "show_logo", "show_intro"]


__all__ = list(_import_map.keys())
