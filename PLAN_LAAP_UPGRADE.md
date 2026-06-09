# LAAP 全面升级方案

## LAAP → Production-Grade Autonomous Agent Framework

> **目标**: 在保留 LAAP 独特创新（PSI 认知架构、RSI 进化引擎、情绪系统、14 网关）的同时，补齐 claw-code 级别的工程能力（测试、安全、CI/CD、文档、容器化、MCP 全生命周期）

---

## 📊 当前状态 vs 目标状态

| 维度 | 当前 | 目标 |
|------|------|------|
| 测试覆盖率 | ~200 行, 0% | 10,000+ 行, >70% |
| CI/CD | ❌ | ✅ GitHub Actions + Release |
| 安全沙箱 | 基础危险命令拦截 | 完整 OS 级沙箱 + 权限系统 |
| 文档 | 1 README | 全套文档体系 (10+ 文件) |
| 容器化 | ❌ | Docker + docker-compose |
| MCP | 原型客户端 | 完整生命周期 + 服务端 |
| 插件系统 | 简单注册 | 钩子系统 + 生命周期 |
| 会话持久化 | 纯内存 | 文件 + 数据库持久化 |
| 错误恢复 | ❌ | 会话恢复 + 错误处理链 |
| 配置管理 | .env + cli | YAML 配置文件 + CLI wizard |
| RAG | ❌ | 独立 RAG 服务 |
| Kubernetes | ❌ | K8s 部署配置 |

---

## 📋 实施路线图（6 个阶段，约 40+ 个子任务）

---

## Phase 1: 🏗 基础设施与工程质量 (Foundation)

### 1.1 CI/CD 管道

**新增文件:**
- `.github/workflows/python-ci.yml` — Python 代码构建+测试+lint
- `.github/workflows/python-release.yml` — PyPI 发布
- `.github/workflows/rust-ci.yml` — Rust core 构建+测试
- `.github/ISSUE_TEMPLATE/bug_report.yml` — Bug 报告模板
- `.github/ISSUE_TEMPLATE/feature_request.yml` — 功能请求模板
- `.github/PULL_REQUEST_TEMPLATE.md` — PR 模板
- `.github/FUNDING.yml` — 赞助入口
- `.github/CODEOWNERS` — 代码所有权

**修改文件:**
- `pyproject.toml` — 增加 lint/tool 配置
- `core/Cargo.toml` — lint 配置

**CI 包含:**
- `ruff` / `mypy` 静态检查
- `pytest` + coverage
- `cargo clippy` + `cargo fmt`
- `cargo test`

### 1.2 项目社区标准

**新增文件:**
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `ROADMAP.md`
- `CHANGELOG.md`

### 1.3 容器化部署

**新增文件:**
- `Containerfile` / `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `Containerfile.rust` — Rust core 独立构建
- `k8s/` — Kubernetes 部署文件
  - `k8s/deployment.yaml`
  - `k8s/service.yaml`
  - `k8s/configmap.yaml`

---

## Phase 2: 🛡 安全体系 (Security)

### 2.1 Shell 沙箱系统

**新增文件:**
- `laap/shell/sandbox.py` — OS 级沙箱（Linux `unshare` + Windows `Job` API）
- `laap/shell/validation.py` — 命令白名单/黑名单引擎

**修改文件:**
- `laap/shell/executor.py` — 集成沙箱
- `laap/tools/shell.py` — 增加安全级别参数

### 2.2 权限系统

**新增文件:**
- `laap/permissions/enforcer.py` — 权限强制执行器
- `laap/permissions/policy.py` — 策略解析与匹配
- `laap/permissions/approval_tokens.py` — 令牌批准机制
- `laap/permissions/trust_resolver.py` — 信任解析

**修改文件:**
- `laap/permissions/__init__.py` — 暴露接口
- `laap/api/cli.py` — 权限 UI

### 2.3 路径安全

**新增文件:**
- `laap/editor/path_scope.py` — 路径范围强制
- `laap/editor/allowed_paths.py` — 允许路径管理

**修改文件:**
- `laap/editor/operations/files.py` — 路径检查

### 2.4 OAuth / API Key 管理

**新增文件:**
- `laap/auth/oauth.py` — OAuth 流程
- `laap/auth/keychain.py` — 密钥链管理
- `laap/auth/encryption.py` — 加密存储

---

## Phase 3: 🔧 核心引擎增强 (Core Engine)

### 3.1 MCP 全生命周期

**新增文件:**
- `laap/mcp/server.py` — MCP 服务端
- `laap/mcp/stdio.py` — MCP stdio 传输
- `laap/mcp/lifecycle.py` — 生命周期管理
- `laap/mcp/hardened_manager.py` — 强化 MCP 管理器

**修改文件:**
- `laap/mcp/client.py` — 完善客户端协议
- `laap/mcp/__init__.py` — 暴露接口

### 3.2 插件与钩子系统

**新增文件:**
- `laap/plugins/hooks.py` — 钩子系统（pre/post hooks）
- `laap/plugins/lifecycle.py` — 插件生命周期
- `laap/plugins/sample_hooks/` — 示例钩子
  - `laap/plugins/sample_hooks/pre.sh`
  - `laap/plugins/sample_hooks/post.sh`
- `laap/plugins/plugin.json` — 插件元数据规范

**修改文件:**
- `laap/plugins/manager.py` — 集成钩子

### 3.3 会话持久化与恢复

**新增文件:**
- `laap/store/session_manager.py` — 会话管理器
- `laap/store/session_store.py` — 文件/数据库存储后端
- `laap/store/compaction.py` — 会话压缩
- `laap/store/recovery.py` — 故障恢复

**修改文件:**
- `laap/store/session.py` — 增强持久化
- `laap/cli/repl.py` — 会话恢复 UI

### 3.4 配置系统增强

**新增文件:**
- `laap/cli/config_validate.py` — 配置验证
- `laap/cli/config_schema.py` — JSON Schema 定义
- `laap/cli/setup_wizard.py` — 引导式配置工具

**修改文件:**
- `laap/cli/config_manager.py` — 增强配置管理

### 3.5 错误处理与 Green Contract

**新增文件:**
- `laap/core/green_contract.py` — 绿色契约（函数合同）
- `laap/core/error_chain.py` — 错误链

### 3.6 Rust Core 加强

**修改文件:**
- `core/src/lib.rs` — 增加性能监控、内存安全加固

**新增文件:**
- `core/src/embedding.rs` — 嵌入向量计算（使用 fastembed）
- `core/src/search.rs` — 高性能全文搜索
- `core/benches/` — Rust 基准测试

---

## Phase 4: 🚀 高级系统 (Advanced Systems)

### 4.1 RAG 服务

**新增文件:**
- `laap/rag/` — RAG 模块
  - `laap/rag/__init__.py`
  - `laap/rag/ingest.py` — 文档摄入
  - `laap/rag/chunk.py` — 分块策略
  - `laap/rag/embed.py` — 嵌入生成
  - `laap/rag/search.py` — 语义搜索
  - `laap/rag/db.py` — 向量数据库适配器
  - `laap/rag/qdrant_index.py` — Qdrant 索引

### 4.2 任务与工作流系统

**新增文件:**
- `laap/tasks/` — 任务系统
  - `laap/tasks/__init__.py`
  - `laap/tasks/registry.py` — 任务注册表
  - `laap/tasks/packet.py` — 任务包定义
  - `laap/tasks/worker.py` — 后台工作者
  - `laap/tasks/scheduler.py` — 定时任务（增强 cron）

**修改文件:**
- `laap/cron/scheduler.py` — 集成任务系统

### 4.3 遥测与监控

**新增文件:**
- `laap/telemetry/` — 遥测系统
  - `laap/telemetry/__init__.py`
  - `laap/telemetry/metrics.py` — 指标收集
  - `laap/telemetry/report.py` — 报告生成
  - `laap/telemetry/usage.py` — 使用情况追踪

### 4.4 事件与报告系统

**新增文件:**
- `laap/events/` — 事件系统
  - `laap/events/__init__.py`
  - `laap/events/bus.py` — 事件总线
  - `laap/events/types.py` — 事件类型定义
  - `laap/events/handlers.py` — 事件处理器
- `laap/reports/` — 报告系统
  - `laap/reports/__init__.py`
  - `laap/reports/generator.py`
  - `laap/reports/schema.py`

### 4.5 分支锁定与 Git 增强

**新增文件:**
- `laap/git/branch_lock.py` — 分支锁定
- `laap/git/stale_checks.py` — 过期分支检测

**修改文件:**
- `laap/git/operations.py` — 增强 Git 操作

---

## Phase 5: 🧪 测试体系 (Testing)

### 5.1 单元测试

**新增文件:**
- `tests/test_shell_executor.py`
- `tests/test_sandbox.py`
- `tests/test_permissions.py`
- `tests/test_mcp.py`
- `tests/test_plugins.py`
- `tests/test_config.py`
- `tests/test_memory_rust.py`
- `tests/test_cognition.py`
- `tests/test_goals.py`
- `tests/test_evolution.py`
- `tests/test_orchestration.py`
- `tests/test_rag.py`
- `tests/test_tasks.py`
- `tests/test_gateway.py`
- `tests/test_tools*.py` (每个工具模块)
- `tests/test_api.py`

### 5.2 集成测试

**新增文件:**
- `tests/integration/` — 集成测试
  - `tests/integration/test_full_pipeline.py`
  - `tests/integration/test_multi_agent.py`
  - `tests/integration/test_gateway_to_llm.py`
  - `tests/integration/test_cli_e2e.py`

### 5.3 模拟服务

**新增文件:**
- `tests/mocks/`
  - `tests/mocks/mock_llm.py` — 模拟 LLM
  - `tests/mocks/mock_shell.py` — 模拟 Shell
  - `tests/mocks/mock_mcp_server.py` — 模拟 MCP

### 5.4 Rust 测试

**新增文件:**
- `core/tests/` — Rust 集成测试

### 5.5 性能基准

**新增文件:**
- `benchmarks/` — 基准测试
  - `benchmarks/test_memory_perf.py`
  - `benchmarks/test_llm_streaming.py`

---

## Phase 6: 📚 文档体系 (Documentation)

### 6.1 架构文档

**新增文件:**
- `docs/architecture-overview.md` — 架构总览
- `docs/cognitive-architecture.md` — 认知架构详解（PSI）
- `docs/rsi-evolution.md` — RSI 进化引擎
- `docs/emotion-system.md` — 情绪系统
- `docs/gateway-system.md` — 消息网关
- `docs/mcp-integration.md` — MCP 集成
- `docs/plugin-system.md` — 插件系统
- `docs/security-model.md` — 安全模型

### 6.2 用户文档

**新增文件:**
- `docs/quickstart.md` — 快速开始
- `docs/installation.md` — 安装指南
- `docs/configuration.md` — 配置指南
- `docs/cli-commands.md` — CLI 命令参考
- `docs/api-reference.md` — API 参考
- `docs/gateway-setup.md` — 网关配置
- `docs/troubleshooting.md` — 故障排除
- `docs/faq.md` — 常见问题

### 6.3 开发者文档

**新增文件:**
- `docs/contributing.md` — 贡献指南
- `docs/development-setup.md` — 开发环境
- `docs/testing-guide.md` — 测试指南
- `docs/release-process.md` — 发布流程

### 6.4 验证映射文档

**新增文件:**
- `docs/verification-maps/` — 验证映射
  - `docs/verification-maps/v001-security.md`
  - `docs/verification-maps/v002-cognitive-loop.md`
  - `docs/verification-maps/v003-gateway.md`
  - `docs/verification-maps/v004-mcp.md`
  - `docs/verification-maps/v005-session-persistence.md`

### 6.5 在线资源

- 创建项目网站 / GitHub Pages
- 更新 README 为完整文档中心

---

## ⚡ 保留的 LAAP 独特性（不改动，只加强）

以下模块是 LAAP 的核心创新，**完全保留并加强**：

| 模块 | 位置 | 独特性 |
|------|------|--------|
| PSI 需求驱动 | `laap/cognition/needs.py` | Dörner PSI 理论的 5 大需求 |
| 情绪梯度 | `laap/cognition/emotion.py` | EG-MRSI 微分情绪模型 |
| 目标层级树 | `laap/cognition/goals.py` | PSI 目标形成 |
| 自我感知 | `laap/cognition/awareness.py` | SelfModel + EnvironmentModel |
| RSI 进化引擎 | `laap/evolution/rsi.py` | Darwin-Gödel Machine 循环 |
| 符号递归 | `laap/evolution/symbolic.py` | 元认知符号处理 |
| 变异机制 | `laap/evolution/mutation.py` | 参数空间探索 |
| 14 网关平台 | `laap/gateway/platforms/*` | 微信/钉钉/飞书/QQ/Discord/Telegram等 |
| 品质空间 | `laap/evaluation/fitness.py` | 多维适应度评估 |
| Swarm 编排 | `laap/orchestration/swarm.py` | 路由/协作/协调三种模式 |
| 层次记忆 | `laap/memory/hierarchical.py` | 工作-情景-语义-程序 |
| 生命动作 | `laap/agent/lifelike.py` | 探索/分析/反思/休息 |

---

## 🔄 修改优先级矩阵

| 优先级 | 模块 | 工作量 | 影响 | 依赖 |
|--------|------|--------|------|------|
| P0 | CI/CD | 2 天 | 极高 | 无 |
| P0 | 容器化 | 1 天 | 高 | 无 |
| P0 | 测试基础设施 | 3 天 | 极高 | CI/CD |
| P1 | Shell 沙箱 | 3 天 | 极高 | 无 |
| P1 | 权限系统 | 2 天 | 极高 | 无 |
| P1 | 配置验证 | 1 天 | 高 | 无 |
| P2 | MCP 生命周期 | 3 天 | 高 | 无 |
| P2 | 会话持久化 | 2 天 | 高 | 测试 |
| P2 | 插件钩子 | 2 天 | 中 | 无 |
| P3 | RAG 服务 | 4 天 | 中 | 无 |
| P3 | 任务系统 | 3 天 | 中 | 无 |
| P3 | 遥测 | 2 天 | 中 | 无 |
| P4 | 事件/报告 | 2 天 | 低 | 遥测 |
| P4 | 分支锁定 | 1 天 | 低 | 无 |
| P5 | 文档体系 | 5 天 | 高 | 所有模块 |
| P5 | 社区标准 | 1 天 | 中 | 无 |
| P5 | 完整测试套件 | 10 天 | 极高 | 所有模块 |

---

## 📐 架构决策记录

### ADR-1: Rust 强化 vs 纯 Python
- **决定**: 现有 Rust core 保持 PyO3 架构，增量增加 Rust 模块
- **理由**: 保留 Python 生态灵活性，Rust 只用于性能关键路径
- **Python 版本要求**: >= 3.10 (保持现有)

### ADR-2: 沙箱策略
- **决定**: 双模式沙箱
  - Linux: `unshare` namespace isolation（类似 claw-code）
  - Windows: Job Object + AppContainer
  - fallback: Python `subprocess` + 命令验证
- **理由**: 跨平台兼容，OS 级安全

### ADR-3: 持久化后端
- **决定**: 分层存储
  - 内存: 当前 session（已有）
  - 文件: JSONL session dump（新增）
  - SQLite: 历史查询/分析（新增）
  - 向量: Qdrant（可选，新增）

### ADR-4: 配置格式
- **决定**: YAML 为主 + 环境变量覆写
- **理由**: 人类可读 + 12-factor app 兼容

### ADR-5: 测试策略
- **决定**: pytest + 属性测试（Hypothesis）+ 模拟（pytest-mock）
- **覆盖率目标**: 分支覆盖 > 70%

---

## 🗓 阶段时间线

```
Phase 1 - Foundation (Week 1-2)
  ├── CI/CD 管道
  ├── 社区标准
  ├── 容器化
  └── pyproject.toml 现代化

Phase 2 - Security (Week 2-3)
  ├── Shell 沙箱
  ├── 权限系统
  ├── 路径安全
  └── OAuth/Keychain

Phase 3 - Core Engine (Week 3-5)
  ├── MCP 全生命周期
  ├── 插件与钩子
  ├── 会话持久化
  ├── 配置系统增强
  ├── 错误处理
  └── Rust Core 加强

Phase 4 - Advanced Systems (Week 5-7)
  ├── RAG 服务
  ├── 任务与工作流
  ├── 遥测与监控
  ├── 事件与报告
  └── Git 增强

Phase 5 - Testing (Week 7-9)
  ├── 单元测试 (200 → 10,000+ 行)
  ├── 集成测试
  ├── 模拟服务
  ├── Rust 测试
  └── 性能基准

Phase 6 - Documentation (Week 9-10)
  ├── 架构文档
  ├── 用户文档
  ├── 开发者文档
  ├── 验证映射
  └── README 大修
```

---

## 🎯 成功指标

| 指标 | 当前 | 目标 |
|------|------|------|
| 代码行数 | ~10,233 | ~30,000+ |
| 测试行数 | ~206 | ~15,000+ |
| 测试覆盖率 | ~0% | >80% |
| 测试文件 | 4 | 40+ |
| CI 任务 | 0 | 4+ |
| 文档文件 | 1 | 20+ |
| Docker 配置 | 0 | 3+ |
| MCP 覆盖率 | 30% | 100% |
| Shell 安全 | 基础模式 | 沙箱+验证+权限 |
| GitHub Stars | — | 社区指标 |

---

## 📝 下一步行动

经你确认方案后，我会按优先级从 Phase 1 开始逐步实施。
你希望从哪个阶段开始？或者直接按顺序全部实施？
