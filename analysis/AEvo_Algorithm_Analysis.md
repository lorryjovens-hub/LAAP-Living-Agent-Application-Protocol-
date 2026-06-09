# AEvo 算法深度分析 — 与 LAAP 集成方案

> **论文**: *Harnessing Agentic Evolution* (arXiv:2605.13821)  
> **作者**: Jiayi Zhang, Yongfeng Gu, Jianhao Ruan 等 (DeepWisdom / HKUST(GZ))  
> **核心贡献**: Agent 自进化元编辑框架 (AEvo)

---

## 1. 论文核心思想

### 1.1 问题陈述

现有 Agent 进化方法分为两类，各有缺陷：

| 方法 | 代表 | 局限 |
|------|------|------|
| **Procedure-based** (固定手工设计循环) | 固定 selection rules、feedback summaries、update heuristics | **僵化** — 搜索策略绑定到固定规则，无法自适应 |
| **Agent-based** (通用 LLM Agent 管理搜索) | Meta-Agent 直接提议下一个候选 | **漂移** — 长 horizon 进化中上下文膨胀，agent 偏离原目标 |

共同问题：两类方法都积累了丰富的进化证据（candidates, feedback, traces, failures），但**缺乏一个稳定接口来利用这些证据改进进化过程本身**。

### 1.2 AEvo 解决方案

**核心理念**: 将进化过程本身建模为**可交互环境**，Meta-Agent **编辑驱动进化的机制**，而非直接策展候选。

```
传统: Agent → 生成候选 → 评估 → 反馈 → Agent(改进)
                                                         
AEvo: Meta-Agent → 编辑进化机制 → 进化机制运行 → 产生候选
       ↑                                            |
       └──── 观察进化上下文 (traces, failures, ...) ──┘
```

**关键区别**: 
- 从 "在解空间中搜索"(search in solution space) 转变为 "在策略空间中搜索"(search in strategy space)
- Meta-Agent 不产生候选，而是**编辑产生候选的程序/Agent 上下文**

---

## 2. 算法架构

### 2.1 两阶段循环 (Two-Phase Loop)

```
┌──────────────────────────────────────────────────┐
│                 AEvo 执行循环                      │
│                                                    │
│  Phase 1: Meta-Editing Phase                       │
│  ┌────────────────────────────┐                    │
│  │ Meta-Agent 观察:            │                    │
│  │  • 完整进化上下文           │                    │
│  │  • 候选历史 + 反馈轨迹      │                    │
│  │  • 失败记录 + 保护评估器    │                    │
│  │  Meta-Agent 行动:           │                    │
│  │  • 编辑 Procedure 代码块    │                    │
│  │  • 更新 Agent 上下文(提示词)│                    │
│  │  • 输出 Run Plan            │                    │
│  └──────────┬─────────────────┘                    │
│             ▼                                      │
│  Phase 2: Evolution Segment                        │
│  ┌────────────────────────────┐                    │
│  │ 更新后的机制运行多次迭代    │                    │
│  │ • 受保护评估器防 reward    │                    │
│  │ • 候选历史可搜索           │                    │
│  │ • 标准 CLI 支持启停恢复    │                    │
│  └────────────────────────────┘                    │
└──────────────────────────────────────────────────┘
```

### 2.2 Meta-Agent 可编辑的对象

**Procedure-based 进化**:
- Selection rules (如何选择候选进行评估)
- Feedback formats (反馈总结的格式)
- Mutation/update heuristics (如何根据反馈修改)
- Candidate generation parameters (生成参数)

**Agent-based 进化**:
- Agent context / system prompt (促使更专注的搜索)
- Skills & tools (增减能力)
- Goals & sub-goals (重构目标层级)
- Memory structures (调整记忆权重)

### 2.3 关键设计

| 组件 | 作用 |
|------|------|
| **Harness** (框架) | 标准化 workspace，保护 evaluator，记录候选历史，提供 CLI 启停恢复 |
| **Protected Evaluator** | 隔离真实评估环境，防止 Agent 通过操纵评估函数进行 reward hacking |
| **Searchable History** | 所有候选 + 评估结果持久化，Meta-Agent 可搜索查询 |
| **Run Plan** | Meta-Agent 输出的行动计划，指导 Evolution Segment 的执行 |

---

## 3. 实验结果

| Benchmark | 基线 | AEvo | 改进 |
|-----------|------|------|------|
| Terminal-Bench | 44.3 | **53.8** | +21.4% |
| ARC-AGI-2 | 36.0 | **47.0** | +30.6% |
| Autocorrelation_second | 0.9245 (HyperAgents) | **0.9459** | +2.3% |
| Kernel 优化 (100轮) | — | **1138 cycles** (best) | — |

**整体**: 超越 5 个进化基线，最强基线 **26% 相对提升**

**成本**: 每轮约 baseline 的 3 倍，但计算花费在"优化过程中的审慎决策"而非堆叠更多候选

---

## 4. 与 LAAP 的集成分析

### 4.1 LAAP 现有进化模块 (RSI + Symbolic) 对比

| 维度 | LAAP 现有 (RSI) | AEvo 方案 |
|------|-----------------|-----------|
| **进化驱动** | 固定模板 + LLM 生成简单 proposal | Meta-Agent 编辑整个进化机制 |
| **上下文利用** | 仅使用最近 reward/fitness | 使用完整进化上下文 (trace/failure/history) |
| **修改粒度** | 参数级 (exploration_rate 等) | 机制级 (代码块/上下文/策略) |
| **保护机制** | 无专门保护 | Protected Evaluator 防 reward hacking |
| **历史搜索** | 无 | Searchable Candidate History |
| **多机制支持** | 仅 Agent-based | Procedure-based + Agent-based 双模式 |

### 4.2 集成方案

#### 方案 A: AEvo Engine — 替代现有 RSI 引擎

```
LAAP Agent → AEvoEngine
                ├── MetaEditor (Meta-Agent)
                │     ├── 观察 Agent 状态 (Needs/Emotions/Fitness/History)
                │     ├── 编辑策略 (修改 RSI 模板/参数/上下文)
                │     └── 输出 Run Plan
                ├── ProtectedEvaluator (安全封装现有 FitnessEvaluator)
                └── CandidateHistory (持久化搜索历史)
```

#### 方案 B: AEvo Layer — 作为 RSI 的上层控制器

```
LAAP Agent
    ├── RSI Engine (现有) ← 受 AEvo 控制的进化段
    │     └── 从 AEvo 获取运行计划
    ├── AEvo Controller (新增)
    │     ├── 每隔 N 轮调用 MetaEditor
    │     └── 观察 RSI 的运行效果
    └── Original Components
```

**推荐方案 B** — 渐进式集成，保持现有 RSI 的 N2M-RSI 能力的同时增加元编辑层

### 4.3 需要新增的模块

```
laap/evolution/
├── aevo/                    # AEvo 元编辑框架
│   ├── __init__.py
│   ├── meta_editor.py      # Meta-Agent 编辑器
│   ├── harness.py          # Evolution Harness
│   ├── protected_eval.py   # 受保护评估器
│   ├── candidate_history.py # 候选历史
│   ├── run_plan.py         # 运行计划
│   └── strategies.py       # 编辑策略
├── rsi.py                  # 现有 RSI (作为被控进化段)
└── symbolic.py             # 现有符号递归层
```

### 4.4 集成后的进化流程

```
1. Agent 运行 N 步 (由 RunPlan 指定)
2. 每步产生候选 → ProtectedEvaluator 评估
3. CandidateHistory 记录所有结果
4. 每 N 步触发 MetaEditor:
   a. 收集进化上下文 (fitness 曲线/失败模式/探索历史)
   b. LLM 分析并生成编辑方案
   c. 应用编辑 (修改策略/参数/上下文)
   d. 生成新的 RunPlan
5. RSI Engine 在新策略下继续运行
```

---

## 5. AEvo 核心算法伪代码

```python
class AEvoEngine:
    def __init__(self, meta_agent, base_evolution, evaluator):
        self.meta_agent = meta_agent          # LLM-based Meta-Agent
        self.base_evolution = base_evolution  # 被控进化引擎 (RSI)
        self.evaluator = evaluator            # ProtectedEvaluator
        self.history = CandidateHistory()
        self.edit_interval = 20               # 每 20 步编辑一次
        self.run_plan = None                  # 当前运行计划
    
    def step(self, agent):
        # 1. 执行基础进化步骤
        candidate = self.base_evolution.generate(agent, self.run_plan)
        result = self.evaluator.evaluate(candidate)
        self.history.record(candidate, result)
        
        # 2. 判断是否需要元编辑
        if agent.step_count % self.edit_interval == 0:
            self._meta_edit(agent)
        
        return result
    
    def _meta_edit(self, agent):
        # 收集进化上下文
        context = {
            "history": self.history.summary(),
            "fitness_trend": self.history.fitness_trend(),
            "failure_patterns": self.history.failure_patterns(),
            "agent_state": self._get_agent_state(agent),
        }
        
        # Meta-Agent 分析并生成编辑
        edit_plan = self.meta_agent.analyze(context)
        
        # 应用编辑
        if edit_plan.target == "procedure":
            self._edit_procedure(edit_plan.changes)
        elif edit_plan.target == "context":
            self._edit_agent_context(agent, edit_plan.changes)
        
        # 生成新的运行计划
        self.run_plan = RunPlan(
            iterations=edit_plan.iterations,
            focus=edit_plan.focus_area,
            termination_condition=edit_plan.termination,
        )
```

---

## 6. 预期收益

| 指标 | 当前 LAAP | 集成 AEvo 后 |
|------|-----------|-------------|
| 进化策略数量 | 4 种固定模板 | 动态生成，无限制 |
| 上下文利用 | 最近 fitness | 完整进化轨迹 + 失败模式 |
| Reward Hacking 防护 | 无 | Protected Evaluator |
| 适应性强 | 中等 (模板) | 高 (Meta-Agent 自适应编辑) |
| 长期稳定性 | 中等 | 高 (机制级干预改善) |
| 可扩展性 | 参数级 | 机制级 + 参数级 |

---

## 7. 参考实现

参考实现见 `implementations/aevo/meta_editor.py`，包含 Meta-Agent 编辑循环、ProtectedEvaluator 和 CandidateHistory 的核心逻辑。

---

**论文链接**: https://arxiv.org/abs/2605.13821  
**相关代码**: 
- A-EVO-Lab/a-evolve (通用进化框架，MIT): https://github.com/A-EVO-Lab/a-evolve
- A-EVO-Lab/AdaptiveHarness (自适应 Harness，代码准备中)
- FoundationAgents/AFlow (自动化 Workflow 生成): https://github.com/FoundationAgents/AFlow
