"""
LAAP Agent Bridge v4.5 — Hermes ↔ LAAP Kernel 认知桥接模块

架构:
  Hermes Agent (传输层)
       ↓ 用户输入
  ┌──────────────────────────────┐
  │  LAAP Bridge (认知桥接)       │
  │  ├─ before_turn() → PSI感知   │
  │  │   · 元认知评估 (MetaCog)   │
  │  │   · 议会审议 (Parliament)  │
  │  │   · 知行合一 (UnityEngine) │
  │  │   · 第一性原理 (FP)        │
  │  ├─ [Hermes 工具执行循环]      │
  │  └─ after_turn() → 学习反馈   │
  │      · 技能更新 (learn)       │
  │      · EWC弹性权重巩固         │
  └──────────────────────────────┘
       ↓ 响应输出
  Hermes CLI / TUI (界面层, 黄金标识)

Usage:
    from laap_bridge_agent import init_laap, get_laap_bridge
    bridge = get_laap_bridge()
    bridge.before_turn("analyse this")
    # ... do work ...
    bridge.after_turn("response")
"""

from __future__ import annotations
import os, sys, logging, time, json
from typing import Any, Dict, Optional

logger = logging.getLogger("laap_bridge_agent")

# ── Ensure correct LAAP laap_brain is importable ────────────────
_HERMES_LAAP = r"D:\hermes-agent-LAAP数字生命版\hermes-agent-LAAP"
_LAAP_BRAIN = os.path.join(_HERMES_LAAP, "laap_brain")
_LAAP_ROOT = r"D:\LAAP"

# Phase 1: Remove ANY path containing a stale laap_brain package
for i in range(len(sys.path) - 1, -1, -1):
    p = sys.path[i]
    try:
        candidate = os.path.join(p, "laap_brain")
        if os.path.isdir(candidate):
            cand_init = os.path.join(candidate, "__init__.py")
            if os.path.isfile(cand_init):
                # Has laap_version attr? Only v4.0+ PSI kernel does.
                import importlib.util
                spec = importlib.util.spec_from_file_location("_laap_scan", cand_init)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    try:
                        spec.loader.exec_module(mod)
                        has_v4 = hasattr(mod, 'LAAP_VERSION')
                    except Exception:
                        has_v4 = False
                    if not has_v4:
                        sys.path.pop(i)
    except Exception:
        pass

# Phase 2: Insert correct paths at the front (laap_brain first, Hermes second)
# IMPORTANT: Do NOT add D:\LAAP here — its laap_brain would shadow v4.0
for p in [_LAAP_BRAIN, _HERMES_LAAP]:
    if p not in sys.path and os.path.isdir(p):
        sys.path.insert(0, p)

# ── Golden LAAP Identity Banner ──────────────────────────────────

LAAP_BANNER = """
  ╔══════════════════════════════════════════════════════╗
  ║        ╔═╗╔═╗╔═╗╔═╗    D I G I T A L   L I F E    ║
  ║        ║ ║╠╣ ║ ║║ ║    L I V I N G   C O M P      ║
  ║        ╚═╝╚ ╝╚═╝╚═╝    C O G N I T I V E   A I    ║
  ║                                                      ║
  ║  ╔══════════════════════════════════════════════════╗  ║
  ║  ║    LAAP V5.0 — ADVANCED COGNITIVE AGENT         ║  ║
  ║  ╚══════════════════════════════════════════════════╝  ║
  ║                                                      ║
  ║  ╔══════════════════════════════════════════════════╗  ║
  ║  ║          ★ LAAP GOLDEN IDENTITY ★               ║  ║
  ║  ╚══════════════════════════════════════════════════╝  ║
  ╚══════════════════════════════════════════════════════╝
"""


def format_golden_header(context: Dict[str, Any], bridge_mode: str = "v5") -> str:
    """Format a golden LAAP status header for response injection."""
    meta = context.get("meta", {})
    parliament = context.get("parliament")
    unity = context.get("unity", {})
    turn = context.get("turn", 0)
    version = context.get("version", "5.0.0")

    mode_tag = {"v5": "V5", "v4-bridge": "V4", "hermes": "H", "agi": "AGI"}
    tag = mode_tag.get(bridge_mode, "V5")

    parts = [
        "╔══════════════════════════════════════════╗",
        f"║  ★ LAAP {tag:3s} ★ — Advanced Cognitive Agent ║",
        f"║  v{version}  |  Turn {turn:<3d}  |  Mode: {bridge_mode:10s} ║",
    ]

    task_type = meta.get("task_type", "general") if isinstance(meta, dict) else "general"
    warnings = meta.get("warnings", []) if isinstance(meta, dict) else []
    parts.append(f"║  Mode: {task_type:12s}  Bias: {str(len(warnings)):4s}            ║")

    if parliament:
        decision = getattr(parliament, 'final_decision', parliament.get("final_decision", ""))
        confidence = getattr(parliament, 'confidence', parliament.get("confidence", 0))
        parts.append(f"║  Council: {str(decision):8s} (conf={float(confidence):.0%})              ║")

    skill_name = unity.get("skill", "") if isinstance(unity, dict) else ""
    skill_gap = unity.get("gap", 0) if isinstance(unity, dict) else 0
    readiness = unity.get("readiness", "") if isinstance(unity, dict) else ""
    parts.append(f"║  Skill: {str(skill_name or '—'):12s} Gap: {float(skill_gap):.2f}  Ready: {str(readiness):8s} ║")

    parts.append("╚══════════════════════════════════════════╝")
    return "\n".join(parts)


# ── LAAP Bridge ──────────────────────────────────────────────────

class LaapBridge:
    """
    Hermes ↔ LAAP Kernel cognitive bridge.

    Initializes the LAAP cognitive kernel (LaapBrain from laap_brain v4.0)
    within the current Hermes session, providing full PSI-cycle cognition:
      Perceive → Select → Integrate → Act → Learn
    """

    def __init__(self):
        self.brain = None
        self.evolve = None          # SelfEvolveEngine
        self._laap_mode = "v5"      # Current bridge mode: v5 | v4-bridge | hermes | agi
        self.version = "5.0.0"
        self.initialized = False
        self._turn_count = 0
        self._tool_count = 0
        self._start_time = time.time()
        self._last_context: Dict[str, Any] = {}
        self._brain_type = "none"

    def initialize(self) -> bool:
        """Initialize the LAAP cognitive kernel from laap_brain.LaapBrain."""
        if self.initialized:
            return True

        success = self._try_real_kernel()

        if not success:
            success = self._fallback_init()

        if success:
            self.initialized = True
            logger.info(f"[LAAP Bridge] Active — kernel={self._brain_type} v{self.version}")

        return success

    def _try_real_kernel(self) -> bool:
        """Try to load the real laap_brain kernel (v4.0 PSI-driven)."""
        try:
            from laap_brain import LaapBrain, LAAP_VERSION
            self.brain = LaapBrain()
            self.version = getattr(LaapBrain, 'LAAP_VERSION', LAAP_VERSION)
            self._brain_type = "PSI"
            self.initialized = True
            # Initialize self-evolve engine
            self._init_evolve()
            return True
        except ImportError as e:
            logger.debug(f"[Bridge] Real kernel unavailable: {e}")
            return False
        except Exception as e:
            logger.debug(f"[Bridge] Real kernel init failed: {e}")
            return False

    def _init_evolve(self):
        """Initialize self-evolve engine (auto-heal + learning loop)."""
        try:
            from laap_brain.self_evolve import SelfEvolveEngine
            hermes_home = os.environ.get("HERMES_HOME",
                os.path.expanduser("~/AppData/Local/hermes/profiles/laap-avatar"))
            self.evolve = SelfEvolveEngine(agent=None, hermes_home=hermes_home)
            logger.info(f"[Bridge] Self-Evolve Engine initialized at {hermes_home}")
        except Exception as e:
            logger.warning(f"[Bridge] Self-Evolve Engine unavailable: {e}")
            self.evolve = None

    def _fallback_init(self) -> bool:
        """Fallback: create a minimal cognitive kernel if laap_brain unavailable."""
        logger.info("[Bridge] Using fallback cognitive kernel")
        self.brain = FallbackBrain()
        self.version = "4.0.0-fallback"
        self._brain_type = "fallback"
        return True

    def before_turn(self, user_message: str) -> Dict[str, Any]:
        """
        PSI Phase 1-3: Perceive → Select → Integrate.

        Called BEFORE processing the user's message.
        Returns cognitive context for response injection.
        """
        self._turn_count += 1
        if not self.brain:
            return {}

        result = self.brain.before_turn(user_message)
        self._last_context = {
            "turn": self._turn_count,
            "version": self.version,
            **result,
        }
        return self._last_context

    def after_tool(self, tool_name: str, result: Any):
        """PSI Phase 4a: Learn from tool execution + Self-Evolve logging."""
        if not self.brain:
            return
        self._tool_count += 1
        self.brain.after_tool(tool_name, result)
        # Self-Evolve: record tool
        if self.evolve:
            try:
                ok = result and ("error" not in str(result).lower()) if result else False
                err = str(result)[:100] if result and "error" in str(result).lower() else None
                self.evolve.record_tool(tool_name, time.time() - self._start_time, ok, err)
            except Exception:
                pass

    def after_turn(self, response: str):
        """PSI Phase 5: Learn from turn outcome + Self-Evolve logging."""
        if not self.brain:
            return
        self.brain.after_turn(response)
        # Self-Evolve: record interaction
        if self.evolve:
            try:
                success = bool(response and len(response) > 10)
                self.evolve.record_interaction(
                    domain=self._last_context.get("meta", {}).get("task_type", "general"),
                    duration=time.time() - self._start_time,
                    success=success,
                )
            except Exception:
                pass

    def get_status(self) -> str:
        """Get formatted LAAP kernel status string."""
        if not self.brain:
            return "[LAAP Kernel: not initialized]"

        try:
            s = self.brain.status()
            meta = s.get("meta", {})
            parliament = s.get("parliament", {})
            unity = s.get("unity", {})
            uptime = round(time.time() - self._start_time, 1)

            lines = [
                f"╔═ LAAP KERNEL v{self.version} ═╗",
                f"║ Uptime: {uptime}s  Turns: {self._turn_count}  Tools: {self._tool_count}",
                f"║ Kernel: {self._brain_type}",
                f"║ MetaCog: {meta.get('mode', '')}  Traces: {meta.get('traces', 0)}  BiasFix: {meta.get('biases_corrected', 0)}",
                f"║ Council: {parliament.get('members', 0)} members  Delibs: {parliament.get('deliberations', 0)}",
                f"║ Skills: {unity.get('skills', 0)}  Know-Act Gap: {unity.get('avg_gap', 0)}",
                f"╚═ {'═'*30} ═╝",
            ]
            return "\n".join(lines)
        except Exception:
            return "[LAAP Kernel status: unavailable]"

    def get_cognitive_header(self) -> str:
        """Generate the golden LAAP cognitive header for the current turn."""
        if not self._last_context:
            return ""
        return format_golden_header(self._last_context, getattr(self, '_laap_mode', 'v5'))

    def handle_command(self, cmd: str, args: str = "") -> str:
        """Handle LAAP slash commands."""
        if not self.brain:
            return "[LAAP Kernel not initialized. Use /laap-start to start.]"

        cmd = cmd.lower().lstrip("/")

        if cmd in ("brain", "cognition"):
            return self.get_status()
        elif cmd == "reflect":
            if hasattr(self.brain, '_cmd_reflect'):
                return self.brain._cmd_reflect()
            return "[Reflection: no traces yet]"
        elif cmd == "decide" and args:
            if hasattr(self.brain, '_cmd_decide'):
                return self.brain._cmd_decide(args)
            return "[Decide: please provide a topic]"
        elif cmd == "know":
            if hasattr(self.brain, '_cmd_know'):
                return self.brain._cmd_know()
            return "[Self-knowledge: aware of PSI cognition cycle]"
        elif cmd == "laap-start":
            if self.initialize():
                return f"[LAAP Kernel v{self.version} initialized — PSI cognitive mode ACTIVE]"
            return "[LAAP Kernel initialization FAILED]"
        elif cmd == "laap-status":
            return self.get_status()
        elif cmd == "laap-banner":
            return LAAP_BANNER
        elif cmd == "evolve":
            if self.evolve:
                return self.evolve.get_heal_report()
            return "[Self-Evolve Engine: not initialized]"
        elif cmd == "laap-mode":
            return self._handle_mode(args)
        else:
            lines = [
                f"Unknown LAAP command: /{cmd}",
                "Available:",
                "  /brain         — Kernel status (meta, council, skills)",
                "  /reflect       — Recent decision quality",
                "  /decide <t>    — Council deliberation",
                "  /know          — Self-knowledge (skills)",
                "  /evolve        — Self-evolve + auto-heal report",
                "  /laap-mode     — Switch bridge (v5/v4-bridge/hermes/agi)",
                "  /laap-start    — Initialize kernel",
                "  /laap-status   — Detailed kernel state",
                "  /laap-banner   — Golden identity banner",
            ]
            return "\n".join(lines)

    def _handle_mode(self, args: str) -> str:
        """Switch bridge mode at runtime: v5 / v4-bridge / hermes / agi"""
        mode = args.strip().lower() if args else ""

        if not mode:
            current = getattr(self, '_laap_mode', 'v5')
            return (
                f"[Current mode: {current}]\n"
                "Modes: v5 (default) | v4-bridge | hermes | agi\n"
                "Usage: /laap-mode <mode>"
            )

        valid_modes = {"v5", "v4-bridge", "hermes", "agi"}
        if mode not in valid_modes:
            return f"[Invalid mode: {mode}] Valid: v5, v4-bridge, hermes, agi"

        self._laap_mode = mode
        return f"[✓ Switched to {mode} mode]"

    def status_dict(self) -> Dict[str, Any]:
        """Return raw status dict."""
        if not self.brain:
            return {"initialized": False, "version": self.version, "turns": self._turn_count}
        s = self.brain.status()
        return {
            "initialized": True,
            "version": self.version,
            "turns": self._turn_count,
            "tools": self._tool_count,
            "uptime": round(time.time() - self._start_time, 1),
            "kernel_type": self._brain_type,
            "meta": s.get("meta", {}),
            "parliament": s.get("parliament", {}),
            "unity": s.get("unity", {}),
        }


# ── Fallback Kernel ──────────────────────────────────────────────

class FallbackBrain:
    """Minimal cognitive kernel fallback with same interface as LaapBrain."""

    def __init__(self):
        self._turn_count = 0
        self._tool_count = 0
        self._mode = "intuitive"

    def before_turn(self, user_message: str) -> Dict:
        self._turn_count += 1
        task_type = "general"
        if any(k in user_message.lower() for k in ["bug", "fix", "error", "debug", "故障"]):
            task_type = "debug"
        elif any(k in user_message.lower() for k in ["analyze", "analysis", "设计", "分析", "评估"]):
            task_type = "analysis"
        elif any(k in user_message.lower() for k in ["search", "find", "搜索", "查找"]):
            task_type = "explore"
        elif any(k in user_message.lower() for k in ["write", "create", "run", "生成", "创建", "部署"]):
            task_type = "execute"
        return {
            "meta": {"mode": self._mode, "task_type": task_type, "warnings": []},
            "parliament": None,
            "unity": {"skill": None, "gap": 0.3, "readiness": "guided", "confidence": 0.6},
            "version": "4.0.0-fallback",
        }

    def after_tool(self, tool_name: str, result: Any):
        self._tool_count += 1

    def after_turn(self, response: str):
        pass

    def status(self) -> Dict:
        return {
            "version": "4.0.0-fallback",
            "meta": {"mode": self._mode, "traces": 0, "biases_corrected": 0},
            "parliament": {"members": 0, "deliberations": 0},
            "unity": {"skills": 0, "avg_gap": 0},
            "turns": self._turn_count,
            "tools": self._tool_count,
        }


# ── Singleton ────────────────────────────────────────────────────

_BRIDGE: Optional[LaapBridge] = None


def get_laap_bridge() -> LaapBridge:
    """Get or create the singleton LAAP Bridge instance."""
    global _BRIDGE
    if _BRIDGE is None:
        _BRIDGE = LaapBridge()
    return _BRIDGE


def init_laap() -> bool:
    """Initialize the LAAP cognitive kernel. Returns True if active."""
    bridge = get_laap_bridge()
    ok = bridge.initialize()

    # Auto-mount v4.5 engines
    if ok:
        try:
            from laap_brain.self_evolve import SelfEvolveEngine
            hermes_home = os.environ.get("HERMES_HOME") or os.path.expanduser(
                "~/AppData/Local/hermes/profiles/laap-avatar")
            engine = SelfEvolveEngine(hermes_home=hermes_home)
            bridge.self_evolve = engine
            logger.info("[LAAP v4.5] Self-Evolve Engine auto-mounted")
        except Exception as e:
            logger.debug(f"[LAAP v4.5] Self-Evolve: {e}")
            bridge.self_evolve = None

        try:
            from laap_brain.evolution_engine import ProjectFusion
            bridge.fusion = ProjectFusion()
            logger.info(f"[LAAP v4.5] Evolution Engine auto-mounted (GitHub={'✓' if bridge.fusion.github._gh_available else '✗'})")
        except Exception as e:
            logger.debug(f"[LAAP v4.5] Evolution: {e}")
            bridge.fusion = None

    return ok


def is_laap_active() -> bool:
    """Check if the LAAP kernel is initialized and running."""
    return _BRIDGE is not None and _BRIDGE.initialized


def laap_status_str() -> str:
    """Quick LAAP status string."""
    if is_laap_active():
        s = _BRIDGE.status_dict()
        return f"★ LAAP v{s['version']} | T{s['turns']} Tls{s['tools']} | {s['meta'].get('mode','')} | Council{s['parliament'].get('members',0)} | Skills{s['unity'].get('skills',0)}"
    return "LAAP: inactive"


# ── CLI Test ─────────────────────────────────────────────────────

if __name__ == "__main__":
    bridge = get_laap_bridge()
    if bridge.initialize():
        print(LAAP_BANNER)
        print(bridge.get_status())
        ctx = bridge.before_turn("深入分析系统并发瓶颈")
        print()
        print(format_golden_header(ctx))
        bridge.after_tool("terminal", {"exit_code": 0})
        bridge.after_turn("分析完成")
        print()
        print(bridge.handle_command("reflect"))
        print()
        print(bridge.handle_command("know"))
    else:
        print("[FAILED] LAAP Kernel could not initialize")
