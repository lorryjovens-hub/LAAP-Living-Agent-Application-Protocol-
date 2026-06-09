# laap-ai · npm package

> **LAAP — Lifeform Autonomous Adaptive Protocol**  
> A self-evolving cognitive agent runtime. This npm package is a thin shim
> that installs the Python LAAP CLI into an isolated venv and forwards all
> arguments to it.

[![npm](https://img.shields.io/npm/v/laap-ai)](https://www.npmjs.com/package/laap-ai)
[![MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

## One-line install

```bash
# Try it without installing:
npx laap-ai --version

# Or install globally and use the `laap` command:
npm install -g laap-ai
laap --version
laap -i               # interactive REPL
laap -q "hi there"    # one-shot question
```

The first invocation will:

1. Detect an existing `laap` on `PATH` (e.g. installed via `uv tool install`)
2. Otherwise locate a Python ≥ 3.10 interpreter
3. Create an isolated venv at `~/.laap/npm/venv`
4. Install `laap[cli]` (or `laap[tui]` if `LAAP_EXTRAS=tui`) into it
5. Forward all subsequent `laap` calls straight to that binary

Subsequent invocations are **near-instant** (a single `spawn`).

## Configuration

| Env var               | Default | Effect                                            |
|-----------------------|---------|---------------------------------------------------|
| `LAAP_VERSION`        | `0.3.0` | Version of `laap` to install                      |
| `LAAP_EXTRAS`         | `cli`   | Pip extras to add, e.g. `tui`, `all`              |
| `LAAP_POSTINSTALL_TIMEOUT_MS` | `120000` | Postinstall timeout in ms (0 = disable)     |

## Updating

```bash
npm install -g laap-ai@latest
```

## Uninstalling

```bash
npm uninstall -g laap-ai
# (the postuninstall hook will remove ~/.laap/npm)
```

## Why a Python shim?

LAAP is a Python project with a Rust acceleration layer. We don't want to
re-implement the cognitive engine in JavaScript. The npm package is a
package-manager-friendly front door that handles the install + spawn for
you. If you'd rather use uv directly, see [install-uv.sh][1].

[1]: https://github.com/laap-agi/laap/blob/main/installers/install-uv.sh

## License

MIT © LAAP Team
