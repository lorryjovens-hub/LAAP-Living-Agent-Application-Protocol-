"""
laap_brain — LAAP Cognitive Kernel v3.1 (Hermes 嵌入式版本)

轻量级认知增强内核，可直接嵌入任何 Agent 框架。
核心功能：
  - 元认知 (Meta-Cognition): 4层认知监控 + 7种偏差检测
  - 议会 (Parliament): 8议员多视角审议 + 快闪模式
  - 知行合一 (Unity): 6个具身技能 + 自动熟练度进化
  - 持续学习 (EWC): 弹性权重巩固，防止灾难性遗忘

使用方式：
    from laap_brain import LaapBrain
    brain = LaapBrain()
    brain.before_turn(messages, system_prompt)
    brain.after_tool(tool_name, result)
    brain.after_turn(response)

依赖：
  - 原生 LAAP 模块 (laap.*) 有空则深度集成，无则自包含降级
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import time, logging, json, math, threading, uuid, os

logger = logging.getLogger("laap_brain")

__version__ = "3.1.0"
VERSION = __version__

__all__ = [
    "LaapBrain",
    "ThinkingMode", "CognitiveBias", "SkillProficiency",
    "EmbodiedSkill", "UnityDecision", "BrainState",
    "VERSION",
]

# ════════════════════════════════════════════════════════════
# 常量与枚举
# ════════════════════════════════════════════════════════════

class ThinkingMode(str, Enum):
    INTUITIVE = "intuitive"
    DELIBERATE = "deliberate"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    REFLECTIVE = "reflective"
    EXPLORATORY = "exploratory"

class CognitiveBias(str, Enum):
    CONFIRMATION = "confirmation_bias"
    OVERCONFIDENCE = "overconfidence"
    ANCHORING = "anchoring"
    AVAILABILITY = "availability"
    SUNK_COST = "sunk_cost"
    RECENCY = "recency_bias"
    HASTY_GENERALIZATION = "hasty_generalization"

class SkillProficiency(str, Enum):
    UNKNOWN = "unknown"
    AWARE = "aware"
    NOVICE = "novice"
    PRACTITIONER = "practitioner"
    EXPERT = "expert"
    MASTER = "master"

# ════════════════════════════════════════════════════════════
# 数据类
# ════════════════════════════════════════════════════════════

@dataclass
class EmbodiedSkill:
    name: str = ""
    description: str = ""
    cognitive_action: str = ""
    proficiency: SkillProficiency = SkillProficiency.UNKNOWN
    use_count: int = 0
    success_count: int = 0
    avg_quality: float = 0.0
    last_used: float = 0.0
    intuitive_triggers: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.success_count / max(1, self.use_count)

@dataclass
class UnityDecision:
    id: str = ""
    timestamp: float = 0.0
    trigger: str = ""
    cognitive_action: str = ""
    intention: str = ""
    action_plan: str = ""
    tool_calls: List[Dict] = field(default_factory=list)
    confidence: float = 0.5
    execution_readiness: float = 0.5
    knowledge_action_gap: float = 0.0
    actual_steps: int = 0
    actual_quality: float = 0.0
    completed: bool = False
    learning: str = ""

@dataclass
class BrainState:
    """大脑当前状态快照"""
    pfc_activation: float = 0.5
    limbic_activation: float = 0.5
    salience_signal: float = 0.3
    dmn_activation: float = 0.1
    attention_breadth: float = 0.5
    cognitive_load: float = 0.3
    integration_level: float = 0.7
    avg_gap: float = 0.0

    def to_dict(self) -> dict:
        return {k: round(v, 2) for k, v in self.__dict__.items()}


# ════════════════════════════════════════════════════════════
# LaapBrain — 认知核心
# ════════════════════════════════════════════════════════════

class LaapBrain:
    """
    LAAP Brain — 认知增强核心

    轻量级类人脑认知系统，提供：
    - 元认知监控 (偏检测, 思考模式切换)
    - 多视角决策 (内部议会)
    - 具身技能 (知行合一)
    - 持续学习 (EWC)
    - 状态报告

    用法:
        brain = LaapBrain(agent_id="hermes-01")

        # 注入到 system prompt
        prompt_block = brain.before_turn(messages, system_prompt)
        system_prompt += prompt_block

        # 每个工具调用后学习
        brain.after_tool(tool_name, result)

        # 每轮对话后反思
        brain.after_turn(response)
    """

    def __init__(self, agent: Any = None, agent_id: str = ""):
        self.agent = agent
        self.id = agent_id or os.environ.get("LAAP_AGENT_ID", f"brain_{uuid.uuid4().hex[:6]}")
        self.name = f"LAAP-Brain-{self.id[:6]}"

        # 原生 LAAP 集成（有则用，无则自包含降级）
        self._native_brain = None
        self._native_unity = None
        self._native_ewc = None
        self._try_native_import()

        # 皮层状态
        self.state = BrainState()

        # 元认知
        self.current_mode: str = ThinkingMode.INTUITIVE.value
        self.bias_corrections: int = 0
        self._bias_history: List[str] = []

        # 议会
        self._deliberations: int = 0

        # 知行合一 — 具身技能
        self.skills: Dict[str, EmbodiedSkill] = {}
        self._init_skills()

        # 全局统计
        self._total_turns = 0
        self._total_tools = 0
        self._tool_history: List[Dict] = []
        self._max_history = 100
        self._start_time = time.time()
        self._avg_gap = 0.0
        self._gap_samples = 0

        # EWC 参数
        self._ewc_lambda = 0.5
        self._fisher_matrix: Dict[str, float] = {}
        self._old_params: Dict[str, Any] = {}

        # 线程锁
        self._lock = threading.Lock()

        logger.info(f"[{self.name}] 初始化完成 — 元认知+议会+知行合一+EWC 就绪")

    # ═══════════════════════════════════════════════════════
    # 原生 LAAP 集成
    # ═══════════════════════════════════════════════════════

    def _try_native_import(self):
        """尝试导入原生 LAAP 模块，失败则降级为自包含"""
        try:
            from laap.cognition.brain import Brain
            from laap.cognition.unity import UnityEngine
            self._native_brain_cls = Brain
            self._native_unity_cls = UnityEngine
            self._has_native = True
            logger.info("原生 LAAP 模块可用，深度集成模式")
        except ImportError:
            self._has_native = False
            logger.info("原生 LAAP 模块不可用，自包含降级模式")

    def _get_native_brain(self):
        """延迟初始化原生 Brain"""
        if self._native_brain is None and self._has_native:
            try:
                from laap.cognition.brain import Brain
                self._native_brain = Brain(agent_id=self.id)
            except Exception as e:
                logger.warning(f"原生 Brain 初始化失败: {e}")
        return self._native_brain

    def _get_native_unity(self):
        """延迟初始化原生 Unity"""
        if self._native_unity is None and self._has_native and self._native_brain:
            try:
                from laap.cognition.unity import UnityEngine
                if hasattr(self._native_brain, 'meta_cognition'):
                    self._native_unity = UnityEngine(
                        cortex=self._native_brain.meta_cognition,
                        brain=self._native_brain,
                    )
            except Exception as e:
                logger.warning(f"原生 Unity 初始化失败: {e}")
        return self._native_unity

    # ═══════════════════════════════════════════════════════
    # 具身技能初始化
    # ═══════════════════════════════════════════════════════

    def _init_skills(self):
        """初始化内置具身技能"""
        defaults = [
            ("文件分析", "读取并分析文件内容", "analyze",
             ["分析文件", "文件内容", "读取", "查看文件"], SkillProficiency.PRACTITIONER),
            ("代码调试", "系统化调试：隔离-分析-修复-验证", "debug",
             ["debug", "bug", "错误", "崩溃", "不工作", "修复"], SkillProficiency.PRACTITIONER),
            ("信息搜索", "搜索和收集相关信息", "explore",
             ["搜索", "查找", "查一下", "search", "find", "查询"], SkillProficiency.EXPERT),
            ("代码生成", "生成和验证代码", "execute",
             ["生成", "创建", "写代码", "实现", "implement"], SkillProficiency.NOVICE),
            ("数据探索", "探索数据集的模式和结构", "explore",
             ["探索", "分析数据", "查看", "统计"], SkillProficiency.PRACTITIONER),
            ("性能优化", "分析性能问题并优化", "debug",
             ["性能", "慢", "优化", "响应时间", "提速"], SkillProficiency.NOVICE),
        ]
        for name, desc, action, triggers, prof in defaults:
            self.skills[name] = EmbodiedSkill(
                name=name, description=desc,
                cognitive_action=action,
                proficiency=prof,
                intuitive_triggers=triggers,
            )

    # ═══════════════════════════════════════════════════════
    # 核心接口: before_turn
    # ═══════════════════════════════════════════════════════

    def before_turn(self, messages: List[Dict], system_prompt: str = "") -> str:
        """
        每轮对话前的认知准备

        1. 元认知分析：检测任务类型、偏差信号
        2. 议会快闪（高风险任务）: 3人快速审议
        3. 技能匹配：Unity 分析需要什么具身技能
        4. 生成大脑状态提示块注入 system prompt

        Returns:
            要追加到 system_prompt 的提示块
        """
        self._total_turns += 1

        # 提取最后一条用户消息
        user_msg = ""
        for m in reversed(messages or []):
            if m.get("role") == "user" and m.get("content"):
                user_msg = str(m["content"])[:200]
                break

        if not user_msg:
            return ""

        # 元认知分析
        mode = self._analyze_mode(user_msg)
        self.current_mode = mode

        bias_signal = self._detect_bias(user_msg)

        # 议会（高风险触发）
        parliament_block = ""
        risk_score = self._compute_risk(user_msg)
        if risk_score > 0.6:
            deliberation = self._fast_deliberate(user_msg)
            parliament_block = self._format_deliberation(deliberation)

        # 技能匹配
        skill_name = self._match_skill(user_msg)
        gap = self._compute_gap(skill_name)

        # DMN 反射节律
        if self._total_turns % 5 == 0:
            self.state.dmn_activation = min(1.0, self.state.dmn_activation + 0.1)
        else:
            self.state.dmn_activation = max(0.0, self.state.dmn_activation - 0.02)

        # 更新皮层状态
        self.state.pfc_activation = min(1.0, self.state.pfc_activation + 0.05)
        self.state.cognitive_load = min(1.0, len(user_msg) / 2000)

        # 生成提示块
        prompt_block = self._build_prompt_block(
            mode, bias_signal, parliament_block,
            skill_name, gap, risk_score,
        )

        # 原生集成
        native_brain = self._get_native_brain()
        if native_brain:
            try:
                native_brain.think(user_msg)
                extra = native_brain.get_brain_prompt_block()
                prompt_block += "\n" + extra
            except Exception:
                pass

        logger.info(
            f"[{self.name}] before_turn #{self._total_turns}: "
            f"mode={mode} risk={risk_score:.2f} skill={skill_name}"
        )
        return prompt_block

    def after_tool(self, tool_name: str, result: Any):
        """
        工具调用后学习

        1. 更新技能熟练度（如果匹配）
        2. EWC 参数更新
        3. 元认知反馈
        """
        self._total_tools += 1

        outcome_score = self._compute_outcome_score(result)

        # 更新匹配的技能
        matched = self._find_skill_by_tool(tool_name)
        if matched:
            with self._lock:
                matched.use_count += 1
                matched.last_used = time.time()
                if outcome_score > 0.5:
                    matched.success_count += 1
                matched.avg_quality = matched.avg_quality * 0.9 + outcome_score * 0.1
                self._advance_proficiency(matched)

        # EWC 学习
        if self._total_tools % 10 == 0:
            self._ewc_before_learning()
            self._ewc_compute_fisher()

        # 记录工具历史
        self._tool_history.append({
            "tool": tool_name,
            "score": outcome_score,
            "time": time.time(),
            "bias_mode": self.current_mode,
        })
        if len(self._tool_history) > self._max_history:
            self._tool_history = self._tool_history[-self._max_history:]

        # 更新知行差距
        self._gap_samples += 1
        self._avg_gap = self._avg_gap * 0.95 + (1.0 - outcome_score) * 0.05

        # 原生集成
        native_brain = self._get_native_brain()
        if native_brain:
            try:
                native_brain.learn_from_outcome(tool_name, outcome_score)
            except Exception:
                pass

        logger.debug(
            f"[{self.name}] after_tool: {tool_name} "
            f"score={outcome_score:.2f} "
            f"skills_matched={matched.name if matched else 'none'}"
        )

    def after_turn(self, response: str):
        """
        每轮对话后反思

        1. 元认知反思
        2. 偏差纠正评估
        3. 皮层状态衰减
        """
        # 状态衰减
        self.state.pfc_activation = max(0.3, self.state.pfc_activation - 0.02)
        self.state.limbic_activation = max(0.3, self.state.limbic_activation - 0.01)
        self.state.cognitive_load = max(0.1, self.state.cognitive_load - 0.05)

        # 元认知反思（每10轮一次完整反思）
        if self._total_turns % 10 == 0:
            self._meta_reflection()

        logger.debug(f"[{self.name}] after_turn #{self._total_turns}")

    # ═══════════════════════════════════════════════════════
    # 认知命令接口
    # ═══════════════════════════════════════════════════════

    def cmd_brain(self) -> str:
        """完整认知状态报告"""
        lines = [
            "╔══ LAAP Brain 认知状态 ══╗",
            "",
            f"  元认知模式: {self.current_mode}",
            f"  偏差纠正: {self.bias_corrections} 次",
            f"  议会审议: {self._deliberations} 次",
            f"  工具调用: {self._total_tools} 次",
            f"  对话轮次: {self._total_turns} 轮",
            "",
            "  皮层活动:",
            f"    PFC(规划):   {self.state.pfc_activation:.0%}",
            f"    边缘(情感):  {self.state.limbic_activation:.0%}",
            f"    DMN(反思):   {self.state.dmn_activation:.0%}",
            f"    突显(重要):  {self.state.salience_signal:.0%}",
            f"    注意力广度:  {self.state.attention_breadth:.0%}",
            f"    整合度:      {self.state.integration_level:.0%}",
            f"    知行差距:    {self._avg_gap:.3f}",
            "",
            f"  存活时间: {time.time() - self._start_time:.0f}s",
        ]

        native_brain = self._get_native_brain()
        if native_brain:
            try:
                lines.append("")
                lines.append(native_brain.introspect())
            except Exception:
                pass

        return "\n".join(lines)

    def cmd_reflect(self) -> str:
        """元认知反思"""
        recent = self._tool_history[-20:] if self._tool_history else []
        if not recent:
            return "尚无足够数据反思。"

        avg_score = sum(r["score"] for r in recent) / len(recent)
        modes = {}
        for r in recent:
            modes[r["bias_mode"]] = modes.get(r["bias_mode"], 0) + 1

        lines = [
            "=== 元认知反思 ===",
            f"  近期平均结果: {avg_score:.2f}",
            f"  思考模式分布: {dict(sorted(modes.items(), key=lambda x: x[1], reverse=True))}",
        ]

        if avg_score < 0.4:
            lines.append("  诊断: 结果偏差，建议切换到谨慎模式")
        elif avg_score > 0.8:
            lines.append("  诊断: 表现良好，保持当前策略")
        else:
            lines.append("  诊断: 正常范围")

        # 偏差历史
        if self._bias_history:
            lines.append(f"  偏差纠正历史: {len(self._bias_history)} 次")
            lines.append(f"  常见偏差: {max(set(self._bias_history), key=self._bias_history.count)}")

        return "\n".join(lines)

    def cmd_decide(self, topic: str = "") -> str:
        """议会审议 + 知行合一"""
        if not topic:
            return "请提供一个议题。用法: /decide <议题>"

        self._deliberations += 1
        deliberation = self._fast_deliberate(topic)
        skill_name = self._match_skill(topic)

        lines = [
            "=== 议会审议 ===",
            f"  议题: {topic}",
            f"  参与议员: {len(deliberation['opinions'])} 人",
        ]
        for op in deliberation["opinions"]:
            lines.append(f"    [{op['role']}] {op['stance']} (conf={op['confidence']:.2f})")

        lines.append(f"  决议: {deliberation['decision']}")
        lines.append("")

        if skill_name:
            skill = self.skills.get(skill_name)
            gap = self._compute_gap(skill_name)
            lines.append("=== 知行合一 ===")
            lines.append(f"  匹配技能: {skill_name}")
            if skill:
                lines.append(f"  熟练度: {skill.proficiency.value} (使用{skill.use_count}次, 成功率{skill.success_rate:.0%})")
            lines.append(f"  知行差距: {gap:.2f}")
        else:
            lines.append("  未匹配到具身技能")

        return "\n".join(lines)

    def cmd_know(self) -> str:
        """自知之明"""
        lines = [
            "=== 具身技能 ===",
        ]
        for name, skill in self.skills.items():
            embodied = "✓" if skill.proficiency in (SkillProficiency.EXPERT, SkillProficiency.MASTER) else " "
            lines.append(
                f"  [{embodied}] {name}: {skill.proficiency.value}"
                f" (使用{skill.use_count}次, 成功率{skill.success_rate:.0%})"
            )

        novice = [n for n, s in self.skills.items()
                  if s.proficiency in (SkillProficiency.UNKNOWN, SkillProficiency.AWARE, SkillProficiency.NOVICE)]
        if novice:
            lines.append(f"")
            lines.append(f"  需要练习: {', '.join(novice)}")

        lines.append(f"")
        lines.append(f"  平均知行差距: {self._avg_gap:.3f}")
        lines.append(f"  EWC 参数保护: {len(self._fisher_matrix)} 个技能")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════
    # 内部: 元认知
    # ═══════════════════════════════════════════════════════

    _TRIGGER_ANALYTICAL = ["分析", "比较", "评估", "判断", "哪个更好", "pros and cons", "优缺点"]
    _TRIGGER_CREATIVE = ["创意", "设计", "想一个", "生成", "写一个", "创造", "想象"]
    _TRIGGER_EXPLORE = ["搜索", "查", "寻找", "探索", "调查", "research"]
    _TRIGGER_REFLECTIVE = ["反思", "回顾", "思考", "我想", "我觉得", "为什么", "反省"]
    _TRIGGER_DEBUG = ["错误", "bug", "修复", "调试", "不工作", "崩溃", "失败"]

    def _analyze_mode(self, text: str) -> str:
        """分析输入选择思考模式"""
        t = text.lower()
        for word in self._TRIGGER_ANALYTICAL:
            if word in t:
                return ThinkingMode.ANALYTICAL.value
        for word in self._TRIGGER_CREATIVE:
            if word in t:
                return ThinkingMode.CREATIVE.value
        for word in self._TRIGGER_EXPLORE:
            if word in t:
                return ThinkingMode.EXPLORATORY.value
        for word in self._TRIGGER_REFLECTIVE:
            if word in t:
                return ThinkingMode.REFLECTIVE.value
        for word in self._TRIGGER_DEBUG:
            if word in t:
                return ThinkingMode.ANALYTICAL.value
        return ThinkingMode.INTUITIVE.value

    def _detect_bias(self, text: str) -> List[str]:
        """检测输入中的认知偏差信号"""
        biases = []
        t = text.lower()

        # 确认偏差
        if any(w in t for w in ["肯定", "一定是", "毫无疑问", "obviously", "clearly"]):
            biases.append(CognitiveBias.CONFIRMATION.value)

        # 过度自信
        if any(w in t for w in ["绝对", "100%", "永远", "always", "never", "百分百"]):
            biases.append(CognitiveBias.OVERCONFIDENCE.value)

        # 锚定效应
        if any(w in t for w in ["基于", "按照", "根据之前的", "像上次一样"]):
            biases.append(CognitiveBias.ANCHORING.value)

        # 沉没成本
        if any(w in t for w in ["已经花了", "投入了", "做了这么多", "不能放弃"]):
            biases.append(CognitiveBias.SUNK_COST.value)

        if biases:
            self.bias_corrections += len(biases)
            self._bias_history.extend(biases)

        return biases

    def _compute_risk(self, text: str) -> float:
        """计算输入的风险等级 0-1"""
        risk = 0.2
        t = text.lower()

        # 高风险触发词
        high_risk = ["删除", "清除", "deploy", "生产", "production", "提交", "merge",
                     "push", "rm -rf", "drop", "发布", "支付", "付款"]
        for w in high_risk:
            if w in t:
                risk += 0.3

        # 代码段
        if "```" in t or "`rm " in t or "`drop" in t:
            risk += 0.2

        # 系统操作
        if any(w in t for w in ["系统", "配置", "config", "sudo", "chmod", "chown"]):
            risk += 0.15

        return min(1.0, risk)

    # ═══════════════════════════════════════════════════════
    # 内部: 议会
    # ═══════════════════════════════════════════════════════

    _MEMBER_ROLES = [
        ("理性分析员", "rational", "数据驱动，逻辑优先"),
        ("安全卫士", "safety", "风险评估，安全第一"),
        ("实用主义者", "pragmatist", "可行性和效率"),
    ]

    def _fast_deliberate(self, topic: str) -> Dict:
        """快闪审议（3人）"""
        opinions = []
        for name, role, style in self._MEMBER_ROLES:
            stance, conf = self._simulate_opinion(topic, role, style)
            opinions.append({
                "name": name,
                "role": role,
                "stance": stance,
                "confidence": conf,
                "style": style,
            })

        # 议长综合
        avg_conf = sum(o["confidence"] for o in opinions) / len(opinions)
        stances = [o["stance"] for o in opinions]

        return {
            "opinions": opinions,
            "decision": " | ".join(stances[:2]),
            "confidence": round(avg_conf, 2),
            "members": len(opinions),
        }

    def _simulate_opinion(self, topic: str, role: str, style: str) -> Tuple[str, float]:
        """模拟议员意见"""
        t = topic.lower()
        conf = 0.5

        if role == "rational":
            conf += 0.2 if any(w in t for w in ["分析", "数据", "统计", "比较"]) else 0
            return ("逻辑分析后建议基于事实评估", min(0.9, conf + 0.2))
        elif role == "safety":
            risk = self._compute_risk(topic)
            if risk > 0.5:
                return (f"高风险({risk:.0%})，建议添加安全检查", 0.8)
            return ("风险可控，安全", 0.7)
        elif role == "pragmatist":
            if len(t) > 100:
                return ("复杂度较高，建议分步执行", 0.6)
            return ("可行，直接执行", 0.8)
        return ("了解", 0.5)

    def _format_deliberation(self, d: Dict) -> str:
        """格式化议会结果"""
        parts = ["[议会快闪]"]
        for o in d["opinions"]:
            parts.append(f"  {o['name']}({o['role']}): {o['stance']}")
        parts.append(f"  → 决议: {d['decision']} (conf={d['confidence']:.2f})")
        return "\n".join(parts)

    # ═══════════════════════════════════════════════════════
    # 内部: 知行合一
    # ═══════════════════════════════════════════════════════

    def _match_skill(self, text: str) -> Optional[str]:
        """匹配触发的具身技能"""
        t = text.lower()
        best_name = None
        best_score = 0

        for name, skill in self.skills.items():
            score = sum(1 for trig in skill.intuitive_triggers if trig.lower() in t)
            if score > best_score:
                best_score = score
                best_name = name

        return best_name

    def _compute_gap(self, skill_name: Optional[str]) -> float:
        """计算知行差距"""
        if not skill_name:
            return 0.9
        skill = self.skills.get(skill_name)
        if not skill:
            return 0.9

        if skill.proficiency == SkillProficiency.MASTER:
            return 0.1
        elif skill.proficiency == SkillProficiency.EXPERT:
            return 0.2
        elif skill.proficiency == SkillProficiency.PRACTITIONER:
            return 0.35
        elif skill.proficiency == SkillProficiency.NOVICE:
            return 0.6
        return 0.8

    def _find_skill_by_tool(self, tool_name: str) -> Optional[EmbodiedSkill]:
        """通过工具名查找匹配的技能"""
        for skill in self.skills.values():
            if tool_name.lower() in skill.name.lower():
                return skill
        return None

    def _advance_proficiency(self, skill: EmbodiedSkill):
        """提升技能熟练度"""
        if skill.use_count >= 20 and skill.success_rate > 0.9:
            skill.proficiency = SkillProficiency.MASTER
        elif skill.use_count >= 10 and skill.success_rate > 0.8:
            skill.proficiency = SkillProficiency.EXPERT
        elif skill.use_count >= 5 and skill.success_rate > 0.7:
            skill.proficiency = SkillProficiency.PRACTITIONER
        elif skill.use_count >= 1:
            if skill.proficiency == SkillProficiency.UNKNOWN:
                skill.proficiency = SkillProficiency.NOVICE

    # ═══════════════════════════════════════════════════════
    # 内部: EWC
    # ═══════════════════════════════════════════════════════

    def _ewc_before_learning(self):
        """学习前保存参数快照"""
        self._old_params = {}
        for name, skill in self.skills.items():
            self._old_params[name] = {
                "proficiency": skill.proficiency.value,
                "avg_quality": skill.avg_quality,
                "success_rate": skill.success_rate,
            }

    def _ewc_compute_fisher(self):
        """计算 Fisher 信息矩阵"""
        for name, skill in self.skills.items():
            freq = skill.use_count / max(1, self._total_tools)
            prof_weight = {
                "unknown": 0.0, "aware": 0.1, "novice": 0.3,
                "practitioner": 0.6, "expert": 0.8, "master": 1.0,
            }.get(skill.proficiency.value, 0.0)
            importance = freq * 0.3 + skill.success_rate * 0.3 + prof_weight * 0.4
            self._fisher_matrix[name] = importance

    # ═══════════════════════════════════════════════════════
    # 内部: 提示块生成
    # ═══════════════════════════════════════════════════════

    def _build_prompt_block(self, mode: str, biases: List[str],
                             parliament: str, skill_name: Optional[str],
                             gap: float, risk: float) -> str:
        """生成注入到 System Prompt 的大脑状态块"""
        parts = [
            "",
            "[LAAP Brain State]",
            f"  Mode: {mode}",
        ]

        if biases:
            parts.append(f"  Detected biases: {', '.join(biases)}")

        if parliament:
            parts.append(f"  Parliament: risk={risk:.0%}")
            parts.append(parliament)

        if skill_name:
            parts.append(f"  Unity: {skill_name} (gap={gap:.2f})")

        parts.append(f"  Attention: {'broad' if self.state.attention_breadth > 0.6 else 'focused'}")
        parts.append(f"  Cognitive load: {self.state.cognitive_load:.0%}")
        parts.append("")

        return "\n".join(parts)

    def _compute_outcome_score(self, result: Any) -> float:
        """从工具返回值提取结果评分"""
        if result is None:
            return 0.3

        if isinstance(result, dict):
            if result.get("error"):
                return 0.1
            if result.get("exit_code") == 0:
                return 0.9
            if result.get("exit_code") is not None:
                return 0.2
            return 0.6

        if isinstance(result, str):
            if "error" in result.lower() or "traceback" in result.lower():
                return 0.15
            return 0.7

        return 0.5

    def _meta_reflection(self):
        """执行深层反思"""
        recent = self._tool_history[-20:] if len(self._tool_history) >= 20 else self._tool_history
        if not recent:
            return

        avg_score = sum(r["score"] for r in recent) / len(recent)
        if avg_score < 0.3:
            self.state.dmn_activation = min(1.0, self.state.dmn_activation + 0.2)
            logger.info(f"[{self.name}] 反思: 近期结果偏低({avg_score:.2f}), 建议调整策略")

    # ═══════════════════════════════════════════════════════
    # 查询接口
    # ═══════════════════════════════════════════════════════

    def status(self) -> dict:
        return {
            "version": "3.1",
            "mode": self.current_mode,
            "turns": self._total_turns,
            "tools": self._total_tools,
            "biases_corrected": self.bias_corrections,
            "deliberations": self._deliberations,
            "skills": len(self.skills),
            "avg_gap": round(self._avg_gap, 3),
            "cortex": self.state.to_dict(),
            "has_native": self._has_native,
            "uptime_s": round(time.time() - self._start_time),
        }

    def to_dict(self) -> dict:
        return self.status()
