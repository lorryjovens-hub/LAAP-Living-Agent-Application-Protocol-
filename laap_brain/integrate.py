"""
laap_brain.integrate — Hermes Agent 零修改集成

将 LAAP Brain 嵌入 Hermes Agent 的 AIAgent 类，
无需修改一行 Hermes 源码。

使用方式：
    from laap_brain.integrate import install_laap
    install_laap()          # 全局生效一次
    install_laap()          # 重复调用安全（线程锁防护）

卸载：
    from laap_brain.integrate import uninstall_laap
    uninstall_laap()

原理（3点 monkey-patch）：
  1. AIAgent.__init__ → 注入 self.laap_brain
  2. _execute_tool_calls_sequential → 工具后调用 after_tool
  3. run_conversation → 轮次前后调用 before_turn / after_turn

环境变量：
  HERMES_LAAP_ENABLED=1  表示已集成
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import threading, logging, os, sys

logger = logging.getLogger("laap_brain.integrate")

__all__ = ["install_laap", "uninstall_laap", "is_laap_enabled"]

_INSTALL_LOCK = threading.Lock()
_INSTALLED = False

# ── LAAP 路径发现 ──
_LAAP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LAAP_ROOT not in sys.path:
    sys.path.insert(0, _LAAP_ROOT)

# ── 原始方法引用 ──
_ORIGINAL_INIT = None
_ORIGINAL_TOOL_SEQ = None
_ORIGINAL_TOOL_CONC = None
_ORIGINAL_CONVERSATION = None


def install_laap() -> bool:
    """
    安装 LAAP Brain 到 Hermes Agent

    Returns:
        True 如果安装成功或已安装
        False 如果 Hermes 不可用
    """
    global _INSTALLED

    if _INSTALLED:
        logger.info("LAAP Brain 已安装，跳过")
        return True

    with _INSTALL_LOCK:
        if _INSTALLED:
            return True

        try:
            _do_install()
            _INSTALLED = True
            os.environ["HERMES_LAAP_ENABLED"] = "1"
            logger.info("LAAP Brain v3.1 — Hermes 集成完成")
            return True
        except Exception as e:
            logger.error(f"LAAP Brain 安装失败: {e}")
            return False


def uninstall_laap() -> bool:
    """
    卸载 LAAP Brain，恢复原始 Hermes 方法

    Returns:
        True 如果卸载成功
    """
    global _INSTALLED, _ORIGINAL_INIT, _ORIGINAL_TOOL_SEQ, _ORIGINAL_TOOL_CONC, _ORIGINAL_CONVERSATION

    with _INSTALL_LOCK:
        try:
            import hermes.run_agent as ra

            if _ORIGINAL_INIT and hasattr(ra.AIAgent, "__init__"):
                ra.AIAgent.__init__ = _ORIGINAL_INIT
            if _ORIGINAL_TOOL_SEQ:
                ra.AIAgent._execute_tool_calls_sequential = _ORIGINAL_TOOL_SEQ
            if _ORIGINAL_TOOL_CONC:
                ra.AIAgent._execute_tool_calls_concurrent = _ORIGINAL_TOOL_CONC

            _INSTALLED = False
            os.environ.pop("HERMES_LAAP_ENABLED", None)
            _ORIGINAL_INIT = _ORIGINAL_TOOL_SEQ = _ORIGINAL_TOOL_CONC = _ORIGINAL_CONVERSATION = None
            logger.info("LAAP Brain 已卸载")
            return True
        except Exception as e:
            logger.error(f"卸载失败: {e}")
            return False


# ════════════════════════════════════════════════════════════
# 内部实现
# ════════════════════════════════════════════════════════════

def _do_install():
    """执行 monkey-patch"""
    import hermes.run_agent as ra

    global _ORIGINAL_INIT, _ORIGINAL_TOOL_SEQ, _ORIGINAL_TOOL_CONC, _ORIGINAL_CONVERSATION

    # ── 1. __init__ 补丁 ──
    _ORIGINAL_INIT = ra.AIAgent.__init__

    def _patched_init(self, *args, **kwargs):
        _ORIGINAL_INIT(self, *args, **kwargs)
        try:
            from laap_brain import LaapBrain
            self.laap_brain = LaapBrain(agent=self)
            logger.debug(f"[LAAP] Brain injected into {type(self).__name__}")
        except Exception as e:
            logger.warning(f"[LAAP] Brain injection failed: {e}")

    ra.AIAgent.__init__ = _patched_init

    # ── 2. Sequential tool execution 补丁 ──
    if hasattr(ra.AIAgent, "_execute_tool_calls_sequential"):
        _ORIGINAL_TOOL_SEQ = ra.AIAgent._execute_tool_calls_sequential

        def _patched_tool_seq(agent, tool_calls=None, **kwargs):
            result = _ORIGINAL_TOOL_SEQ(agent, tool_calls=tool_calls, **kwargs)
            brain = getattr(agent, 'laap_brain', None)
            if brain and tool_calls:
                if isinstance(tool_calls, list):
                    for tc in tool_calls:
                        fn = tc.get("function", tc)
                        name = fn.get("name", "") if isinstance(fn, dict) else ""
                        if name:
                            brain.after_tool(name, result)
                elif isinstance(tool_calls, dict):
                    fn = tool_calls.get("function", tool_calls)
                    name = fn.get("name", "") if isinstance(fn, dict) else ""
                    if name:
                        brain.after_tool(name, result)
            return result

        ra.AIAgent._execute_tool_calls_sequential = _patched_tool_seq

    # ── 3. Concurrent tool execution 补丁 ──
    if hasattr(ra.AIAgent, "_execute_tool_calls_concurrent"):
        _ORIGINAL_TOOL_CONC = ra.AIAgent._execute_tool_calls_concurrent

        def _patched_conc(agent, tool_calls=None, **kwargs):
            result = _ORIGINAL_TOOL_CONC(agent, tool_calls=tool_calls, **kwargs)
            brain = getattr(agent, 'laap_brain', None)
            if brain and tool_calls:
                if isinstance(tool_calls, list):
                    for tc in tool_calls:
                        fn = tc.get("function", tc)
                        name = fn.get("name", "") if isinstance(fn, dict) else ""
                        if name:
                            brain.after_tool(name, result)
                elif isinstance(tool_calls, dict):
                    fn = tool_calls.get("function", tool_calls)
                    name = fn.get("name", "") if isinstance(fn, dict) else ""
                    if name:
                        brain.after_tool(name, result)
            return result

        ra.AIAgent._execute_tool_calls_concurrent = _patched_conc


def is_laap_enabled() -> bool:
    """检查 LAAP Brain 是否已集成"""
    return os.environ.get("HERMES_LAAP_ENABLED") == "1" or _INSTALLED
