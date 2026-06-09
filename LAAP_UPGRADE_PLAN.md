# LAAP 全面升级计划

> 基于全面分析结果，修复关键 Bug → 增强流式输出 + CLI → 补齐生产级特性 → 激活 LAAP 独有能力

## Global Context

- Repo root: `D:\LAAP`
- Python version: 3.10+
- Package: `laap` v0.3.0
- Core features: PSI cognitive architecture, RSI evolution engine, multi-LLM support, Swarm orchestration, hierarchical memory, 14-platform gateway, MCP client, Rust PyO3 core
- Critical known bugs: Anthropic tool calls broken, Rust core not integrated, duplicate tool registration, encoding issues in stability monitor
- Naming conventions: snake_case for files/functions, PascalCase for classes, UPPER for constants

---

## T1: Fix AnthropicProvider Tool Call Handling

**Severity: CRITICAL — Blocks all Anthropic users**

Canonical files:
- `/d/LAAP/laap/llm/provider.py` (lines 210-258, `AnthropicProvider.chat_stream`)

Description:
The `AnthropicProvider.chat_stream()` currently only handles `text_delta` events during streaming. It completely ignores `content_block_start` with `tool_use` type blocks. This means when using Anthropic Claude, the LLM can respond with tool calls but LAAP silently discards them — tools never execute.

Required changes:
1. In `AnthropicProvider.chat_stream()`, detect `content_block_start` events where `event.content_block.type == "tool_use"` and capture the tool name + input
2. Track partial tool calls across streaming chunks (Anthropic sends tool_use as a complete block, not incremental like OpenAI)
3. After the stream ends, collect all tool_use blocks and build the tool_calls structure matching the existing `StreamEvent` format
4. Yield a `StreamEvent(type="tool_call_start")` with the collected tool calls

Acceptance Criteria:
- When Anthropic Claude responds with a tool call, the stream yields `tool_call_start` events
- Tool name, arguments are correctly parsed
- The `StreamEvent._tool_calls` field contains valid tool call dicts
- Existing OpenAI/DeepSeek providers continue to work unchanged

Validation:
- `python -c "from laap.llm.provider import AnthropicProvider; print('OK')"`
- Set `ANTHROPIC_API_KEY` and run a tool-using chat through the agent
- Check that `tool_call_buffer` is populated in `StreamHandler`

---

## T2: Fix Duplicate Tool Registration + Base Agent Tool Conflicts

**Severity: HIGH — Causes double-registration errors**

Canonical files:
- `/d/LAAP/laap/agent/base.py` (lines 207-212, `_init_default_tools`)
- `/d/LAAP/laap/agent/codex.py` (lines 42-76, `_register_code_tools`)
- `/d/LAAP/laap/tools/code_edit.py` (lines 18-20, `register_all` guard)
- `/d/LAAP/laap/tools/shell.py` (lines 16-18, `register_all` guard)

Description:
Multiple issues:
1. `Agent.__init__()` calls `register_code_tools`, `register_shell_tools`, `register_web_tools` directly (line 210-212)
2. `CodexAgent._register_code_tools()` calls the **same** `register_all` functions again (lines 53-62)
3. Both `Agent.__init__()` AND `CodexAgent.__init__()` call `_init_default_tools()` which registers `run_python` and `apply_modification`
4. There's a `global registered` guard in each `register_all` but `_init_default_tools()` isn't guarded

Required changes:
1. In `agent/base.py`: Remove the direct `register_code_tools`/`register_shell_tools`/`register_web_tools` calls from `__init__()` — let subclasses decide what to register
2. In `agent/codex.py`: Make `_register_code_tools` idempotent with a similar `_registered` flag
3. Ensure `_init_default_tools()` has a guard against double registration
4. Verify `register_tool()` doesn't silently overwrite existing tools (or add a warning)

Acceptance Criteria:
- Creating a `CodexAgent` doesn't log any duplicate tool warnings
- `Agent` (base) and `LifelikeAgent` register tools exactly once
- `tool_registry.count` returns the correct number of unique tools
- Existing tool calls work correctly

Validation:
- `python -c "from laap.agent.codex import CodexAgent; a = CodexAgent(); assert a.tool_registry.count == a.tool_registry.count; print(f'Tools: {a.tool_registry.count}')"`
- Run the existing test suite: `python -m pytest tests/ -v`

---

## T3: Fix StabilityMonitor Character Encoding

**Severity: MEDIUM — Display corruption**

Canonical files:
- `/d/LAAP/laap/evaluation/stability.py` (lines 24-30)

Description:
The `StabilityMonitor.check()` method prints Chinese characters with incorrect encoding. Lines 24-30 contain garbled text like `"����Ч������ƫ��"` instead of proper Chinese text like `"情感效价偏负"`.

Required changes:
1. Fix all Chinese strings in `stability.py` to be proper UTF-8 encoded Chinese
2. Add `# -*- coding: utf-8 -*-` encoding declaration if not present
3. Ensure the file is saved with UTF-8 encoding

Acceptance Criteria:
- All strings display correctly in a UTF-8 terminal
- No garbled characters

Validation:
- `python -c "from laap.evaluation.stability import StabilityMonitor; print('OK')"`

---

## T4: Integrate Rust Core with Python

**Severity: HIGH — 500 lines of Rust unused**

Canonical files:
- `/d/LAAP/core/src/lib.rs`
- `/d/LAAP/core/Cargo.toml`
- `/d/LAAP/laap/memory/rust_backend/__init__.py`
- `/d/LAAP/laap/memory/hierarchical.py`

Description:
The Rust PyO3 core (`core/src/lib.rs`) implements MemoryEngine, TokenCounter, KeywordSearch, SessionManager, and ExperienceGraph — but the Python side never imports or uses these. Need to build the Rust crate and integrate it.

Required changes:
1. Verify `Cargo.toml` has proper `[lib]` section with `crate-type = ["cdylib"]`
2. Build the Rust crate: `cd core && cargo build --release`
3. In `laap/memory/rust_backend/__init__.py`, add proper import and fallback logic
4. Create a bridge in `laap/memory/provider.py` that selects between Rust and Python backends
5. Add a `TokenCounter` bridge in `laap/llm/provider.py` (use Rust token counter if available)
6. Add graceful fallback: if the Rust module isn't compiled, use pure Python

Acceptance Criteria:
- Rust core compiles successfully
- Python can import the compiled module
- Memory operations fall back to Python if Rust module unavailable
- Token counting works with both backends

Validation:
- `cd /d/LAAP/core && cargo build --release 2>&1`
- `python -c "import sys; sys.path.insert(0, 'core/target/release'); import laap_core; print(dir(laap_core))"`

---

## T5: Enhanced Streaming Output System

**Severity: HIGH — User-requested feature**

Canonical files:
- `/d/LAAP/laap/ui/stream_handler.py`
- `/d/LAAP/laap/ui/display.py`
- `/d/LAAP/laap/agent/base.py` (ToolCallLoop)

Description:
The current StreamHandler provides basic streaming but lacks:
1. Real-time token count display during streaming
2. Tool call progress with ETA/duration
3. Smooth multi-line streaming (not just single-line)
4. Stream pause/resume indicators
5. Token/s timing metrics
6. Proper handling of code blocks during streaming (formatting)
7. Streaming abort support (Ctrl+C during generation)

Required changes:
1. Enhance `StreamHandler.process_stream()` with:
   - Real-time per-token display with WPM/tokens-per-second counter
   - Code block aware streaming (detect ``` and use different formatting)
   - Smooth left-to-right token rendering with word-wrap awareness
   - Progress line showing tokens streamed and elapsed time
2. Add `async_process_stream()` for async streaming support
3. Add abort/stop functionality (check a `_stopped` flag during generation)
4. Add streaming statistics collection (tokens/s, time to first token, peak throughput)

Acceptance Criteria:
- Tokens appear character-by-character in real-time
- Token/s counter updates live during generation
- Code blocks are visually distinguished during streaming
- Ctrl+C can abort streaming mid-generation
- Stats (total tokens, time, tokens/s) shown after completion
- All existing functionality continues to work

Validation:
- Run `python -m laap.api.cli --interactive` and send a message
- Observe token-by-token streaming with live metrics
- Verify Ctrl+C abort works
- Verify code blocks within responses display correctly

---

## T6: Golden Dragon CLI Redesign

**Severity: HIGH — User-requested feature**

Canonical files:
- `/d/LAAP/laap/ui/display.py`
- `/d/LAAP/laap/cli/repl.py`
- `/d/LAAP/laap/cli/skins/dragon.py`
- `/d/LAAP/laap/cli/skins/engine.py`
- `/d/LAAP/laap/cli/logo_art.py`

Description:
Redesign the CLI to have a stunning, modern, living-computation themed interface. Moving beyond basic ANSI colors to a full terminal UI experience.

Required changes:
1. **Status Bar** (inspired by Claude Code but LAAP-themed):
   - Bottom status bar showing: Agent name, provider, model, tool count, step count, context usage
   - Update status bar in real-time as actions complete
   - `\0337` / `\0338` (save/restore cursor) for non-intrusive status bar

2. **Rich Prompt**:
   - Multi-line prompt showing current state
   - Golden dragon symbol + current agent name + step count + emotion indicator
   - Color changes based on emotional state (gold=calm, red=agitated, blue=focused)

3. **Enhanced Spinner**:
   - Animated golden dragon ASCII art (using the existing DRAGON_FRAMES but with better rendering)
   - Context-aware: different animation for thinking vs. tools vs. responding
   - Show tool count in the spinner line

4. **Section Formatting**:
   - Enhanced `format_section()` with box-drawing characters (╔═╗║╚═╝)
   - Colored section headers with background
   - Better code block rendering with syntax-coded borders

5. **Welcome Screen**:
   - Animated golden dragon ASCII logo with gradient color
   - Protocol/system status summary
   - Available commands hint

6. **Needs/Emotion Visualizations**:
   - Horizontal bar charts for needs levels (use █▓▒░ characters)
   - Emotional state indicator showing valence/arousal as 2D map
   - Fitness radar/spider chart (text-based)

Acceptance Criteria:
- Bottom status bar visible and updating
- Animated spinner uses dragon frames
- Sections use box-drawing characters
- Needs visualization shows all 5 needs with bars
- Prompt reflects agent state

Validation:
- `python -m laap.api.cli --interactive` and verify all visual elements
- Check status bar renders at the bottom
- Run `/status`, `/needs`, `/emotion` commands and verify formatting

---

## T7: Permission System with Approval Flow

**Severity: HIGH — Production requirement**

Canonical files:
- `/d/LAAP/laap/permissions/__init__.py`
- `/d/LAAP/laap/permissions/enforcer.py`
- `/d/LAAP/laap/permissions/policy.py`
- `/d/LAAP/laap/agent/base.py` (ToolCallLoop)

Description:
Implement Claude Code-style permission prompts for dangerous operations. The existing `permissions/` module has policy/enforcer stubs but they're not integrated into the agent's execution flow.

Required changes:
1. Implement `PermissionEnforcer` with:
   - Tool-level permission categories (safe, shell, filesystem, dangerous)
   - Per-session allow/deny/always-allow decisions
   - Interactive confirmation prompt for dangerous operations
   - Configurable trust level (local mode vs. remote mode)

2. Integrate into `ToolCallLoop.run()`:
   - Before executing each tool call, check permissions
   - If permission needed, print a styled confirmation prompt
   - Wait for user input (allow/deny/always-allow)
   - Track "always allow" decisions for the session

3. Default permission levels:
   - safe (read_file, search): auto-allow
   - filesystem (write_file, edit_file): prompt once per file
   - shell (run_command): prompt each time
   - dangerous (rm -rf, system modifications): always prompt, yellow/red warning

Acceptance Criteria:
- Read-only operations proceed without prompts
- Write/edit operations prompt for confirmation (first time per file)
- Shell execution shows a styled prompt with command preview
- User can always-allow for the session
- Permission decisions are logged

Validation:
- Test with `run_command("echo hello")` — should not prompt (safe)
- Test with `run_command("rm -rf /")` — should block
- Test with `write_file("test.txt", "hello")` — should prompt first time
- `python -m pytest tests/test_permissions.py -v` if tests exist

---

## T8: Shell Sandbox with OS-Level Isolation

**Severity: HIGH — Security critical**

Canonical files:
- `/d/LAAP/laap/shell/__init__.py`
- `/d/LAAP/laap/shell/executor.py`
- `/d/LAAP/laap/shell/sandbox.py`

Description:
The current shell executor only has a simple command blacklist (`DANGEROUS_COMMANDS`). Need proper OS-level sandbox isolation.

Required changes:
1. In `laap/shell/sandbox.py`, implement:
   - **Windows**: Use Job Object API via `ctypes` to create a restricted job that:
     - Limits process creation
     - Sets memory limit
     - Kills child processes on job close
   - **Linux**: Use `unshare()` for namespace isolation
   - **Fallback**: Enhanced command validation with regex-based allow/block lists

2. In `laap/shell/executor.py`, integrate sandbox:
   - Add `sandbox_level` parameter to `run()` (none/basic/full)
   - Level "full" wraps execution in OS sandbox
   - Level "basic" uses enhanced command validation
   - Level "none" uses current behavior

3. Add path allowlist/blocklist checking

Acceptance Criteria:
- Sandbox module loads on both Windows and Linux
- Dangerous commands are blocked with a styled error message
- Shell execution works normally for safe commands
- No breaking changes to existing tool calls

Validation:
- `python -c "from laap.shell.sandbox import SandboxEnforcer; s = SandboxEnforcer(); print('OK')"`
- `python -c "from laap.shell.executor import shell; r = shell.run('echo hello', check_dangerous=True); print(r)"`
- `python -c "from laap.shell.executor import shell; r = shell.run('rm -rf /', check_dangerous=True); print(r.get('success'))"`  # should be False

---

## T9: MCP Client Hardening

**Severity: MEDIUM — Reliability**

Canonical files:
- `/d/LAAP/laap/mcp/client.py`
- `/d/LAAP/laap/mcp/server.py`
- `/d/LAAP/laap/mcp/lifecycle.py`

Description:
The MCP client uses fragile line-based JSON-RPC communication. Need to implement proper framing, reconnection, and lifecycle management.

Required changes:
1. Replace `readline()` based parsing with proper Content-Length header based framing (standard MCP transport)
2. Add reconnection logic with exponential backoff
3. Add timeout for MCP operations
4. Add health check / ping interval
5. Add `MCPTool` to `ToolDef` conversion for use with LLM providers
6. Add better error reporting when MCP server fails
7. Create `mcp/server.py` — the MCP server implementation that exposes LAAP's own tools via MCP
8. Create `mcp/lifecycle.py` — lifecycle management for MCP servers (start/stop/restart)

Acceptance Criteria:
- MCP client uses Content-Length framing (standard protocol)
- Connection failures trigger retry with backoff
- Timeout on stuck operations
- LAAP tools can be exposed via MCP server to other clients
- Existing MCP configuration format still works

Validation:
- `python -c "from laap.mcp.client import MCPClient; c = MCPClient(); print('OK')"`
- `python -c "from laap.mcp.server import MCPServer; print('OK')"` if server module exists

---

## T10: LLM-Generated RSI Proposals

**Severity: MEDIUM — Makes RSI actually useful**

Canonical files:
- `/d/LAAP/laap/evolution/rsi.py`
- `/d/LAAP/laap/agent/lifelike.py`

Description:
Currently RSI proposals are generated from 4 hardcoded templates (adjust_exploration, adjust_learning_rate, etc.). Replace with LLM-generated proposals that analyze agent state and produce genuinely novel improvement suggestions.

Required changes:
1. Add a `_llm_generate_proposal()` method to `RSIEngine` that:
   - Gathers agent state (needs profile, emotion state, recent rewards, fitness history, skill proficiencies)
   - Constructs a prompt describing the agent's "life" so far
   - Calls the LLM with this context and asks for 1-3 improvement proposals
   - Parses the LLM response into structured `ImprovementProposal` objects

2. The LLM prompt should ask for:
   - Hypothesis about what to change and why
   - Specific parameter modifications
   - Expected impact
   - Confidence level

3. Keep the template-based proposals as fallback when LLM isn't available

4. Enhance `_sandbox_test()` to evaluate proposals more thoroughly:
   - Run multiple simulation steps before/after
   - Measure composite fitness delta more accurately

Acceptance Criteria:
- When LLM is available, proposals are generated by LLM
- Proposal content is relevant to agent's current state
- Fallback to templates works when LLM is unavailable
- Existing RSI pipeline (test → adopt/reject) works unchanged

Validation:
- `python -c "from laap.evolution.rsi import RSIEngine; print('OK')"`
- Run LifelikeAgent for 30+ steps and observe proposal quality

---

## T11: Vector Embedding Integration

**Severity: MEDIUM — Memory enhancement**

Canonical files:
- `/d/LAAP/laap/memory/hierarchical.py`
- `/d/LAAP/laap/memory/provider.py`

Description:
The `MemoryItem` class has an `embedding` field that's always `None`. Need to implement actual embedding generation and semantic search.

Required changes:
1. Add embedding generation in `HierarchicalMemory`:
   - Option A: Use `sentence-transformers` (requires `pip install sentence-transformers`)
   - Option B: Use Rust `fastembed` via the core module
   - Option C: Use LLM API embeddings (if provider supports it)
   - Auto-detect which is available with fallback chain

2. When storing episodic memories, generate and store embedding
3. Add `semantic_search(query, limit=5)` method that:
   - Generates embedding for the query
   - Computes cosine similarity against all stored memories
   - Returns top matches

4. Integrate semantic search into `recall()` as an option:
   - If `query_tags` matches a semantic search, boost those results
   - Add `use_semantic=True` parameter

Acceptance Criteria:
- Embedding generation works with at least one backend
- `semantic_search()` returns relevant results
- Falls back gracefully when no embedding backend is available
- Performance is reasonable (batched embeddings)

Validation:
- `python -c "from laap.memory.hierarchical import HierarchicalMemory; m = HierarchicalMemory(); m.remember('test', importance=0.5); print('OK')"`
- If sentence-transformers is installed: test semantic search returns meaningful results

---

## T12: Test Framework + Critical Tests

**Severity: HIGH — Quality foundation**

Canonical files:
- `/d/LAAP/tests/`
- `/d/LAAP/pyproject.toml` (pytest config already exists)
- `/d/LAAP/.github/workflows/python-ci.yml`

Description:
Build a proper test foundation. The existing 14 test files (~206 lines) are a good start but need expansion.

Required changes:
1. Create `tests/fixtures.py` with shared test fixtures:
   - Mock LLM provider that returns controlled responses
   - Pre-configured Agent/LifelikeAgent instances
   - Temporary directory fixture for file operations

2. Create comprehensive tests:
   - `tests/test_llm_provider.py` — Test all provider implementations, especially tool call flow
   - `tests/test_tool_registry.py` — Tool registration, calling, error handling
   - `tests/test_code_edit.py` — File read/write/edit operations
   - `tests/test_shell.py` — Shell execution, safety checks
   - `tests/test_stream_handler.py` — Streaming output processing
   - `tests/test_rsi_engine.py` — Proposal generation, sandbox test, adoption

3. Ensure tests can run without API keys (use mocks)
4. Configure coverage: `python -m pytest tests/ --cov=laap --cov-report=term`

Acceptance Criteria:
- Minimum 40 tests that pass without any API keys
- Core modules (llm, tools, agent, memory) have >30% coverage
- Tests run in < 30 seconds
- All tests pass

Validation:
- `cd /d/LAAP && python -m pytest tests/ -v --tb=short 2>&1 | tail -60`

---

## T13: Session Persistence System

**Severity: MEDIUM — Data safety**

Canonical files:
- `/d/LAAP/laap/store/__init__.py`
- `/d/LAAP/laap/store/session.py`
- `/d/LAAP/laap/store/session_manager.py`

Description:
Implement session save/load with file-based persistence so agent state (memory, needs, emotions, conversation history) survives restarts.

Required changes:
1. In `laap/store/session.py`, implement `Session` dataclass that stores:
   - Agent config (provider, model, exploration rate, learning rate)
   - Memory state (episodic memories, semantic knowledge, skills, reflections)
   - Need levels (all 5 needs with current/target/decay)
   - Emotional state (valence, arousal, dominance, confidence)
   - Reward history
   - Conversation history (recent messages)

2. In `laap/store/session_manager.py`, implement:
   - `save(session_id, agent)` — serialize agent state to JSON file
   - `load(session_id, agent)` — deserialize and restore agent state
   - `list_sessions()` — list all saved sessions
   - `delete(session_id)` — remove a saved session
   - Save location: `~/.laap/sessions/`
   - Auto-save every N steps (configurable)

3. Integrate with REPL:
   - Auto-save on exit
   - `/save [name]` — manual save
   - `/load [name]` — manual load
   - `/sessions` — list sessions

Acceptance Criteria:
- Agent state can be saved to disk and restored
- After restore, needs levels, emotions, and memory are intact
- Auto-save triggers every 20 steps (configurable)
- Failed save doesn't crash the agent

Validation:
- `python -c "from laap.store.session_manager import SessionManager; sm = SessionManager(); print('OK')"`
- Test save then load across REPL sessions

---

## T14: Gateway Platform Implementation (Telegram + Slack)

**Severity: LOW-MEDIUM — Communication**

Canonical files:
- `/d/LAAP/laap/gateway/platforms/telegram.py`
- `/d/LAAP/laap/gateway/platforms/slack.py`
- `/d/LAAP/laap/gateway/base.py`

Description:
Most gateway platform adapters are empty stubs. Implement the two most popular ones: Telegram and Slack.

Required changes:
1. **Telegram** (`telegram.py`):
   - Implement `send()` via Telegram Bot API HTTP requests
   - Implement `start()` with polling (getUpdates loop)
   - Handle message parsing (text, photos, documents)
   - Connect incoming messages to gateway's `_handle_message`
   - Support markdown formatting in outgoing messages

2. **Slack** (`slack.py`):
   - Implement `send()` via Slack Web API (webhook or socket mode)
   - Implement `start()` with Socket Mode for real-time events
   - Parse messages, threads, reactions
   - Connect to gateway

3. Both should:
   - Handle reconnection on connection loss
   - Log errors without crashing
   - Support configurable polling interval / event filtering

Acceptance Criteria:
- Telegram adapter sends and receives messages
- Slack adapter sends and receives messages  
- Both handle disconnection gracefully
- Gateway broadcasts work with both platforms

Validation:
- `python -c "from laap.gateway.platforms.telegram import TelegramAdapter; print('OK')"`
- `python -c "from laap.gateway.platforms.slack import SlackAdapter; print('OK')"`

---

## T15: Documentation + Final Integration

**Severity: MEDIUM — Knowledge sharing**

Canonical files:
- `/d/LAAP/README.md`
- `/d/LAAP/docs/`

Description:
Update documentation to reflect all changes made, and run final integration verification.

Required changes:
1. Update `README.md` with:
   - New features and capabilities
   - Updated architecture diagram
   - CLI command reference
   - Screenshots/descriptions of the new CLI

2. Create `docs/streaming.md`:
   - How streaming works
   - StreamHandler API
   - Customizing stream display

3. Create `docs/cli-commands.md`:
   - All REPL commands with examples
   - Status indicators legend

4. Run final integration pass:
   - Verify all modules import correctly
   - Run test suite
   - Check for any import errors or broken references
   - Verify the CLI starts

Acceptance Criteria:
- README reflects current state
- New CLI features documented
- All modules import without errors
- Test suite passes

Validation:
- `python -c "import laap; print(laap.__version__)"`
- `python -m pytest tests/ -v --tb=short`
