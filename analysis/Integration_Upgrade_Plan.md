# LAAP 功能整合与升级综合方案

> 基于 AEvo (arXiv:2605.13821) 和 QLAM (arXiv:2605.13833) 的整合分析  
> 目标: 增强 LAAP 自进化引擎 + 记忆系统

---

## 1. 总览

### 1.1 当前 LAAP 状态 (v0.3.0)

```
LAAP (Lifeform Autonomous Adaptive Protocol)
├── PSI 认知引擎 (Needs/Emotions/Goals/Awareness)
├── 层次化记忆 (工作/情景/语义/技能 + Rust 加速)
├── 多 LLM 提供商 (OpenAI/Anthropic/DeepSeek/Ollama)
├── 进化引擎 (RSI 递归自我改进 + Symbolic 符号递归)
├── 多 Agent Swarm 编排
├── 工作流引擎
├── CLI / API / MCP 接口
└── Rust PyO3 核心 (MemoryEngine/TokenCounter)
```

### 1.2 两个论文的整合定位

| 论文 | 核心贡献 | 整合模块 | 优先级 | 复杂度 |
|------|---------|---------|--------|--------|
| **AEvo** | 元编辑进化框架 | `laap/evolution/` | ★★★ 高 | ★★★ 中 |
| **QLAM** | 量子长程记忆 | `laap/memory/` | ★★☆ 中 | ★★★★★ 高 |

---

## 2. AEvo 整合方案

### 2.1 整合架构

LAAP Agent 的进化流程将升级为两层结构:

```
第一层 (元控制): AEvo Controller
  ├── 观察: Agent 状态 + 进化上下文 + 历史记录
  ├── 决策: Meta-Agent (LLM) 分析并生成编辑方案
  └── 行动: 编辑 RSI 策略/参数 → 输出 RunPlan

第二层 (执行): RSI Engine (现有)
  └── 在 RunPlan 指导下运行进化循环
       ├── 提案生成 (模板 + LLM)
       ├── 沙盒测试
       └── 采纳/拒绝
```

### 2.2 AEvo 新增模块

```
laap/evolution/aevo/
├── __init__.py           — 导出
├── meta_editor.py        — Meta-Agent 编辑器核心
│     ├── collect_context()    — 收集进化上下文
│     ├── _llm_analyze()       — LLM 分析
│     ├── generate_edit_plan() — 生成编辑方案
│     └── apply_edit()         — 应用编辑
├── harness.py            — Evolution Harness (标准化框架)
│     ├── run_segment()        — 运行进化段
│     └── get_status()         — 状态查询
├── protected_eval.py     — 受保护评估器
│     ├── evaluate()           — 安全评估
│     └── _validate_input()    — 输入验证
├── candidate_history.py  — 候选历史
│     ├── record()             — 记录候选
│     ├── search()             — 搜索历史
│     ├── fitness_trend()      — 适应度趋势
│     └── failure_patterns()   — 失败模式分析
└── run_plan.py           — 运行计划数据类
```

### 2.3 RSI 改造点

```python
# 现有 RSIEngine 的增强改造

class RSIEngine:
    def __init__(self, ...):
        # 不变
        self.aevo_controller = None  # 新增: 可选挂载 AEvo
    
    def step(self, agent, force=False) -> Optional[ImprovementProposal]:
        """增强: 如果 AEvo 存在，使用其 RunPlan"""
        if self.aevo_controller and self._should_trigger_meta_edit():
            self.aevo_controller.meta_edit(agent)
        
        # ... 保持现有逻辑不变 ...
```

### 2.4 Meta-Agent 提示词设计

```
System: 你是一个 AI 进化工程师。分析 Agent 状态并生成编辑方案。
你的输出决定 Agent 进化引擎下一段如何运行。

分析框架:
  1. 适应度趋势: 是上升/平台/下降?
  2. 失败模式: 是否有重复错误?
  3. 探索-利用平衡: 是否需要调整?
  4. 需求满足: 哪些需求未被满足?

输出格式:
  OBSERVATION: <分析发现>
  EDIT_TARGET: <procedure|context>
  CHANGES: <JSON格式的具体修改>
  FOCUS_AREA: <下段聚焦>
  ITERATIONS: <下段运行步数>
  CONFIDENCE: <0.0-1.0>
```

---

## 3. QLAM 整合方案

### 3.1 整合架构

```
LAAP HierarchicalMemory
    ├── 现有层 (不变)
    │   ├── Working Memory (deque, maxlen=9)
    │   ├── Episodic Memory (List[MemoryItem])
    │   ├── Semantic Memory (Dict[str, MemoryItem])
    │   └── Skill Memory (Dict[str, Skill])
    │
    └── QLAM 量子记忆层 (新增)
          ├── QuantumStateEncoder — 输入→量子态编码
          ├── PQCEvolver — 参数量子电路演化
          └── QuantumRetriever — 量子测量检索
```

### 3.2 QLAM 新增模块

```
laap/memory/quantum/
├── __init__.py            — 导出
├── quantum_state.py       — 量子态表示
│     ├── __init__(n_qubits)   — 初始化 |0⟩^⊗ⁿ
│     ├── apply_gate()         — 应用量子门
│     ├── measure()            — 测量 (Born rule)
│     └── density_matrix()     — 密度矩阵
├── pqc_evolver.py         — 参数量子电路
│     ├── __init__(n_qubits, n_layers)
│     ├── evolve(state, input) — PQC 演化
│     └── get_params()         — 获取可训练参数
├── quantum_encoder.py     — 经典→量子编码
│     ├── amplitude_encode()   — 振幅编码
│     ├── angle_encode()       — 角度编码
│     └── encode_content()     — 内容编码
├── quantum_measurement.py — 量子测量
│     ├── pauli_expectation()  — Pauli 期望值
│     ├── sample()             — 采样
│     └── retrieve()           — 检索
└── quantum_memory.py      — QLAM 记忆层主类
      ├── update_state()       — 更新量子态
      ├── retrieve()           — 基于量子态检索
      └── get_state_vector()   — 获取当前状态
```

### 3.3 集成到 HierarchicalMemory

```python
class HierarchicalMemory:
    def __init__(self, ...):
        # ... 现有初始化 ...
        self.quantum = None  # 懒加载 QLAM
    
    def _init_quantum(self, n_qubits=4):
        """初始化 QLAM 量子记忆层"""
        try:
            from laap.memory.quantum import QLAMMemory
            self.quantum = QLAMMemory(n_qubits=n_qubits)
        except Exception:
            pass  # 降级
    
    def remember(self, content, ...):
        # ... 现有逻辑 ...
        # 同步更新量子态
        if self.quantum:
            emb = self._generate_embedding(content)
            if emb is not None:
                self.quantum.update_state(emb)
    
    def quantum_recall(self, query, k=5):
        """基于 QLAM 量子态的检索"""
        if not self.quantum:
            return []
        return self.quantum.retrieve(query, k)
```

---

## 4. 整合路线图

### 阶段 1: AEvo 基础 (P0, ~2天)

- 创建 `laap/evolution/aevo/` 包
- 实现 `CandidateHistory` (数据结构 + 持久化)
- 实现 `ProtectedEvaluator` (封装 FitnessEvaluator)
- 实现 `RunPlan` 数据类
- 集成到 RSIEngine
- 单元测试

### 阶段 2: Meta-Agent (P0, ~2天)

- 实现上下文收集 (`_collect_context`)
- 设计 Meta-Agent 提示词
- 实现编辑方案解析和应用
- 实现 RunPlan 生成
- 集成测试

### 阶段 3: QLAM 记忆 (P1, ~3天)

- 创建 `laap/memory/quantum/` 包
- 实现 `QuantumState` (量子态操作)
- 实现 `PQCEvolver` (可训练电路)
- 实现编码 + 测量
- 集成到 HierarchicalMemory
- 依赖管理 + 优雅降级

### 阶段 4: 深度集成 (P1, ~2天)

- AEvo 利用 QLAM 增强的上下文
- QLAM 量子态作为 AEvo 评估信号
- 统一 CLI 命令
- 端到端测试 + 性能基准

---

## 5. 代码量估算

| 模块 | 文件数 | 预估代码行 |
|------|--------|-----------|
| AEvo Core | 5-6 | ~800 行 |
| QLAM Core | 5-6 | ~600 行 |
| 集成改造 | 3-4 | ~400 行 |
| 测试 | 5-8 | ~500 行 |
| **总计** | **~20** | **~2300 行** |

---

## 6. 依赖管理

```txt
# AEvo: 无新增依赖 (使用现有 LLM 提供商)
# QLAM: 可选依赖
pennylane>=0.35.0    # 量子机器学习 (可选)
scipy>=1.10.0        # 科学计算 (可选)
```

---

## 7. 成功指标

```
阶段 1:  ✓ RSIEngine 可被 AEvo 控制
          ✓ CandidateHistory 记录所有候选
          ✓ ProtectedEvaluator 工作正常

阶段 2:  ✓ Meta-Agent 生成有意义的编辑
          ✓ 编辑后策略明显变化
          ✓ LLM 成本可控

阶段 3:  ✓ QuantumState 正确模拟量子操作
          ✓ QLAM 可编码和检索
          ✓ 无 PennyLane 时优雅降级

阶段 4:  ✓ AEvo + QLAM 共存稳定
          ✓ 适应度优于纯 RSI
          ✓ 所有测试通过
```

---

## 8. 与现有 T1-T15 计划的关系

| 现有 Task | 与 AEvo/QLAM 的关系 |
|-----------|-------------------|
| T1: Anthropic 工具调用修复 | **前置** — Meta-Agent 需要 Anthropic 正常 |
| T10: LLM 生成 RSI 提案 | AEvo MetaEditor 可复用 LLM 提示词设计 |
| T11: 向量嵌入集成 | QLAM 前置 — 嵌入作为量子编码输入 |
| T12: 测试框架 | 为 AEvo + QLAM 新增测试 |
| T15: 文档 | 更新 README |
