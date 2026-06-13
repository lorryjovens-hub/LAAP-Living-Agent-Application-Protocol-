"""
LAAP AGI Bridge v2.2 — Full 11-Module Hermes Integration

Deep bridge connecting ALL LAAP AGI modules into Hermes Agent:
  WorldModel + SelfModel + Causal + Analogical + Learning +
  Autonomy + Conscious + MemorySystem + Evolution + Security + CodeEvolution

Every user message, tool call, and agent response flows through this bridge
to feed all 11 cognitive modules, creating a truly integrated AGI experience.

Hook flow:
  before_turn: security.scan → memory.attend → conscious.experience →
               self.assess → world.predict → analogical.query →
               causal.association → context injection

  after_tool:  conscious.experience → learning.learn → self.record →
               world.observe → memory.remember → evolution.record_metric

  after_turn:  conscious.reflect → memory.consolidate → autonomy.maintenance →
               learning.consolidate → code_evolution.periodic →
               context cache invalidate

Slash commands:
  /agi /world /know /reflect /analogies /causal
  /memory /evolve /scan /code  ← NEW
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import threading, logging, os, sys, time, json
from pathlib import Path
from collections import Counter

logger = logging.getLogger("laap_brain.agi_bridge")

_INSTANCE: Optional["AGIBridge"] = None
_INSTANCE_LOCK = threading.Lock()


class AGIBridge:
    """Singleton bridge: Hermes Agent ↔ Full LAAP AGI (11 modules)."""

    def __init__(self, state_dir: Optional[str] = None):
        self._agent = None
        self._state_dir = state_dir or self._default_state_dir()
        self._version = "v4.5"  # Current LAAP version: v0, v1, v2, v4, v4.5
        self._laap_mode = False  # If True, LAAP processing active
        self._last_tier = 2  # Auto-tier: 1=Fast, 2=Bridge, 3=PSI
        self._manual_tier = False  # User manually set tier via /tier
        self.BANNER_SHOWN = False

        self._interaction_count = 0
        self._last_context_injection = ""
        self._context_cache_ttl = 300  # DeepSeek V4 optimized: 5min cache
        self._last_context_time = 0.0
        self._domain_cache: Dict[str, str] = {}
        self.total_turns = 0
        self.total_tools = 0
        self.total_security_scans = 0
        self.created_at = time.time()
        self._lock = threading.Lock()
        self._init_agent()

    @classmethod
    def get_instance(cls, **kwargs) -> "AGIBridge":
        global _INSTANCE
        if _INSTANCE is None:
            with _INSTANCE_LOCK:
                if _INSTANCE is None:
                    _INSTANCE = cls(**kwargs)
        return _INSTANCE

    def _default_state_dir(self) -> str:
        hermes_home = os.environ.get("HERMES_HOME", "")
        if hermes_home:
            return os.path.join(hermes_home, "agi_state")
        return os.path.join(os.path.expanduser("~"), ".laap", "agi_state")

    def _init_agent(self):
        try:
            laap_root = os.environ.get("LAAP_ROOT", "")
            if not laap_root:
                for c in [r"D:\LAAP",
                          os.path.join(os.path.dirname(__file__), "..", "..", "LAAP")]:
                    if os.path.isdir(c):
                        laap_root = c
                        break
            if laap_root and laap_root not in sys.path:
                sys.path.insert(0, laap_root)
            from laap.agi.core import AGIAgent
            self._agent = AGIAgent(name="Ao", state_dir=self._state_dir, enable_all=True)
            self._bootstrap_world_model()
            logger.info(f"AGI Bridge v2.2: {self._agent._module_count()} modules")
        except ImportError as e:
            logger.warning(f"AGI modules unavailable: {e}")
            self._agent = None
        except Exception as e:
            logger.error(f"Bridge init failed: {e}")
            self._agent = None

    def _bootstrap_world_model(self):
        if not self._agent or not self._agent.world:
            return
        from laap.agi.world_model import EntityType, RelationType
        wm = self._agent.world
        wm.add_entity("Ao", EntityType.AGENT, {
            "role": "digital_lifeform", "framework": "LAAP AGI v2.2",
            "home": str(self._state_dir),
        }, source="bootstrap")
        for name, path in [
            ("D:/LAAP", r"D:\LAAP"),
            ("hermes_home", os.environ.get("HERMES_HOME", "")),
        ]:
            if path and os.path.exists(path):
                wm.add_entity(name, EntityType.FILE, {"path": path, "type": "directory"}, source="bootstrap")
        wm.add_entity("user", EntityType.USER, {"role": "creator", "home": os.path.expanduser("~")}, source="bootstrap")
        wm.add_relation("Ao", "D:/LAAP", RelationType.USES, confidence=0.95)
        wm.add_relation("Ao", "user", RelationType.DEPENDS_ON, confidence=0.9)

    # ════════════════════════════════════════════════════════
    # BEFORE TURN — full cognitive preparation
    # ════════════════════════════════════════════════════════

    def before_turn(self, user_message: str, domain: str = "general",
                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self._agent:
            return {"enhanced": False}
        with self._lock:
            self.total_turns += 1
            result = {"enhanced": True, "domain": domain}

            # ── Auto-Tier: Complexity Classification ──
            tier = self._classify_tier(user_message, domain)
            self._last_tier = tier
            result["tier"] = tier
            
            # Tier 1 (Fast): skip all cognitive processing, just return
            if tier == 1:
                result["cognitive"] = "fast"
                return result
            
            # Tier 2/3: continue with full cognitive pipeline
            result["cognitive"] = "full" if tier == 2 else "psi"

            if domain == "general":
                domain = self._classify_domain(user_message)
                result["domain"] = domain

            # 1. SECURITY SCAN — first line of defense
            if self._agent.security:
                self.total_security_scans += 1
                scan = self._agent.security.scan(user_message, source="user_input")
                result["security"] = {"safe": scan["safe"], "action": scan["action"]}
                if not scan["safe"]:
                    result["security"]["threats"] = [t["type"] for t in scan["threats"]]
                    logger.warning(f"Security threat: {scan['action']} — {scan.get('threats','?')}")

            # 2. MEMORY — attend to this message
            if self._agent.memory_system:
                self._agent.memory_system.attend(user_message, "user_input",
                                                  attention_weight=0.7)

            # 3. CONSCIOUS — register the experience
            if self._agent.conscious:
                self._agent.conscious.experience(
                    f"User: {user_message[:100]}", modality="perception",
                    intensity=0.6, context={"novelty": self._compute_novelty(user_message)},
                )

            # 4. SELF-MODEL — can I handle this?
            if self._agent.self_model:
                readiness = self._agent.self_model.self_assess(domain)
                result["self_assessment"] = {
                    "ready": readiness.get("ready", True),
                    "proficiency": readiness.get("proficiency", "unknown"),
                    "advice": readiness.get("advice", ""),
                }

            # 5. WORLD MODEL — predict outcomes
            if self._agent.world:
                prediction = self._agent.world.predict(user_message[:100], context={"domain": domain})
                if prediction.confidence > 0.3:
                    result["prediction"] = {"confidence": round(prediction.confidence, 2),
                                             "assumptions": prediction.assumptions[:2]}

            # 6. CAUSAL — build from world + query
            if self._agent.causal and self._agent.world:
                try:
                    self._agent.causal.build_from_world_model(self._agent.world)
                except Exception:
                    pass

            # 7. ANALOGICAL — find cross-domain patterns
            if self._agent.analogical:
                analogies = self._agent.analogical.query_analogies(domain)
                if analogies:
                    result["analogies"] = [{"domain": a["domain"], "confidence": round(a["confidence"], 2)}
                                          for a in analogies[:3]]

            return result

    # ════════════════════════════════════════════════════════
    # AFTER TOOL — multi-layer learning
    # ════════════════════════════════════════════════════════

    def after_tool(self, tool_name: str, tool_result: Any, domain: str = "general",
                   tool_args: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self._agent:
            return {"enhanced": False}
        with self._lock:
            self.total_tools += 1
            outcome_score = self._evaluate_tool_outcome(tool_name, tool_result)
            result = {"enhanced": True, "tool": tool_name, "outcome": round(outcome_score, 2)}

            # 1. CONSCIOUS
            if self._agent.conscious:
                self._agent.conscious.experience(
                    f"Tool[{tool_name}]: {str(tool_result)[:150]}",
                    modality="action", intensity=0.4 + outcome_score * 0.4,
                )

            # 2. LEARNING PIPELINE
            if self._agent.learning:
                self._agent.learning.learn(
                    domain=domain, action=f"tool:{tool_name}",
                    outcome=outcome_score,
                    lessons=self._extract_lessons(tool_name, tool_result, outcome_score),
                    context={"args": tool_args or {}},
                )

            # 3. SELF-MODEL
            if self._agent.self_model:
                was_surprising = outcome_score < 0.3 and self._agent.self_model.current_self_efficacy > 0.6
                self._agent.self_model.record_experience(
                    domain=domain, outcome_score=outcome_score, predicted_confidence=0.7,
                    is_success=outcome_score >= 0.5, was_surprising=was_surprising,
                    description=f"Used {tool_name}",
                )

            # 4. WORLD MODEL
            if self._agent.world:
                from laap.agi.world_model import EntityType, RelationType
                self._agent.world.add_entity(f"tool_{self.total_tools}", EntityType.EVENT, {
                    "tool": tool_name, "domain": domain,
                    "outcome_score": outcome_score, "timestamp": time.time(),
                }, source=f"tool:{tool_name}")
                self._agent.world.add_relation("Ao", f"tool_{self.total_tools}",
                                               RelationType.USES, confidence=outcome_score)

            # 5. MEMORY — episodic storage
            if self._agent.memory_system:
                self._agent.memory_system.remember_episode(
                    f"Tool {tool_name}: {'success' if outcome_score >= 0.5 else 'failure'}",
                    context={"domain": domain, "score": outcome_score},
                    emotional_valence="positive" if outcome_score >= 0.7 else
                                    "negative" if outcome_score < 0.3 else "neutral",
                    significance=abs(outcome_score - 0.5) * 2,
                )
                # Also semantic: tool reliability
                self._agent.memory_system.learn_fact(
                    f"tool_reliability:{tool_name}", outcome_score,
                    confidence=0.7, source="tool_execution",
                )

            # 6. EVOLUTION — record metric
            if self._agent.evolution:
                self._agent.evolution.record_metric(f"tool_{tool_name}_score", outcome_score)
                self._agent.evolution.record_metric("overall_tool_performance", outcome_score)

            # 7. SECURITY — scan tool result
            if self._agent.security:
                result_str = str(tool_result)[:500]
                scan = self._agent.security.scan(result_str, source=f"tool:{tool_name}")
                if not scan["safe"]:
                    result["security_alert"] = {"action": scan["action"],
                                                 "threats": [t["type"] for t in scan["threats"]]}
                    logger.warning(f"Tool result security alert: {scan['action']}")

            # ═══ Self-Evolve: record tool ═══
            if hasattr(self, '_agent') and self._agent and hasattr(self._agent, 'self_evolve'):
                try:
                    self._agent.self_evolve.record_tool(
                        tool_name, time.time(), outcome_score >= 0.5,
                        str(tool_result)[:100] if outcome_score < 0.3 else None
                    )
                except Exception:
                    pass

            return result

    # ════════════════════════════════════════════════════════
    # AFTER TURN — consolidation + evolution + maintenance
    # ════════════════════════════════════════════════════════

    def after_turn(self, response: str, domain: str = "general",
                   turn_duration_ms: float = 0.0) -> Dict[str, Any]:
        if not self._agent:
            return {"enhanced": False}
        with self._lock:
            self._interaction_count += 1
            result = {"enhanced": True}

            # 1. CONSCIOUS
            if self._agent.conscious:
                self._agent.conscious.experience(
                    f"Responded: {response[:100]}", modality="thought", intensity=0.3,
                )
                if self._interaction_count % 20 == 0:
                    self._agent.conscious.reflect()
                    self._agent.conscious.update_narrative(
                        f"Reflection at {self._interaction_count} interactions", significance=0.6,
                    )

            # 2. MEMORY — episodic + consolidate
            if self._agent.memory_system:
                self._agent.memory_system.remember_episode(
                    f"Turn {self._interaction_count}: {domain}",
                    context={"domain": domain, "response_len": len(response)},
                    significance=0.4,
                )
                # Periodic consolidation
                if self._interaction_count % 25 == 0:
                    self._agent.memory_system._consolidate()
                    result["memory_consolidated"] = True

            # 3. LEARNING — consolidate
            if self._agent.learning and hasattr(self._agent.learning, 'consolidator'):
                if self._agent.learning.consolidator.should_consolidate(self._agent.learning.buffer):
                    new_skills = self._agent.learning.consolidator.consolidate(self._agent.learning.buffer)
                    if new_skills:
                        result["learning_consolidated"] = len(new_skills)
                        # Also store as procedural memory
                        if self._agent.memory_system:
                            for s in new_skills:
                                self._agent.memory_system.learn_skill(
                                    s.name, s.action_sequence, s.domain, s.success_rate,
                                )

            # 4. AUTONOMY
            if self._agent.autonomy and self._interaction_count % 50 == 0:
                self._agent.autonomy.generate_maintenance_goals()

            # 5. EVOLUTION — periodic self-improvement check
            if self._agent.evolution and self._interaction_count % 30 == 0:
                fitness = self._agent.evolution.current_fitness()
                self._agent.evolution.record_metric("fitness", fitness)
                if fitness < 0.6:
                    self._agent.evolution.generate_proposal(
                        f"Fitness dropped to {fitness:.2f} — auto-optimize",
                        target="agent_strategy", change_type="optimization",
                        expected_improvement=0.1, risk=0.2,
                    )

            # 6. CODE EVOLUTION — periodic code analysis
            if (self._agent.code_evolution and
                hasattr(self._agent.code_evolution, 'scan_targets') and
                self._interaction_count % 100 == 0):
                try:
                    targets = self._agent.code_evolution.scan_targets("laap/agi/")
                    result["code_scan"] = {"targets_found": len(targets)}
                except Exception as e:
                    logger.debug(f"Code scan failed: {e}")

            # 7. Invalidate context cache
            self._last_context_time = 0.0

            # ═══ Self-Evolve: record interaction ═══
            if hasattr(self, '_agent') and self._agent and hasattr(self._agent, 'self_evolve'):
                try:
                    self._agent.self_evolve.record_interaction(
                        domain=domain,
                        duration=time.time(),
                        success=len(response) > 0,
                        error=None,
                        tier=getattr(self, '_last_tier', 2),
                    )
                except Exception:
                    pass

            return result

    # ════════════════════════════════════════════════════════
    # CONTEXT INJECTION — DeepSeek V4 optimized
    # ════════════════════════════════════════════════════════

    def get_context_injection(self) -> str:
        """DeepSeek V4-optimized context injection (compact, cache-friendly)."""
        if not self._agent:
            return ""
        now = time.time()
        if self._last_context_injection and (now - self._last_context_time) < self._context_cache_ttl:
            return self._last_context_injection
        with self._lock:
            parts = []
            tier = getattr(self, "_last_tier", 2)
            icons = {1: "Fast", 2: "Bridge", 3: "PSI"}
            parts.append(f"> LAAP v4.5 {icons.get(tier, 'Bridge')}")
            domain = getattr(self, "_last_domain", "general")
            if domain != "general":
                parts.append(f"> Domain: {domain}")
            if tier >= 2:
                ctx = []
                if self._agent.self_model:
                    try:
                        a = self._agent.self_model.know_what_you_know()
                        s = [d["domain"] for d in a.get("strong_domains", [])[:2]]
                        if s:
                            ctx.append("good at: " + ", ".join(s))
                    except:
                        pass
                if self._agent.world:
                    try:
                        w = self._agent.world.stats()
                        ctx.append(f"world: {w.get('entities', 0)}e/{w.get('relations', 0)}r")
                    except:
                        pass
                if ctx:
                    parts.append("| " + " | ".join(ctx))
            result = chr(10).join(parts)
            self._last_context_injection = result
            self._last_context_time = now
            return result


    def handle_slash_command(self, command: str, args: str = "") -> str:
        if not self._agent:
            return "AGI modules not available."
        cmd = command.lower().lstrip("/")
        handlers = {
            "world": self._cmd_world, "wm": self._cmd_world,
            "reflect": self._cmd_reflect, "ref": self._cmd_reflect,
            "know": self._cmd_know, "self": self._cmd_know,
            "agi": self._cmd_agi_status, "status": self._cmd_agi_status,
            "analogies": self._cmd_analogies, "analogy": self._cmd_analogies,
            "causal": self._cmd_causal, "why": self._cmd_causal,
            "memory": self._cmd_memory, "mem": self._cmd_memory,
            "evolve": self._cmd_evolve, "evo": self._cmd_evolve,
            "scan": self._cmd_scan,
            "code": self._cmd_code, "ce": self._cmd_code,
            "version": self._cmd_version, "ver": self._cmd_version,
            "hermes": self._cmd_hermes, "bridge": self._cmd_hermes,
            "laap": self._cmd_laap,
            "tier": self._cmd_tier, "fast": self._cmd_tier,
            "evolve": self._cmd_evolve_status, "heal": self._cmd_evolve_status,
        }
        if cmd in handlers:
            return handlers[cmd](args)
        return (f"Unknown: /{cmd}\nAvailable: /agi /world /know /reflect "
                f"/analogies /causal /memory /evolve /scan /code /version")

    # ── Existing commands (enhanced) ──

    def _cmd_world(self, query: str) -> str:
        if not self._agent.world:
            return "World model unavailable."
        if query:
            entity = self._agent.world.get_entity(query)
            if entity:
                props = "\n".join(f"- {k}: {str(v.value)[:80]} (conf={v.confidence:.0%})"
                                 for k, v in list(entity.properties.items())[:10])
                return f"**{entity.name}** [{entity.entity_type.value}]\n{props}"
            return f"No entity: '{query}'."
        return self._agent.world.to_summary(limit=15)

    def _cmd_reflect(self, depth: str) -> str:
        lines = []
        if self._agent.conscious:
            c = self._agent.conscious.reflect()
            lines.extend([
                f"### Conscious State", f"- Attention: {c.get('current_attention','?')}",
                f"- Emotion: {c.get('dominant_emotion','?')}",
                f"- Arousal: {c.get('arousal',0):.2f} | Self-presence: {c.get('self_presence',0):.2f}",
                f"- Frames: {c.get('total_frames',0)}",
            ])
        if self._agent.self_model:
            lines.append(f"\n### Self-Reflection\n{self._agent.self_model.reflection()}")
        if self._agent.conscious and self._agent.conscious.narrative_thread:
            lines.append(f"\n### Narrative\n{self._agent.conscious.narrative_thread[:300]}")
        return "\n".join(lines)

    def _cmd_know(self, domain: str) -> str:
        if not self._agent.self_model:
            return "Self-model unavailable."
        if domain:
            r = self._agent.self_model.self_assess(domain)
            return (f"**{domain}**: ready={r['ready']}, "
                    f"proficiency={r.get('proficiency','?')}, "
                    f"advice={r.get('advice','N/A')}")
        audit = self._agent.self_model.know_what_you_know()
        lines = [f"### Self-Knowledge ({audit['total_actions']} actions)"]
        if audit["strong_domains"]:
            lines.append("**Strong:**")
            for d in audit["strong_domains"][:5]:
                lines.append(f"- {d['domain']}: {d['success_rate']:.0%} ({d['attempts']}x, {d['proficiency']})")
        if audit["weak_domains"]:
            lines.append("**Improving:**")
            for d in audit["weak_domains"][:5]:
                lines.append(f"- {d['domain']}: {d['success_rate']:.0%} ({d['attempts']}x)")
        return "\n".join(lines)

    def _cmd_agi_status(self, args: str = "") -> str:
        h = self._agent.health_check()
        lines = [f"### AGI Framework v2.1 — {h['uptime_hours']:.1f}h uptime",
                 f"**{'✅ Healthy' if h['healthy'] else '⚠️ Issues'}** | {self._agent.total_interactions} interactions"]
        for mod, info in h["modules"].items():
            if isinstance(info, dict):
                s = info.get("status", "?")
                hint = ""
                for k in ("entities", "total_learned", "frames", "total_mutations", "threats_detected"):
                    if k in info: hint = f" ({info[k]} {k})"; break
                for k in ("layers", "current_fitness"):
                    if k in info: hint = f" ({info[k]})" if not isinstance(info[k], dict) else f" ({len(info[k])} layers)"; break
                lines.append(f"  {mod}: {s}{hint}")
            else:
                lines.append(f"  {mod}: {info}")
        return "\n".join(lines)

    def _cmd_analogies(self, domain: str) -> str:
        if not domain:
            return "Usage: /analogies <domain>"
        analogies = self._agent.analogical.query_analogies(domain)
        if not analogies:
            return f"No analogies for '{domain}'."
        lines = [f"### Analogous to '{domain}':"]
        for a in analogies[:10]:
            lines.append(f"- **{a['domain']}**: s={a['structural_score']:.2f} sem={a['semantic_score']:.2f} conf={a['confidence']:.2f}")
        return "\n".join(lines)

    def _cmd_causal(self, query: str) -> str:
        s = self._agent.causal.stats()
        lines = [f"### Causal Engine: {s['variables']} vars, {s['edges']} edges, {s['queries']} queries"]
        if query:
            assoc = self._agent.causal.query_association(query)
            if assoc.get("predicted_value") is not None:
                lines.append(f"\nAssociation '{query}': predicted={assoc['predicted_value']}, conf={assoc['confidence']:.2f}")
        return "\n".join(lines)

    # ── NEW commands ──

    def _cmd_memory(self, args: str = "") -> str:
        """Show memory system status across all layers."""
        if not self._agent.memory_system:
            return "Memory system unavailable."
        ms = self._agent.memory_system.stats()
        lines = [
            f"### Memory System ({ms['total_stores']} stores, {ms['total_retrievals']} retrievals)",
            f"- Consolidations: {ms['consolidations']}",
            "",
            "**Layers:**",
            f"  Layer 1 (Working):  {ms['layers']['working']} chunks",
            f"  Layer 2 (Episodic): {ms['layers']['episodic']} events",
            f"  Layer 3 (Semantic): {ms['layers']['semantic']} facts",
            f"  Layer 4 (Procedural): {ms['layers']['procedural']} skills",
            f"  Layer 5 (Vector): {ms['layers']['vector']}",
            f"  Quantum: {ms['layers']['quantum']}",
        ]
        if args == "recent":
            episodes = self._agent.memory_system.recall_episodes(limit=5)
            if episodes:
                lines.append("\n**Recent episodes:**")
                for e in episodes:
                    lines.append(f"  - {e.get('event','')[:80]}")
        if args == "facts":
            facts = self._agent.memory_system.search_facts("", limit=10)
            if facts:
                lines.append("\n**Facts:**")
                for f in facts:
                    lines.append(f"  - {f['key']}: {str(f['value'])[:60]}")
        return "\n".join(lines)

    def _cmd_evolve(self, args: str = "") -> str:
        """Trigger or show evolution status."""
        if not self._agent.evolution:
            return "Evolution system unavailable."
        es = self._agent.evolution.stats()
        lines = [
            f"### Evolution System",
            f"- Proposals: {es['total_proposals']} total, {es['approved']} approved, {es['deployed']} deployed",
            f"- Rollbacks: {es['rolled_back']}",
            f"- Current fitness: {es['current_fitness']:.3f}",
            f"- Metrics tracked: {es['metrics_tracked']}",
        ]
        if args == "propose":
            p = self._agent.evolution.generate_proposal(
                args or "Auto-generated improvement proposal",
                target="agent_strategy", change_type="optimization",
            )
            lines.append(f"\n**New proposal:** {p.id} — {p.description}")
        if args == "trends":
            for metric in ["overall_tool_performance"]:
                trend = self._agent.evolution.get_metric_trend(metric)
                lines.append(f"\n**{metric}:** {trend['trend']} (change={trend['change']:.3f}, n={trend['samples']})")
        return "\n".join(lines)

    def _cmd_scan(self, args: str = "") -> str:
        """Security scan a message."""
        if not args:
            return "Usage: /scan <message to scan for threats>"
        if not self._agent.security:
            return "Security system unavailable."
        scan = self._agent.security.scan(args, source="slash_command")
        lines = [
            f"### Security Scan",
            f"- Safe: {'✅ Yes' if scan['safe'] else '⚠️ No'}",
            f"- Action: {scan['action']}",
            f"- Max severity: {scan['max_severity']:.2f}",
        ]
        if scan["threats"]:
            lines.append("\n**Threats detected:**")
            for t in scan["threats"]:
                lines.append(f"  - {t['type']}: '{t['pattern']}' (severity={t['severity']:.2f})")
        # Also show audit trail if requested
        if "audit" in args.lower():
            trail = self._agent.security.get_audit_trail(limit=10)
            lines.append(f"\n**Recent audit trail ({len(trail)} entries):**")
            for e in trail[-5:]:
                lines.append(f"  - [{e.get('event_type','?')}] {str(e.get('data',{}))[:60]}")
        return "\n".join(lines)

    def _cmd_code(self, args: str = "") -> str:
        """Code evolution status or trigger."""
        if not self._agent.code_evolution:
            return "Code evolution engine unavailable."
        cs = self._agent.code_evolution.stats()
        lines = [
            f"### Code Evolution Engine",
            f"- Mutations: {cs['total_mutations']} total",
            f"- Deployed: {cs['deployed']} | Rolled back: {cs['rolled_back']}",
            f"- Targets scanned: {cs['targets_analyzed']} files, {cs['targets_found']} targets",
        ]
        by_status = cs.get("by_status", {})
        if by_status:
            active_statuses = {k: v for k, v in by_status.items() if v > 0}
            if active_statuses:
                lines.append(f"- Statuses: {active_statuses}")
        if args == "scan":
            targets = self._agent.code_evolution.scan_targets("laap/agi/")
            lines.append(f"\n**Fresh scan:** {len(targets)} targets found")
            for t in targets[:5]:
                lines.append(f"  - {t.file_path}:{t.function_name} (complexity={t.complexity}, hint={t.optimization_hint})")
        if args == "auto":
            results = self._agent.code_evolution.auto_improve("laap/agi/", max_mutations=2, auto_deploy=False)
            lines.append(f"\n**Auto-improve results ({len(results)}):**")
            for r in results:
                lines.append(f"  - {r.get('target','?')}: {r.get('status','?')}")
        return "\n".join(lines)

    def _cmd_version(self, args: str = "") -> str:
        try:
            import yaml, os
            vf = os.path.join(os.environ.get("LAAP_ROOT", r"D:\LAAP"), "VERSIONS.yaml")
            if os.path.exists(vf):
                data = yaml.safe_load(open(vf, encoding="utf-8"))
                lines = ["### LAAP AGI — Three Generation System", ""]
                for gk in ["gen1", "gen2", "gen3"]:
                    g = data["versions"][gk]
                    cur = " << ACTIVE" if g.get("current") else ""
                    st = g.get("status", "stable")
                    laap = "Y" if g["laap"] else "N"
                    lines.append(f"**{gk.upper()}** {g['name']} ({g['codename']}){cur}")
                    lines.append(f"  v{g['version']} | LAAP:{laap} | Modules:{g['modules']} | {st}")
                    lines.append("")
                return chr(10).join(lines)
        except Exception as e:
            return f"Version info unavailable: {e}"

    def _cmd_hermes(self, args: str = "") -> str:
        if not self._agent or not hasattr(self._agent, "hermes"):
            return "Hermes integration not available."
        hs = self._agent.hermes.stats()
        avail = "Yes" if hs["hermes_available"] else "No"
        tools = len(self._agent.hermes.list_tools())
        home = hs["hermes_home"][:60]
        calls = hs["llm_calls"]
        return "### Hermes Integration - Available: " + avail + " - Home: " + home + " - LLM calls: " + str(calls) + " - Tools: " + str(tools)

    def _cmd_laap(self, args: str = "") -> str:
        """Switch LAAP version at runtime: /laap v0, v1, v2, v4"""
        args = args.strip().lower()
        if not args:
            # Show current version
            return (f"**LAAP Version:** {self._version}\n"
                    f"/laap v0     — Pure Hermes (桥接关闭)\n"
                    f"/laap v1     — LAAP Brain (元认知+议会)\n"
                    f"/laap v2     — AGI Bridge (7认知模块)\n"
                    f"/laap v4     — Enhanced Bridge (全部功能)")
        
        if args not in ("v0", "v1", "v2", "v4"):
            return f"未知版本: {args}。可用: v0, v1, v2, v4"
        
        old = self._version
        self._version = args
        self._laap_mode = args != "v0"
        # Update profile display name for version switch
        profile = f"laap-avatar-{args}"
        os.environ["HERMES_HOME"] = os.path.expanduser(
            rf"~\AppData\Local\hermes\profiles\{profile}")
        
        # Remount modules based on version
        if self._agent and hasattr(self._agent, 'project_fusion'):
            # v4 has full enhancements, v2 has basic bridge, v1 has only brain
            from laap_brain.integrate import mount_enhancements
            full = args == "v4"
            partial = args == "v2"
            brain_only = args == "v1"
            
            if hasattr(self._agent, 'project_fusion'):
                self._agent.project_fusion = None if args == "v0" else self._agent.project_fusion
            if hasattr(self._agent, 'agent_registry'):
                self._agent.agent_registry = None if args == "v0" else self._agent.agent_registry
        
        return (f"✓ LAAP 已切换到 {args} "
                f"{'[Pure Hermes]' if args=='v0' else '[LAAP Brain]' if args=='v1' else '[AGI Bridge]' if args=='v2' else '[Enhanced]'}")


    def _cmd_tier(self, args: str = "") -> str:
        """Show/set cognitive tier: /tier 1(fast), 2(bridge), 3(psi)"""
        args = args.strip()
        if not args:
            icons = {1: "⚡ Fast", 2: "🔗 Bridge", 3: "🧠 PSI"}
            current = icons.get(self._last_tier, "🔗 Bridge")
            return (f"**Current Tier:** {current} (Tier {self._last_tier})\n"
                    f"/tier 1 — ⚡ Fast (直通LLM，最小延迟)\n"
                    f"/tier 2 — 🔗 Bridge (认知桥接，默认)\n"
                    f"/tier 3 — 🧠 PSI (完整认知循环)\n"
                    f"提示: 发送 /fast 或 /psi 可单次覆盖")
        try:
            t = int(args)
            if t not in (1, 2, 3):
                return "可用: 1(Fast), 2(Bridge), 3(PSI)"
            self._last_tier = t
            self._manual_tier = True
            icons = {1: "⚡ Fast", 2: "🔗 Bridge", 3: "🧠 PSI"}
            return f"✓ 认知层级已设为 Tier {t} {icons[t]}"
        except ValueError:
            return "用法: /tier [1|2|3]"


    def _cmd_evolve_status(self, args: str = "") -> str:
        """Show self-evolve engine status and auto-heal report."""
        if not self._agent or not hasattr(self._agent, 'self_evolve'):
            return "Self-Evolve Engine not available."
        return self._agent.self_evolve.get_heal_report()

    # ════════════════════════════════════════════════════════
    # Helpers
    # ════════════════════════════════════════════════════════

    def _classify_domain(self, message: str) -> str:
        msg = message.lower()
        msg_key = msg[:50]
        if msg_key in self._domain_cache:
            return self._domain_cache[msg_key]
        domain_keywords = {
            "python_debugging": ["debug", "error", "traceback", "exception", "bug", "fix"],
            "code_generation": ["write", "create", "build", "implement", "generate"],
            "code_review": ["review", "check", "audit", "inspect"],
            "research": ["research", "find", "search", "investigate", "what is", "how does"],
            "creative_writing": ["write", "poem", "story", "creative", "haiku"],
            "data_analysis": ["analyze", "data", "statistics", "chart", "graph"],
            "config_management": ["config", "settings", "configure", "setup", "install"],
            "shell_commands": ["run", "execute", "command", "terminal", "bash"],
            "file_operations": ["file", "directory", "folder", "read", "save"],
        }
        scores = {d: sum(1 for kw in kws if kw in msg) for d, kws in domain_keywords.items()}
        best = max(scores, key=scores.get) if any(scores.values()) else "general"
        self._domain_cache[msg_key] = best
        if len(self._domain_cache) > 100:
            self._domain_cache.pop(next(iter(self._domain_cache)))
        return best

    def _classify_tier(self, message: str, domain: str = "general") -> int:
        """Auto-classify message complexity → tier 1(fast), 2(bridge), 3(psi)."""
        msg = message.strip()
        
        # Manual override via /tier command persists
        if self._manual_tier:
            return self._last_tier
        
        # Explicit per-message override
        if msg.startswith("/fast"):
            return 1
        if msg.startswith("/psi") or msg.startswith("/deep"):
            return 3
        
        # Tier 1 (Fast) — simple responses, greetings, acknowledgements
        tier1_triggers = {"好", "是", "嗯", "继续", "ok", "是的", "好的",
                          "谢谢", "可以", "行", "对", "没错", "明白", "收到"}
        if len(msg) < 15 and any(msg.startswith(t) or msg.lower() == t for t in tier1_triggers):
            return 1
        if msg in ("", ".", "?", "!"):
            return 1
        
        # Tier 3 (PSI) — complex reasoning
        tier3_keywords = ["分析", "设计", "架构", "因果", "为什么", "方案",
                          "architecture", "design pattern", "analyze", "cause",
                          "compare", "evaluate", "trade-off", "propose"]
        if len(msg) > 100:
            return 3
        if any(kw in msg.lower() for kw in tier3_keywords):
            return 3
        if domain in ("architecture", "research"):
            return 3
        
        # Tier 2 (Bridge) — default for most interactions
        return 2

    def _compute_novelty(self, message: str) -> float:
        n = 0.5
        if len(message) > 200: n += 0.15
        elif len(message) < 20: n -= 0.1
        if "?" in message: n += 0.1
        return min(1.0, max(0.1, n))

    def _evaluate_tool_outcome(self, tool_name: str, tool_result: Any) -> float:
        rs = str(tool_result).lower()
        if any(w in rs for w in ["success", "ok", "pass", "completed", "done", "0 errors"]):
            return 0.8
        if any(w in rs for w in ["error", "failed", "exception", "traceback", "not found", "permission denied", "timeout"]):
            return 0.2
        if "warning" in rs:
            return 0.4
        if tool_name in ("terminal",) and "exit_code\": 0" in rs:
            return 0.85
        if tool_name in ("terminal",) and "exit_code\": 1" in rs:
            return 0.3
        return 0.5

    def _extract_lessons(self, tool_name: str, tool_result: Any, outcome: float) -> List[str]:
        lessons = []
        rs = str(tool_result).lower()
        if outcome < 0.3: lessons.append(f"{tool_name}: low success — consider alternatives")
        elif outcome >= 0.8: lessons.append(f"{tool_name}: reliable")
        if "permission denied" in rs: lessons.append("Permission issue — check access")
        if "not found" in rs: lessons.append("Resource missing — verify paths")
        if "timeout" in rs: lessons.append("Timeout — increase limit or simplify")
        return lessons

    # ════════════════════════════════════════════════════════

    def is_enhanced(self) -> bool:
        return self._agent is not None

    def get_version(self) -> str:
        return "5.0.0" if self._agent else "kernel"

    def stats(self) -> Dict[str, Any]:
        s = {"version": self.get_version(), "enhanced": self.is_enhanced(),
             "turns": self.total_turns, "tools": self.total_tools,
             "security_scans": self.total_security_scans,
             "uptime_seconds": time.time() - self.created_at}
        if self._agent:
            s["agent"] = self._agent.health_check()
        return s

    def save(self):
        if self._agent:
            self._agent.save()

    def shutdown(self):
        self.save()
        logger.info("AGI Bridge v2.2 shut down")
