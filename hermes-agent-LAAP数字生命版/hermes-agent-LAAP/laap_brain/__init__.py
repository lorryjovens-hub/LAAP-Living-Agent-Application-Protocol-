# LAAP Brain — PSI-Driven Cognitive Kernel for Hermes Agent
"""
LAAP Kernel v4.5 (PSI-Driven) — 认知核心，嵌入 Hermes Agent 作为传输层

Modules:
  kernel.py          — LAAPKernel: PSI-driven main loop
  psi_driver.py      — PSIDriver: perceive→select→integrate→act→learn
  multi_agent.py     — AgentRegistry + EventBus + SafeRollback
  evolution_engine.py — GitHubFusion + LearningLoop + MemoryOptimizer
  agi_bridge.py      — Legacy bridge (v3.x compatibility)
  integrate.py       — Legacy monkey-patch (v3.x compatibility)

Usage:
    from laap_brain.kernel import LAAPKernel
    kernel = LAAPKernel()
    kernel.run()
"""

from __future__ import annotations
import json, logging, time, uuid, math, hashlib, random, threading, queue
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("laap_brain")
LAAP_VERSION = "5.0.0"


# ── 通用增强入口 ────────────────────────────────────────────

def enhance(agent: Any = None) -> "LaapBrain":
    """一行代码让任何智能体获得认知能力"""
    from laap_brain import LaapBrain as LB
    global _enhance_instance
    if agent is not None and hasattr(agent, 'laap_brain'):
        return agent.laap_brain
    if _enhance_instance is not None:
        return _enhance_instance
    if agent is not None:
        try:
            from laap_brain.integrate import install_laap
            install_laap()
            if hasattr(agent, 'laap_brain'):
                return agent.laap_brain
        except Exception:
            pass
    _enhance_instance = LB(agent=agent)
    return _enhance_instance


def is_laap_enhanced(agent: Any = None) -> bool:
    # Kernel v4 check
    try:
        from laap_brain.kernel import LAAPKernel
        return True
    except:
        pass
    # Legacy v3 check
    if agent is None:
        return _enhance_instance is not None
    return getattr(agent, 'laap_brain', None) is not None


def quick_check(agent: Any = None) -> str:
    s = "LAAP 未激活 (调用 enhance())"
    brain = agent if isinstance(agent, LaapBrain) else (
        getattr(agent, 'laap_brain', None) if agent is not None else _enhance_instance
    )
    if brain:
        s2 = brain.status()
        s = f"LAAP v{s2['version']} | 轮次{s2['turns']} 工具{s2['tools']} | 元认知{s2['meta']['mode']} 议会{s2['parliament']['members']}人 技能{s2['unity']['skills']}个 知行差距{s2['unity']['avg_gap']}"
    return s


def detect_variant(agent: Any = None) -> str:
    if is_laap_enhanced(agent):
        return "laap_enhanced"
    import os as _os
    if _os.environ.get("HERMES_LAAP_ENABLED") == "1":
        return "laap_enhanced"
    return "vanilla"


# ── 元认知 ──────────────────────────────────────────────────

class ThinkingMode(Enum):
    INTUITIVE = "intuitive"; DELIBERATE = "deliberate"
    ANALYTICAL = "analytical"; CREATIVE = "creative"
    REFLECTIVE = "reflective"; EXPLORATORY = "exploratory"


@dataclass
class CognitiveTrace:
    episode: int = 0; trigger: str = ""
    mode: str = "intuitive"; confidence: float = 0.5
    biases: List[str] = field(default_factory=list)
    outcome: Optional[float] = None; duration_ms: float = 0.0


class MetaCognition:
    _BIAS_PATTERNS = {"overconfidence": ["绝对","definitely","100%","always","never","毫无疑问","absolutely","certainly","必须是","一定是"],
                      "confirmation": ["我认为","我觉得","clearly","obviously"],
                      "anchoring": ["baseline","基准","默认","original","本来"]}

    def __init__(self):
        self.mode = ThinkingMode.INTUITIVE
        self.traces: List[CognitiveTrace] = []
        self._bias_risk: Dict[str, float] = {}
        self._episode = 0
        self.bias_corrections = 0

    def before_decision(self, task: str) -> Dict:
        self._episode += 1; task_l = task.lower(); warnings = []
        for bias, patterns in self._BIAS_PATTERNS.items():
            if any(p in task_l for p in patterns):
                self._bias_risk[bias] = min(1.0, self._bias_risk.get(bias, 0) + 0.2)
                if self._bias_risk[bias] > 0.5: warnings.append(bias)
        task_type = "general"
        if any(k in task_l for k in ["bug","fix","error","debug","故障","崩溃"]): task_type = "debug"
        elif any(k in task_l for k in ["analyze","analysis","分析","评估","检查"]): task_type = "analysis"
        elif any(k in task_l for k in ["search","find","搜索","查找","探索"]): task_type = "explore"
        elif any(k in task_l for k in ["write","create","生成","创建","run","运行"]): task_type = "execute"
        return {"warnings": warnings, "task_type": task_type}

    def after_decision(self, task: str, confidence: float, outcome: float):
        self.traces.append(CognitiveTrace(episode=self._episode, trigger=task[:40], mode=self.mode.value,
                                          confidence=confidence, biases=[k for k,v in self._bias_risk.items() if v>0.5], outcome=outcome))
        if len(self.traces) > 100: self.traces = self.traces[-100:]

    def status(self) -> dict:
        return {"mode": self.mode.value, "traces": len(self.traces), "biases_corrected": self.bias_corrections}


# ── 议会 ────────────────────────────────────────────────────

@dataclass
class Opinion:
    role: str = ""; stance: str = ""; argument: str = ""
    confidence: float = 0.5; weight: float = 1.0

@dataclass
class Deliberation:
    topic: str = ""; opinions: List[Opinion] = field(default_factory=list)
    final_decision: str = ""; confidence: float = 0.0

_ROLE_STANCES = {"理性": lambda t: ("分析",f"需要更多数据: {t[:30]}",0.6),
                 "想象": lambda t: ("探索",f"有创新可能: {t[:30]}",0.5),
                 "守护": lambda t: ("谨慎","需要评估风险",0.7),
                 "实干": lambda t: ("执行",f"可以执行: {t[:30]}",0.6),
                 "质疑": lambda t: ("挑战","假设需要验证",0.5)}

class Parliament:
    def __init__(self):
        self.deliberations: List[Deliberation] = []
        self._weights: Dict[str, float] = {n: 1.0 for n in _ROLE_STANCES}

    def deliberate(self, topic: str, fast: bool = True) -> Deliberation:
        d = Deliberation(topic=topic)
        roles = ["理性","实干","质疑"] if fast else list(_ROLE_STANCES.keys())
        for role in roles:
            fn = _ROLE_STANCES[role]
            stance, arg, conf = fn(topic)
            d.opinions.append(Opinion(role=role, stance=stance, argument=arg, confidence=conf, weight=self._weights.get(role, 1.0)))
        support = sum(o.weight for o in d.opinions if o.stance in ("支持","执行","分析"))
        oppose = sum(o.weight for o in d.opinions if o.stance in ("反对","谨慎","拒绝"))
        d.confidence = support / max(1, support + oppose)
        d.final_decision = "执行" if d.confidence > 0.6 else "否决" if d.confidence < 0.3 else "重新评估"
        self.deliberations.append(d)
        return d

    def learn(self, topic: str, outcome: float):
        for d in self.deliberations:
            if d.topic == topic:
                for o in d.opinions:
                    agreement = outcome if o.stance in ("支持","执行","分析") else 1.0 - outcome
                    self._weights[o.role] = self._weights.get(o.role, 1.0) * (0.95 + 0.05 * agreement)
                return

    def summary(self, d: Deliberation) -> str:
        lines = [f"╔═ 议会: {d.topic[:30]} ═╗"]
        for o in d.opinions: lines.append(f"  [{o.role}] {o.stance}: {o.argument[:40]}")
        lines.append(f"  决议: {d.final_decision} (conf={d.confidence:.0%})")
        lines.append("╚" + "═"*20 + "╝")
        return "\n".join(lines)

    def status(self) -> dict:
        return {"members": len(_ROLE_STANCES), "deliberations": len(self.deliberations)}


# ── 第一性原理 ──────────────────────────────────────────────

class FirstPrinciples:
    _PRINCIPLES = {"同一律": "A=A", "排中律": "真或假", "因果": "相同原因→相同结果", "守恒": "信息不灭"}
    def analyze(self, problem: str) -> Dict:
        assumptions = []
        if "应该" in problem: assumptions.append("隐含价值判断")
        if "通常" in problem: assumptions.append("隐含统计概括")
        if len(problem) > 100: assumptions.append("信息过载")
        return {"assumptions": assumptions, "principles": list(self._PRINCIPLES.keys())[:3], "score": max(0.1, 0.5 - len(assumptions) * 0.1)}
    def status(self) -> dict: return {"principles": len(self._PRINCIPLES)}


# ── 知行合一引擎 ────────────────────────────────────────────

class SkillProficiency(Enum):
    UNKNOWN = "unknown"; AWARE = "aware"; NOVICE = "novice"
    PRACTITIONER = "practitioner"; EXPERT = "expert"; MASTER = "master"

@dataclass
class EmbodiedSkill:
    name: str = ""; cognitive_action: str = ""; description: str = ""
    proficiency: SkillProficiency = SkillProficiency.UNKNOWN
    use_count: int = 0; success_count: int = 0; avg_quality: float = 0.0

_UNITY_SKILLS = [
    EmbodiedSkill("文件分析", "analysis", "读取并分析文件", SkillProficiency.PRACTITIONER),
    EmbodiedSkill("代码调试", "debug", "隔离-分析-修复-验证", SkillProficiency.PRACTITIONER),
    EmbodiedSkill("信息搜索", "explore", "搜索和收集信息", SkillProficiency.EXPERT),
    EmbodiedSkill("代码生成", "execute", "生成和验证代码", SkillProficiency.NOVICE),
    EmbodiedSkill("数据探索", "explore", "探索数据模式", SkillProficiency.PRACTITIONER),
    EmbodiedSkill("性能优化", "debug", "分析和优化性能", SkillProficiency.NOVICE),
]

_UNITY_TRIGGER_MAP = {
    "analysis": ["分析","检查","评估","analyze","analysis","examine","review"],
    "debug": ["debug","bug","错误","修复","fix","故障","崩溃","不工作"],
    "explore": ["搜索","查找","探索","search","find","explore","discover"],
    "execute": ["生成","创建","运行","execute","run","create","write","implement"],
}

class UnityEngine:
    def __init__(self):
        self.skills: Dict[str, EmbodiedSkill] = {s.name: s for s in _UNITY_SKILLS}
        self._gap_sum = 0.0; self._gap_n = 0

    def select_skill(self, action: str, trigger: str) -> Optional[EmbodiedSkill]:
        candidates = [s for s in self.skills.values() if s.cognitive_action == action]
        if not candidates: return None
        triggers = _UNITY_TRIGGER_MAP.get(action, [])
        for s in candidates:
            if any(t in trigger.lower() for t in triggers): return s
        return max(candidates, key=lambda s: s.use_count) if candidates else None

    def decide(self, action: str, trigger: str) -> Dict:
        skill = self.select_skill(action, trigger)
        if skill:
            embodied = skill.proficiency in (SkillProficiency.EXPERT, SkillProficiency.MASTER)
            gap = 0.1 if embodied else 0.3 if skill.proficiency == SkillProficiency.PRACTITIONER else 0.6
            self._gap_sum += gap; self._gap_n += 1
            return {"skill": skill.name, "proficiency": skill.proficiency.value,
                    "gap": gap, "confidence": max(0.3, 0.8 - gap),
                    "readiness": "immediate" if embodied else "guided"}
        return {"skill": None, "proficiency": "unknown", "gap": 0.9, "confidence": 0.2, "readiness": "none"}

    def learn(self, skill_name: str, quality: float):
        skill = self.skills.get(skill_name)
        if not skill: return
        skill.use_count += 1
        if quality > 0.5: skill.success_count += 1
        skill.avg_quality = skill.avg_quality * 0.9 + quality * 0.1
        sr = skill.success_count / max(1, skill.use_count)
        if skill.use_count >= 20 and sr >= 0.9: skill.proficiency = SkillProficiency.MASTER
        elif skill.use_count >= 10 and sr >= 0.8: skill.proficiency = SkillProficiency.EXPERT
        elif skill.use_count >= 5 and sr >= 0.7: skill.proficiency = SkillProficiency.PRACTITIONER
        elif skill.use_count >= 1: skill.proficiency = SkillProficiency.NOVICE

    def know_thyself(self) -> Dict:
        return {n: {"proficiency": s.proficiency.value, "use": s.use_count,
                     "success_rate": f"{s.success_count/max(1,s.use_count):.0%}" if s.use_count else "N/A"}
                for n, s in self.skills.items()}

    def status(self) -> dict:
        return {"skills": len(self.skills), "avg_gap": round(self._gap_sum/max(1,self._gap_n), 3)}


# ── 可解释性 ────────────────────────────────────────────────

class Explainability:
    @staticmethod
    def to_html(trigger: str, action: str, confidence: float, reasoning: List[str]) -> str:
        return f"""<!DOCTYPE html><html><head><title>LAAP决策</title><style>
body{{font-family:'Segoe UI',sans-serif;background:#1a1a2e;color:#e0e0e0;padding:20px}}
.card{{background:#16213e;border-radius:12px;padding:20px;margin:10px 0}}
.phase{{border-left:3px solid #0f3460;padding-left:10px;margin:4px 0}}
</style></head><body><h1>LAAP 认知决策</h1>
<div class="card"><h3>{action}</h3><p>触发: {trigger[:60]}</p><p>置信度: {confidence:.2f}</p></div>
<div class="card"><h3>推理路径</h3>{''.join(f'<div class="phase">{r}</div>' for r in reasoning[-5:])}</div></body></html>"""


# ── EWC持续学习 ──────────────────────────────────────────────

class EWC:
    def __init__(self):
        self.fisher: Dict[str, float] = {}
        self.old_params: Dict[str, Any] = {}

    def before(self, skill_name: str, value: float):
        self.old_params[skill_name] = value

    def after(self, skill_name: str, new_value: float) -> float:
        old = self.old_params.get(skill_name, 0.5)
        if not isinstance(old, (int, float)): old = 0.5
        if not isinstance(new_value, (int, float)): new_value = 0.5
        fisher = self.fisher.get(skill_name, 0.1)
        penalty = fisher * (new_value - old) ** 2
        self.fisher[skill_name] = min(1.0, fisher + 0.05)
        return penalty

    def status(self) -> dict:
        return {"params": len(self.fisher), "mean_fisher": round(sum(self.fisher.values())/max(1,len(self.fisher)), 3)}


# ═══════════════════════════════════════════════════════════════
# LaapBrain — 统一入口
# ═══════════════════════════════════════════════════════════════

class LaapBrain:
    def __init__(self, agent: Any = None):
        self.agent = agent
        self.meta = MetaCognition()
        self.parliament = Parliament()
        self.fp = FirstPrinciples()
        self.unity = UnityEngine()
        self.explain = Explainability()
        self.ewc = EWC()
        self._turn_count = 0; self._tool_count = 0
        self._start_time = time.time()
        logger.info(f"LaapBrain v{LAAP_VERSION} initialized")

    def before_turn(self, user_message: str) -> Dict:
        self._turn_count += 1
        meta_info = self.meta.before_decision(user_message)
        action_type = meta_info.get("task_type", "general")
        deliberation = None
        if len(user_message) > 100 or any(k in user_message.lower() for k in ["delete","remove","修改","删除","deploy","publish"]):
            deliberation = self.parliament.deliberate(user_message[:60])
        unity_plan = self.unity.decide(action_type, user_message)
        if unity_plan.get("skill"):
            skill = self.unity.skills.get(unity_plan["skill"])
            if skill: self.ewc.before(unity_plan["skill"], skill.avg_quality)
        return {"meta": meta_info, "parliament": deliberation, "unity": unity_plan, "version": LAAP_VERSION}

    def after_tool(self, tool_name: str, result: Any):
        self._tool_count += 1
        quality = 0.8 if result and "error" not in str(result).lower() else 0.2
        for skill in self.unity.skills.values():
            if tool_name in skill.description or tool_name in skill.name:
                self.unity.learn(skill.name, quality)
                self.ewc.after(skill.name, skill.avg_quality)
                break

    def after_turn(self, response: str):
        ok = response and len(response) > 10
        self.meta.after_decision("turn", 0.6 if response else 0.0, 0.7 if ok else 0.2)

    def get_prompt_block(self) -> str:
        parts = ["[=== LAAP 认知状态 ===]", self.meta.status(), self._fmt_skills(self.unity.know_thyself()),
                 "[=== 第一性原理提示 ===]", "当遇到瓶颈时: 1)挑战假设 2)分解到基本真理 3)从零重建"]
        return "\n".join(str(p) for p in parts if p)

    def _fmt_skills(self, skills: Dict) -> str:
        return "\n".join(["[具身技能]"] + [f"  {n}: {s['proficiency']} (使用{s['use']}次, 成功率{s['success_rate']})" for n, s in skills.items()])

    def handle_command(self, cmd: str, args: str = "") -> str:
        if cmd in ("/brain","/cognition"): return self._cmd_status()
        elif cmd == "/reflect": return self._cmd_reflect()
        elif cmd == "/decide": return self._cmd_decide(args)
        elif cmd == "/know": return self._cmd_know()
        return f"未知命令: {cmd}"

    def _cmd_status(self) -> str:
        m=self.meta.status(); p=self.parliament.status(); u=self.unity.status(); e=self.ewc.status()
        return f"[LAAP Brain v{LAAP_VERSION} 状态]\n元认知: {m['mode']} | 轨迹: {m['traces']} | 偏差纠正: {m['biases_corrected']}\n议会: {p['members']}人, 审议{p['deliberations']}次\n技能: {u['skills']}个 | 知行差距: {u['avg_gap']}\nEWC: {e['params']}参数 | Fisher均值: {e['mean_fisher']}\n轮次: {self._turn_count} | 工具: {self._tool_count}"

    def _cmd_reflect(self) -> str:
        recent = [t for t in self.meta.traces[-10:] if t.outcome is not None]
        avg = sum(t.outcome for t in recent)/max(1,len(recent)) if recent else 0
        g = sum(1 for t in recent if t.outcome and t.outcome>0.6)
        l = sum(1 for t in recent if t.outcome and t.outcome<0.4)
        return f"[反思] 近期{len(recent)}次决策\n  平均结果: {avg:.2f} | 成功: {g} | 低于预期: {l}\n  偏差纠正: {self.meta.bias_corrections}次\n  知行差距: {self.unity.status()['avg_gap']}"

    def _cmd_decide(self, topic: str) -> str:
        if not topic: return "用法: /decide <议题>"
        meta = self.meta.before_decision(topic)
        d = self.parliament.deliberate(topic)
        u = self.unity.decide(meta.get("task_type","general"), topic)
        return f"[决策] 议题: {topic[:40]}\n偏差警告: {', '.join(meta['warnings']) if meta['warnings'] else '无'}\n{self.parliament.summary(d)}\n知行合一: 技能={u.get('skill','无')} | 差距={u.get('gap',0.9):.2f} | 准备度={u.get('readiness','none')}"

    def _cmd_know(self) -> str:
        skills = self.unity.know_thyself()
        lines = ["[自知之明 — 我知道我会什么]", ""]
        for n, s in skills.items(): lines.append(f"  {n:10s}: {s['proficiency']:15s} ({s['use']}次, 成功率{s['success_rate']})")
        novice = [n for n,s in skills.items() if s['proficiency'] in ("novice","unknown")]
        if novice: lines.extend(["", f"需要练习: {', '.join(novice)}"])
        lines.append(f"\n平均知行差距: {self.unity.status()['avg_gap']}")
        return "\n".join(lines)

    def status(self) -> dict:
        return {"version": LAAP_VERSION,
                "meta": self.meta.status(), "parliament": self.parliament.status(),
                "fp": self.fp.status(), "unity": self.unity.status(),
                "ewc": self.ewc.status(),
                "turns": self._turn_count, "tools": self._tool_count,
                "uptime": round(time.time()-self._start_time, 1)}


# ── 导出 ────────────────────────────────────────────────────

__all__ = [
    "LaapBrain", "LAAP_VERSION",
    "enhance", "is_laap_enhanced", "quick_check", "detect_variant",
    # AGI Bridge (v2.0)
    "AGIBridge", "get_agi_bridge",
]

# ── AGI Bridge Access ──────────────────────────────────────

def get_agi_bridge() -> Optional[Any]:
    """
    Get the AGI Bridge instance if available.
    
    Returns AGIBridge for full AGI, or None if not initialized.
    """
    try:
        from laap_brain.agi_bridge import AGIBridge
        return AGIBridge.get_instance()
    except Exception:
        return None

if __name__ == "__main__":
    print(f"LAAP Brain v{LAAP_VERSION}")
    print("=" * 40)
    brain = enhance()
    s = brain.status()
    print(f"✓ 认知增强已激活")
    print(f"  元认知: {s['meta']['mode']}, 轨迹: {s['meta']['traces']}")
    print(f"  议会: {s['parliament']['members']}位议员, 审议: {s['parliament']['deliberations']}次")
    print(f"  技能: {s['unity']['skills']}个, 知行差距: {s['unity']['avg_gap']}")
    print()
    print("在代码中使用:")
    print("  from laap_brain import enhance")
    print("  brain = enhance()")
    print("  brain.before_turn('分析性能瓶颈')")
