# LAAP CLI Commands

## Basic Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `help` | `?`, `h` | Show help |
| `exit` | `quit`, `bye` | Exit LAAP |
| `status` | `stats`, `info` | Show agent status |
| `self` | `whoami` | Show self-model |

## Cognitive Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `needs` | `drives`, `psi` | Show need drive system |
| `emotion` | `mood`, `affect` | Show emotional state |
| `evolve` | `rsi`, `improve` | Trigger RSI cycle |
| `fitness` | `score`, `eval` | Show fitness evaluation |
| `grow` | `reflect`, `learn` | Trigger reflection |

## Tool Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `tools` | `functions` | List available tools |
| `fork` | `split` | Fork agent |
| `mutate` | - | Mutate agent config |
| `lineage` | - | Show agent lineage |

## Orchestration Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `swarm` | `hive` | Swarm orchestration |
| `immune` | `health` | System health check |

## Configuration Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `config` | `settings` | Configuration menu |
| `model` | `llm` | Model/provider settings |
| `reset` | - | Reset agent state |
| `clear` | - | Clear screen |
| `save` | - | Save session |
| `load` | - | Load session |
| `share` | `broadcast` | Broadcast to swarm |

## Server Mode

```bash
laap serve --host 0.0.0.0 --port 8080
```

Available endpoints:
- `GET /health` — Health check
- `POST /chat` — Chat with agent
- `GET /status` — Agent status
- `POST /tools/{name}` — Execute tool
