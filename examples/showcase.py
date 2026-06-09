"""
LAAP — Comprehensive Showcase Demo
Demonstrates all upgraded features.
"""

from __future__ import annotations
import sys, os, time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from laap import __version__

C = lambda: None
attrs = {
    "GOLD": "\033[38;5;214m", "GOLD_B": "\033[38;5;220m", "GOLD_D": "\033[38;5;179m",
    "GREEN": "\033[38;5;82m", "CYAN": "\033[38;5;51m", "GRAY": "\033[38;5;244m",
    "DIM": "\033[38;5;240m", "RESET": "\033[0m", "BOLD": "\033[1m", "RED": "\033[38;5;196m",
}
for k, v in attrs.items(): setattr(C, k, v)


def section(title):
    w = 50
    print(f"\n  {C.GOLD}[{'-'*w}]{C.RESET}")
    print(f"  {C.GOLD}|{C.RESET} {C.BOLD}{C.GOLD_B}{title}{C.RESET}{' '*(w-len(title))} {C.GOLD}|{C.RESET}")
    print(f"  {C.GOLD}[{'-'*w}]{C.RESET}\n")


def ok(text): print(f"  {C.GREEN}v{C.RESET} {text}")
def info(text): print(f"  {C.DIM}i {text}{C.RESET}")


def demo():
    print(f"\n  {C.GOLD_B}{C.BOLD}* LAAP v{__version__} Showcase{C.RESET}")
    print(f"  {C.GOLD_D}{'-'*50}{C.RESET}\n")

    # 1. Streaming
    section("1. Enhanced Streaming Output")
    from laap.ui.stream_handler import CodeBlockTracker, StreamStats
    cbt = CodeBlockTracker()
    for t in ["Hello", "```python", "def foo():", "    pass", "```", "Done"]:
        cbt.feed(t)
    info(f"CodeBlockTracker: in_code={cbt.in_code_block}, lang={cbt.code_lang}")
    ss = StreamStats()
    ss.start()
    for _ in range(50): ss.record_token()
    ss.record_tool_call()
    ss.finish()
    info(f"StreamStats: {ss.token_count} tokens, {ss.tokens_per_second:.0f} tok/s")
    ok("Streaming OK")

    # 2. CLI
    section("2. Golden Dragon CLI")
    from laap.ui.display import needs_bar_chart, emotion_grid, format_section_box
    profile = {k: {"current": v, "drive": max(0, 0.8-v)} for k, v in
               {"certainty": .72, "competence": .45, "autonomy": .81, "relatedness": .53, "energy": .38}.items()}
    print(needs_bar_chart(profile)[:3]+"  ...")
    es = {"valence": .42, "arousal": .67, "dominance": .55, "confidence": .73}
    print(emotion_grid(es).split("\n")[0]+" ...")
    print(format_section_box("Test").split("\n")[0]+" ...")
    ok("CLI visualizations OK")

    # 3. Permissions
    section("3. Permission System")
    from laap.permissions.enforcer import PermissionEnforcer, PermissionLevel
    e = PermissionEnforcer()
    e.add_permission("shell:execute", PermissionLevel.ALWAYS_ALLOW)
    assert e.check("shell:execute", "demo")
    e.add_permission("shell:dangerous", PermissionLevel.ALWAYS_DENY)
    assert not e.check("shell:dangerous", "rm -rf")
    ok("Permission system OK")

    # 4. RSI
    section("4. RSI Evolution")
    from laap.evolution.rsi import RSIEngine
    rsi = RSIEngine()
    info(f"Templates: {len(rsi._templates)} (with LLM fallback)")
    ok("RSI OK")

    # 5. Memory embeddings
    section("5. Semantic Memory")
    from laap.memory.hierarchical import HierarchicalMemory
    mem = HierarchicalMemory()
    mem.remember("LAAP PSI cognitive architecture", tags=["laap"], importance=0.9)
    results = mem.semantic_search("LAAP", limit=3)
    info(f"Semantic search: {len(results)} results")
    ok("Memory embeddings OK")

    # 6. Sessions
    section("6. Session Persistence")
    from laap.store.session_manager import SessionManager
    sm = SessionManager()
    info(f"Saved sessions: {len(sm.list_agent_states())}")
    ok("Sessions OK")

    # 7. Rust
    section("7. Rust Core")
    from laap.memory.rust_backend import rust_available
    if rust_available():
        from laap.memory.rust_backend import RustTokenCounter
        info(f"TokenCounter: {RustTokenCounter().count('LAAP')} tokens")
        ok("Rust core ACTIVE")
    else:
        info("Rust not compiled — Python fallback")

    # 8. Gateway
    section("8. Multi-Platform Gateway")
    from laap.gateway.platforms.telegram import TelegramAdapter
    from laap.gateway.platforms.slack import SlackAdapter
    ok("Telegram + Slack adapters loaded")

    # Summary
    print(f"\n  {C.GOLD_B}{C.BOLD}{'-'*45}{C.RESET}")
    print(f"  {C.GREEN}v{C.RESET} Streaming | CLI | Permissions | RSI | Memory | Sessions | Rust | Gateway")
    print(f"  {C.GOLD_B}{C.BOLD}{'-'*45}{C.RESET}\n")

if __name__ == "__main__":
    demo()
