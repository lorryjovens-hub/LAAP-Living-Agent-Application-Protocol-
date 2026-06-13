"""
LAAP AGI v2.0 — Hermes Agent Deep Integration (深度集成补丁)

Upgrades from laap_brain kernel (1,400 lines) to full AGI pipeline (4,370 lines).

Hook Points (3 monkey-patches on AIAgent):
  1. __init__ → AGIBridge injected (with all 7 AGI modules)
  2. run_conversation → before_turn + after_turn + context injection
  3. tool_executor → after_tool with learning + world model updates

Changes from v3.1:
  - LaapBrain → AGIBridge (full AGI framework)
  - Domain auto-classification
  - Context injection into system prompt
  - 6 new slash commands: /world /reflect /know /agi /analogies /causal
  - Graceful fallback if full AGI not available
  - Thread-safe singleton bridge
"""

from __future__ import annotations
import logging, types, json, os, threading, sys
from typing import Any, Dict, Optional

logger = logging.getLogger("laap_brain.integrate")

_ORIGINAL_INIT = None
_ORIGINAL_CONV = None
_ORIGINAL_TOOL_SEQ = None
_INSTALL_LOCK = threading.Lock()
_INSTALLED = False
_BRIDGE: Optional[Any] = None  # AGIBridge singleton reference


def is_laap_installed() -> bool:
    """Check if LAAP AGI is installed in current Hermes process."""
    return _INSTALLED


def install_laap(force_full_agi: bool = True) -> bool:
    """
    Install LAAP AGI bridge into Hermes Agent.
    NEVER throws — gracefully returns False on any failure.
    """
    global _INSTALLED, _ORIGINAL_INIT, _ORIGINAL_CONV, _ORIGINAL_TOOL_SEQ, _BRIDGE
    
    try:  # ← Top-level shield: LAAP never blocks Hermes
        with _INSTALL_LOCK:
            if _INSTALLED:
                return True

        # ── Step 0: Initialize AGI Bridge ──
        from laap_brain.agi_bridge import AGIBridge
        _BRIDGE = AGIBridge.get_instance()
        logger.info(f"[AGI] Bridge initialized: {_BRIDGE.get_version()}")
    except Exception as e:
        logger.warning(f"[AGI] Bridge: {e}")
        _BRIDGE = None

    if _BRIDGE is None and not _try_kernel_fallback():
        _INSTALLED = False
        return False

    # ── Step 1: AIAgent.__init__ injection ──
    # ── Step 1: AIAgent.__init__ injection ──
    import run_agent
    _ORIGINAL_INIT = run_agent.AIAgent.__init__

    def _patched_init(self, *args, **kwargs):
        _ORIGINAL_INIT(self, *args, **kwargs)
        self._agi_bridge = _BRIDGE  # Shared singleton
        self._agi_context_injected = False
        self._agi_domain = "general"
        self._agi_turn_count = 0
        # Mount v4.0 enhancements (evolution engine, multi-agent, PSI)
        try:
            from laap_brain.integrate import mount_enhancements
            mount_enhancements(self)
        except Exception:
            pass
        logger.debug(f"[AGI] Agent {id(self):x} connected to bridge")

    run_agent.AIAgent.__init__ = _patched_init

    # ── Step 2: run_conversation patch ──
    _ORIGINAL_CONV = run_agent.AIAgent.run_conversation

    def _patched_conversation(self, user_message, *args, **kwargs):
        bridge = getattr(self, '_agi_bridge', None)
        user_msg_str = str(user_message) if user_message else ""

        # ── BEFORE TURN ──
        if bridge:
            try:
                # Detect domain from message + conversation context
                domain = self._agi_domain or "general"
                if hasattr(self, '_agi_turn_count'):
                    self._agi_turn_count += 1

                prep = bridge.before_turn(user_msg_str, domain=domain)
                if prep.get("domain"):
                    self._agi_domain = prep["domain"]

                # Inject AGI context into system prompt if not yet done
                if not self._agi_context_injected:
                    _inject_agi_context(self, bridge)
                    self._agi_context_injected = True

            except Exception as e:
                logger.debug(f"[AGI] before_turn: {e}")

        # ── ORIGINAL CONVERSATION ──
        result = _ORIGINAL_CONV(self, user_message, *args, **kwargs)

        # ── AFTER TURN ──
        if bridge:
            try:
                resp_text = ""
                if isinstance(result, dict):
                    resp_text = result.get("content", "") or str(result)[:300]
                elif isinstance(result, str):
                    resp_text = result[:300]

                bridge.after_turn(resp_text, domain=self._agi_domain)
            except Exception as e:
                logger.debug(f"[AGI] after_turn: {e}")

        return result

    run_agent.AIAgent.run_conversation = _patched_conversation

    # ── Step 3: Tool execution patch ──
    try:
        from agent import tool_executor
        _ORIGINAL_TOOL_SEQ = tool_executor.execute_tool_calls_sequential

        def _patched_tool_seq(agent, assistant_message, messages,
                              effective_task_id, api_call_count=0):
            """Tool execution with AGI monitoring."""
            tool_calls = []
            if isinstance(assistant_message, dict):
                tool_calls = assistant_message.get('tool_calls', [])

            result = _ORIGINAL_TOOL_SEQ(
                agent, assistant_message, messages,
                effective_task_id, api_call_count
            )

            bridge = getattr(agent, '_agi_bridge', None)
            if bridge:
                try:
                    names = []
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            fn = tc.get("function", tc)
                            name = fn.get("name", "") if isinstance(fn, dict) else ""
                            if name:
                                names.append(name)
                                args_dict = fn.get("arguments", {}) if isinstance(fn, dict) else {}
                                bridge.after_tool(name, result,
                                                  domain=getattr(agent, '_agi_domain', 'general'),
                                                  tool_args=args_dict if isinstance(args_dict, dict) else {})
                    if not names:
                        bridge.after_tool("unknown", result,
                                          domain=getattr(agent, '_agi_domain', 'general'))
                except Exception as e:
                    logger.debug(f"[AGI] after_tool: {e}")

            return result

        tool_executor.execute_tool_calls_sequential = _patched_tool_seq
        logger.info("[AGI] Tool executor patched")
    except (ImportError, AttributeError) as e:
        logger.debug(f"[AGI] Tool executor patch skipped: {e}")

    # ── Step 4: Environment markers ──
    os.environ["HERMES_LAAP_ENABLED"] = "1"
    os.environ["HERMES_LAAP_VERSION"] = _BRIDGE.get_version() if _BRIDGE else "kernel"

    version = os.environ["HERMES_LAAP_VERSION"]
    logger.info(f"[AGI] Integration complete — v{version} active"
                 f"({'full' if _BRIDGE and _BRIDGE.is_enhanced() else 'kernel'})")
    return True


def uninstall_laap() -> bool:
    """Uninstall LAAP AGI patches, restore original Hermes methods."""
    global _ORIGINAL_INIT, _ORIGINAL_CONV, _ORIGINAL_TOOL_SEQ, _INSTALLED, _BRIDGE

    import run_agent

    if _ORIGINAL_INIT:
        run_agent.AIAgent.__init__ = _ORIGINAL_INIT
    if _ORIGINAL_CONV:
        run_agent.AIAgent.run_conversation = _ORIGINAL_CONV
    try:
        from agent import tool_executor
        if _ORIGINAL_TOOL_SEQ:
            tool_executor.execute_tool_calls_sequential = _ORIGINAL_TOOL_SEQ
    except ImportError:
        pass

    # Shutdown bridge
    if _BRIDGE:
        try:
            _BRIDGE.shutdown()
        except:
            pass
        _BRIDGE = None

    _INSTALLED = False
    os.environ.pop("HERMES_LAAP_ENABLED", None)
    os.environ.pop("HERMES_LAAP_VERSION", None)
    logger.info("[AGI] Uninstalled — original Hermes methods restored")
    return True


# ════════════════════════════════════════════════════════════
# Context Injection
# ════════════════════════════════════════════════════════════

def _inject_agi_context(agent, bridge) -> bool:
    """
    Inject AGI cognitive context into the agent's system prompt.

    This is how the AGI modules influence the LLM — by providing it with
    structured self-knowledge and world state as part of its system prompt.
    """
    try:
        context = bridge.get_context_injection()
        if not context:
            return False

        # Append to system prompt
        if hasattr(agent, 'system_prompt_extra'):
            agent.system_prompt_extra = (agent.system_prompt_extra or "") + "\n\n" + context
        elif hasattr(agent, '_extra_system_prompt'):
            agent._extra_system_prompt = (getattr(agent, '_extra_system_prompt', "") +
                                          "\n\n" + context)

        logger.debug(f"[AGI] Context injected ({len(context)} chars)")
        return True
    except Exception as e:
        logger.debug(f"[AGI] Context injection failed: {e}")
        return False


def refresh_agi_context(agent) -> str:
    """Force-refresh the AGI context injection (call periodically)."""
    bridge = getattr(agent, '_agi_bridge', _BRIDGE)
    if bridge:
        return bridge.get_context_injection()
    return ""


# ════════════════════════════════════════════════════════════
# Slash Command Handler (extended with AGI commands)
# ════════════════════════════════════════════════════════════

def handle_slash_command(agent, cmd: str, args: str = "") -> str:
    """
    Handle /brain /reflect /decide /know /world /agi /analogies /causal

    Routes to AGIBridge handlers for full AGI commands.
    """
    bridge = getattr(agent, '_agi_bridge', _BRIDGE)

    # ── Legacy kernel commands ──
    if not bridge:
        brain = getattr(agent, 'laap_brain', None)
        if brain and hasattr(brain, 'handle_command'):
            return brain.handle_command(cmd)
        return "AGI modules not installed."

    # ── AGI commands ──
    agi_commands = {
        "/world", "/wm", "/reflect", "/ref", "/know", "/self",
        "/agi", "/status", "/analogies", "/analogy", "/causal", "/why",
        "/decide", "/brain", "/cognition",
    }

    cmd_normalized = cmd.lower()
    if not cmd_normalized.startswith("/"):
        cmd_normalized = "/" + cmd_normalized

    if cmd_normalized in agi_commands:
        return bridge.handle_slash_command(cmd, args)

    # Fallback to brain
    brain = getattr(agent, 'laap_brain', None)
    if brain and hasattr(brain, 'handle_command'):
        return brain.handle_command(cmd, args)

    return f"Unknown command: {cmd}\nAGI commands: /world /reflect /know /agi /analogies /causal"


# ════════════════════════════════════════════════════════════
# v4.0 Enhanced Modules — Evolution Engine + Multi-Agent + PSI
# ════════════════════════════════════════════════════════════

def mount_enhancements(agent: Any) -> Dict[str, Any]:
    """
    Mount v4.0 enhancement modules onto a Hermes AIAgent.
    
    Adds:
      - project_fusion: GitHub search + open-source integration
      - learning_loop: auto-skill creation from task patterns
      - memory_optimizer: structured knowledge graph
      - agent_registry + task_board: multi-agent coordination
      - evolution_engine files available at laap_brain/
    
    Returns dict of mounted components.
    """
    mounted = {}
    HERMES_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Evolution Engine
    try:
        sys.path.insert(0, HERMES_ROOT)
        from laap_brain.evolution_engine import ProjectFusion, LearningLoop, MemoryOptimizer
        agent.project_fusion = ProjectFusion()
        agent.learning_loop = LearningLoop()
        agent.memory_optimizer = MemoryOptimizer()
        mounted["evolution_engine"] = True
        logger.info("[LAAP v4.0] Evolution Engine mounted")
    except Exception as e:
        logger.warning(f"[LAAP v4.0] Evolution Engine: {e}")
        mounted["evolution_engine"] = False
    
    # 2. Multi-Agent System
    try:
        from laap_brain.multi_agent import AgentRegistry, TaskBoard, SafeRollback
        registry_path = os.path.join(HERMES_ROOT, ".agent_registry.json")
        board_path = os.path.join(HERMES_ROOT, ".task_board.json")
        agent.agent_registry = AgentRegistry(registry_path=registry_path)
        agent.task_board = TaskBoard(board_path=board_path)
        agent.safe_rollback = SafeRollback(repo_root=HERMES_ROOT)
        mounted["multi_agent"] = True
        logger.info("[LAAP v4.0] Multi-Agent System mounted")
    except Exception as e:
        logger.warning(f"[LAAP v4.0] Multi-Agent: {e}")
        mounted["multi_agent"] = False
    
    # 3. Digital Lifeform
    try:
        sys.path.insert(0, os.path.dirname(HERMES_ROOT))  # D:\LAAP for laap.lifeform
        from laap.lifeform.digital_lifeform import DigitalLifeform
        agent.digital_lifeform = DigitalLifeform(agent=agent, agent_id=getattr(agent, 'session_id', 'ao'))
        mounted["digital_lifeform"] = True
        logger.info("[LAAP v4.0] Digital Lifeform mounted")
    except Exception as e:
        logger.warning(f"[LAAP v4.0] Digital Lifeform: {e}")
        mounted["digital_lifeform"] = False
    
    # 4. Self-Evolve Engine (auto-heal + learning loop)
    try:
        from laap_brain.self_evolve import SelfEvolveEngine
        agent.self_evolve = SelfEvolveEngine(
            agent=agent,
            hermes_home=os.environ.get("HERMES_HOME") or os.path.expanduser(
                "~/AppData/Local/hermes/profiles/laap-avatar")
        )
        agent._pending_fixes = []
        logger.info("[LAAP v4.0] Self-Evolve Engine mounted")
        mounted["self_evolve"] = True
    except Exception as e:
        logger.warning(f"[LAAP v4.0] Self-Evolve: {e}")
        mounted["self_evolve"] = False
    
    # 5. PSI Driver (available but not default — use via agent.psi_driver)
    try:
        from laap_brain.psi_driver import PSIDriver, integrate_psi_driver
        if hasattr(agent, '_laap_bridge') and agent._laap_bridge:
            bridge = agent._laap_bridge
            # Build LLM channel from the bridge
            def _psi_llm(prompt):
                return bridge.handle_slash_command("agi", prompt)
            agent.psi_driver = PSIDriver(agent, llm_channel=_psi_llm)
        else:
            agent.psi_driver = PSIDriver(agent)
        mounted["psi_driver"] = True
        logger.info("[LAAP v4.0] PSI Driver mounted")
    except Exception as e:
        logger.warning(f"[LAAP v4.0] PSI Driver: {e}")
        mounted["psi_driver"] = False
    
    return mounted


# ════════════════════════════════════════════════════════════
# Kernel Fallback
# ════════════════════════════════════════════════════════════

def _try_kernel_fallback() -> bool:
    """Fall back to lightweight laap_brain kernel if full AGI unavailable."""
    global _BRIDGE
    try:
        from laap_brain import LaapBrain
        # Create a minimal wrapper that looks like AGIBridge
        class KernelWrapper:
            def __init__(self):
                self._brain = LaapBrain()

            def before_turn(self, msg, domain="general", context=None):
                self._brain.before_turn(msg[:200])
                return {"enhanced": True, "domain": domain}

            def after_tool(self, name, result, domain="general", tool_args=None):
                self._brain.after_tool(name, str(result)[:200])

            def after_turn(self, response, domain="general", duration=0):
                self._brain.after_turn(response[:200])

            def get_context_injection(self):
                return ""

            def handle_slash_command(self, cmd, args=""):
                return self._brain.handle_command(cmd, args)

            def is_enhanced(self):
                return False

            def get_version(self):
                return "1.4.0"

            def stats(self):
                return {"version": "1.4.0", "enhanced": False}

            def save(self):
                pass

            def shutdown(self):
                pass

        _BRIDGE = KernelWrapper()
        logger.info("[AGI] Kernel fallback active (laap_brain v1.4.0)")
        return True
    except Exception as e:
        logger.error(f"[AGI] Kernel fallback also failed: {e}")
        return False
