# LAAP Architecture

## Core Layers

```
Layer 0: CLI/TUI/Gateway    (用户界面层)
Layer 1: Agent              (认知引擎层)  
Layer 2: LLM Provider       (推理层)
Layer 3: Tools/Memory/MCP   (能力层)
Layer 4: Skills/Hub         (扩展层)
```

## Key Design Decisions

1. **Provider Pattern**: 所有外部依赖 (LLM, Memory, MCP) 通过抽象接口
2. **Event-Driven**: Gateway 基于异步事件循环
3. **Plugin Architecture**: Skills, Memory Providers 可热插拔
4. **Security First**: 所有命令执行经过 threat detection + permission check
