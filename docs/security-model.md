# LAAP Security Model

## Defense-in-Depth Architecture

LAAP implements multiple layers of security:

```
Layer 1: Command Sandbox (OS-level isolation)
Layer 2: Permission Enforcer (approval-based access)
Layer 3: Path Scope (restricted file access)
Layer 4: Environment Sanitization (clean env vars)
Layer 5: API Key Validation (format checks)
Layer 6: Input Validation (command/argument validation)
```

## Sandbox Levels

| Level | Isolation | Use Case |
|-------|-----------|----------|
| `none` | None | Trusted environments |
| `basic` | Command validation | Local development |
| `standard` | + Path restrictions | Production |
| `strict` | + Linux namespace | Multi-tenant |
| `maximum` | + Network isolation | High security |

## Permission Model

Resources are checked against the permission enforcer:

- **always_allow**: Auto-approved (e.g., env:read)
- **allow_once**: One-time approval
- **ask**: User must approve each time
- **ask_timeout**: Ask with auto-approve timeout
- **always_deny**: Explicitly blocked

## Safe Development Practices

1. Never run LAAP as root/admin
2. Use environment variables for API keys
3. Keep your `.laap/` directory in `.gitignore`
4. Review permissions before approving
