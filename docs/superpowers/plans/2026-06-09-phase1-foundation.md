# Phase 1: 基础可用性 — LAAP 生存与稳定实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) for syntax tracking.

**Goal:** 修复 LAAP 的致命 Bug，建立持久化存储基础，实现基本技能系统，让 LAAP 能稳定运行不崩溃、重启后状态不丢失。

**Architecture:** 以 LAAP 原有的 PSI 认知架构为核心，先修复直接影响运行的 Bug，再引入 Hermes 的 SQLite 持久化模式和技能系统模式。采用渐进式重构——先稳定现有代码，再注入新能力。

**Tech Stack:** Python 3.10+, SQLite (WAL + FTS5), numpy, pytest, Anthropic SDK, OpenAI SDK

**工作目录:** `D:\LAAP`

---

## 文件结构与职责

### 新建文件
| 文件 | 职责 |
|------|------|
| `laap/store/session_manager.py` | Session 管理器（会话保存/加载/列表，集成 Agent 生命周期） |
| `laap/skills/curator.py` | 技能审查与维护后台（从 Hermes curator 借鉴） |
| `laap/tools/hermes_adapter.py` | Hermes 风格工具适配层（工具自动发现 + schema 生成） |
| `tests/test_integration.py` | 集成测试：Agent + 持久化 + 技能完整流程 |
| `tests/test_session_persistence.py` | 会话持久化测试 |
| `tests/test_skills.py` | 技能系统测试 |
| `tests/fixtures.py` | 共享测试夹具 |

### 修改文件
| 文件 | 变更内容 |
|------|----------|
| `laap/agent/base.py:236-240` | 修复工具重复注册（移除冗余调用） |
| `laap/agent/base.py:44-52` | 添加 session 集成 + 自动保存钩子 |
| `laap/agent/codex.py` | 修复 _register_code_tools 重复注册 |
| `laap/tools/code_edit.py` | 清理全局注册守卫 |
| `laap/tools/shell.py` | 清理全局注册守卫 |
| `laap/llm/provider.py:575-635` | 验证 Anthropic tool_use 处理，增加输入验证 |
| `laap/evaluation/stability.py` | 修复编码问题 |
| `laap/store/session.py` | 增加 AoDB 的 Agent 状态序列化支持 |
| `laap/cli/repl.py` | 增加会话命令（/save, /load, /sessions） |
| `laap/ui/stream_handler.py` | 增强流式输出（实时 token 计数、工具调用进度） |
| `pyproject.toml` | 添加 pytest 配置、覆盖配置 |
