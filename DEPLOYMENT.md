# LAAP — Production Deployment Guide

## 系统要求
- Python 3.10+
- 4GB RAM (推荐 8GB)
- 网络连接 (LLM API + 技能集市)

## 安装

### Windows
```cmd
cd D:\LAAP
pip install -e .
laap
```

### Linux/macOS
```bash
cd /opt/laap
pip install -e .
./bin/laap
```

## 配置

### 环境变量 (.laap/.env)
```ini
# LLM Provider (必选其一)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...

# 可选
LAAP_PROVIDER=openai
LAAP_MODEL=gpt-4o
WEBHOOK_PORT=8765
```

## 启动模式

| 模式 | 命令 | 用途 |
|------|------|------|
| TUI | `laap` | 交互式聊天 (默认) |
| CLI 单次 | `laap "问题"` | 一次性查询 |
| 网关 | `laap --gateway` | 消息平台接入 |
| MCP Server | `laap --mcp` | IDE 工具集成 |

## 架构

```
+------------------+     +------------------+
|   CLI / TUI     |     |    Gateway       |
|  (用户交互)     |     |  (Telegram/DC)   |
+--------+---------+     +--------+---------+
         |                        |
         v                        v
+------------------+     +------------------+
|   Agent Core    |---->|   LLM Provider   |
|  (PSI Cognitive)|     |  (OpenAI/Claude) |
+--------+---------+     +------------------+
         |
    +----+----+----+----+
    |    |    |    |    |
    v    v    v    v    v
  Tools Memory MCP Skills Gateway
```

## 安全

- 所有 API Key 存储在 `~/.laap/.env`
- 命令安全检查自动启用
- 权限系统可配置
- 审计日志在 `~/.laap/logs/audit.log`

## 测试

```bash
pytest tests/ -v --tb=short     # 运行所有测试
pytest tests/ --cov=laap        # 覆盖率报告
```

## 故障排除

| 症状 | 解决方案 |
|------|----------|
| laap 闪退 | 运行 `diagnose.bat` |
| API Key 错误 | 检查 `~/.laap/.env` |
| 内存错误 | `python -c "from laap.memory.persistent import PersistentMemoryEngine;..."` |
| TUI 乱码 | 设置系统区域为 UTF-8 |
