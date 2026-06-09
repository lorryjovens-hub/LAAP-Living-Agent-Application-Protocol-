# LAAP Architecture Overview

## Multi-Language Strategy

LAAP uses a **three-language architecture** to maximize developer experience and runtime performance:

| Language | Role | Share |
|----------|------|-------|
| **Python** | Core framework, cognition, CLI, tools, gateways | ~65% |
| **Rust** | Performance engine, memory, search, sessions | ~25% |
| **TypeScript** | Web dashboard, RAG UI, API client | ~10% |

## Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│                    User Interface                    │
│  ┌─────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │  CLI    │  │   REPL   │  │  Web Dashboard(TS)  │  │
│  │ (Python)│  │ (Python) │  │  (React + Vite)    │  │
│  └─────────┘  └──────────┘  └────────────────────┘  │
├─────────────────────────────────────────────────────┤
│                     API Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ FastAPI  │  │  MCP     │  │  WebSocket SSE   │  │
│  │ REST     │  │ Server   │  │  Streaming       │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────┤
│                  Agent Core (Python)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Agent   │  │Lifelike  │  │   CodexAgent     │  │
│  │  Base    │  │ Agent    │  │   (Coding)       │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────┤
│           Cognitive Architecture (Python)            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Needs   │  │ Emotion  │  │   Awareness      │  │
│  │  (PSI)   │  │ (EG-MRSI)│  │   (Self Model)  │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────┤
│                Engine Layer (Rust + Python)          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Memory   │  │  RSI     │  │   Search(Rust)   │  │
│  │ (Rust)   │  │ Evolution│  │   (Rust)         │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────┤
│               Infrastructure                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Sandbox  │  │Permiss.  │  │   Session Store  │  │
│  │ (Python) │  │(Python)  │  │   (JSONL+SQLite) │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────┤
│                Integration Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ MCP      │  │ Plugins  │  │ 14 Gateways      │  │
│  │ Protocol │  │ + Hooks  │  │ (WeChat/Discord) │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Key Design Principles

1. **PSI Cognitive Architecture**: Needs → Emotion → Action → Learning cycle
2. **Multi-language Optimization**: Each language for its strengths
3. **Pluggable Everything**: Tools, memory backends, LLM providers, gateways
4. **Security by Default**: Sandbox, permissions, path scoping
5. **Observability**: Events, metrics, telemetry throughout
