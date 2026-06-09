"""
LAAP — Streaming Response Handler
Bridges LLM streaming + tool call loop with the golden dragon UI.
Provides real-time feedback for every stage of processing:
  - Real-time token streaming with code-block awareness
  - Tool call lifecycle (start → running → result)
  - Thinking/chain-of-thought indicators
  - Streaming performance stats (tok/s, TTFT)
  - Async streaming support
  - Memory usage tracking
  - Graceful abort (Ctrl+C)
"""

from __future__ import annotations
import sys, time, json, shutil, signal, threading, os
from typing import Any, Callable, Dict, List, Optional, Generator, AsyncIterator
from dataclasses import dataclass, field

from laap.llm.provider import LLMProvider, Message, ToolDef, StreamEvent
from laap.ui.display import (
    C, get_spinner, format_response, format_tool_start, format_tool_result,
    format_error, format_divider, TokenDisplay, context_indicator,
)


class CodeBlockTracker:
    """Tracks whether we're inside a code block during streaming."""

    def __init__(self):
        self.in_code_block = False
        self.code_lang = ""
        self.code_lines = []
        self._buffer = ""

    def feed(self, token: str) -> bool:
        """Feed a token and return True if currently inside a code block."""
        self._buffer += token
        # Detect opening ```
        if not self.in_code_block and "```" in self._buffer:
            self.in_code_block = True
            idx = self._buffer.index("```")
            # Extract language after ```
            rest = self._buffer[idx + 3:].strip().split("\n")[0]
            self.code_lang = rest.strip()
            self._buffer = ""
            return True
        # Detect closing ```
        if self.in_code_block and "```" in token:
            self.in_code_block = False
            self.code_lang = ""
            self._buffer = ""
            return False
        if self.in_code_block:
            self.code_lines.append(token)
        return self.in_code_block


class ThinkingIndicator:
    """Detects and renders thinking/reasoning tokens from chain-of-thought.

    Many LLMs emit  or  blocks that should be
    visually distinguished from normal output.
    """

    def __init__(self):
        self.in_thinking = False
        self.thinking_content = ""
        self._buffer = ""

    def feed(self, token: str) -> bool:
        """Feed a token; returns True if currently inside a thinking block."""
        self._buffer += token

        # Detect opening thinking tag
        if not self.in_thinking and "```thinking" in self._buffer.lower():
            self.in_thinking = True
            idx = self._buffer.lower().index("```thinking")
            self._buffer = ""
            return True

        # Also detect <thinking> XML tag
        if not self.in_thinking and "<thinking>" in self._buffer.lower():
            self.in_thinking = True
            idx = self._buffer.lower().index("<thinking>")
            self._buffer = ""
            return True

        # Detect closing
        if self.in_thinking:
            if "```" in token or "</thinking>" in token.lower():
                self.in_thinking = False
                self.thinking_content = self._buffer
                self._buffer = ""
                return False
            self._buffer += token
            self.thinking_content = self._buffer

        return self.in_thinking

    def render_thinking_line(self) -> str:
        """Return a formatted thinking indicator line."""
        if not self.thinking_content:
            return ""
        preview = self.thinking_content.strip()[:60].replace("\n", " ")
        return f"  {C.BLUE}⟐{C.RESET} {C.DIM}thinking: {preview}{'…' if len(self.thinking_content) > 60 else ''}{C.RESET}"


class StreamStats:
    """Collect streaming performance statistics."""

    def __init__(self):
        self.token_count = 0
        self.start_time = 0.0
        self.first_token_time = 0.0
        self.end_time = 0.0
        self.tool_call_count = 0
        self.error_count = 0
        self.thinking_tokens = 0
        self._peak_memory_mb = 0.0

    def start(self):
        self.start_time = time.time()

    def record_token(self):
        if self.token_count == 0:
            self.first_token_time = time.time()
        self.token_count += 1

    def record_tool_call(self):
        self.tool_call_count += 1

    def record_error(self):
        self.error_count += 1

    def record_thinking_token(self):
        self.thinking_tokens += 1
        self.token_count += 1

    def sample_memory(self):
        """Sample current process memory and update peak."""
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            mb = proc.memory_info().rss / (1024 * 1024)
            self._peak_memory_mb = max(self._peak_memory_mb, mb)
            return mb
        except ImportError:
            return 0.0

    @property
    def peak_memory_mb(self) -> float:
        return self._peak_memory_mb

    def finish(self):
        self.end_time = time.time()

    @property
    def elapsed(self) -> float:
        return self.end_time - self.start_time

    @property
    def time_to_first_token(self) -> float:
        if self.first_token_time == 0:
            return 0
        return self.first_token_time - self.start_time

    @property
    def tokens_per_second(self) -> float:
        t = self.elapsed
        return self.token_count / t if t > 0 else 0

    def display(self) -> str:
        """Return a formatted stats line."""
        parts = [
            f"{C.GOLD}◆{C.RESET} {C.DIM}stream{C.RESET}",
            f"{self.token_count} tok",
            f"{self.tokens_per_second:.1f} tok/s",
        ]
        if self.time_to_first_token > 0:
            parts.append(f"ttft={self.time_to_first_token*1000:.0f}ms")
        parts.append(f"{self.elapsed:.1f}s")
        if self.tool_call_count:
            parts.append(f"{self.tool_call_count} tools")
        if self.error_count:
            parts.append(f"{C.RED}{self.error_count} err{C.RESET}")
        if self.thinking_tokens:
            parts.append(f"⟐{self.thinking_tokens} think")
        if self._peak_memory_mb:
            parts.append(f"{self._peak_memory_mb:.0f}MB")
        return "  " + " | ".join(parts)


class _NullSpinner:
    """No-op spinner for non-TTY or piped output. All methods are silent."""
    def start(self, msg=""): pass
    def set_status(self, status=""): pass
    def stop(self): pass
    def add_tool(self, name, args=None): pass
    def complete_tool(self, name, success=True, result=""): pass


class StreamHandler:
    """Handles LLM streaming output with rich UI feedback.

    Usage:
        handler = StreamHandler()
        content = handler.process_stream(provider.chat_stream(messages, tools))
    """

    def __init__(self, verbose: bool = True, show_tokens: bool = False,
                 file: Optional[Any] = None, use_spinner: Optional[bool] = None):
        self.verbose = verbose
        self.show_tokens = show_tokens
        self._file = file or sys.stdout
        # Auto-detect: disable spinner when output is not a TTY (piped, captured)
        if use_spinner is None:
            use_spinner = self._file.isatty()
        self._use_spinner = use_spinner
        self.spinner = get_spinner() if use_spinner else _NullSpinner()
        self.token_display = TokenDisplay() if show_tokens else None
        self.tool_results: List[Dict] = []
        self.content = ""
        self.tool_call_buffer: List[Dict] = []
        self._last_tool_count = 0
        self._start_time = time.time()
        self._stopped = False
        self._code_tracker = CodeBlockTracker()
        self._thinking_indicator = ThinkingIndicator()
        self.stats = StreamStats()
        self._token_counter = 0
        self._last_stat_update = 0.0
        self._last_error: Optional[str] = None
        self._error_recovery_count = 0

    def _safe_write(self, text: str):
        """Write to output file, safely encoding Unicode for the terminal.

        Handles terminals that don't support certain Unicode chars (e.g. GBK on
        Windows Chinese systems) by replacing problematic characters with ASCII.
        """
        f = self._file
        try:
            f.write(text)
        except UnicodeEncodeError:
            safe = text.encode('ascii', errors='replace').decode('ascii')
            f.write(safe)
        f.flush()

    def _safe_print(self, text: str, end: str = "\n"):
        """Print to output file with encoding-safe Unicode handling."""
        self._safe_write(text + end)

    def stop(self):
        """Signal the stream to stop (for Ctrl+C abort)."""
        self._stopped = True

    def process_stream(self, stream: Generator[StreamEvent, None, None],
                       tools: Optional[List[ToolDef]] = None,
                       max_retries: int = 0) -> str:
        """Process a streaming LLM response with real-time UI updates.

        Args:
            stream: Generator yielding StreamEvent objects
            tools: Optional tool definitions for rendering
            max_retries: Number of error retries (0 = no retry)

        Returns:
            Concatenated content from all text tokens
        """
        self.content = ""
        self.tool_call_buffer = []
        self._start_time = time.time()
        self._stopped = False
        self._code_tracker = CodeBlockTracker()
        self._thinking_indicator = ThinkingIndicator()
        self._token_counter = 0
        self._last_stat_update = 0.0
        self.stats = StreamStats()
        self.stats.start()
        tool_calls_seen = 0
        retries_left = max_retries

        # Start spinner (only in CLI mode)
        if self._use_spinner and self.spinner:
            self.spinner.start("Ao is thinking")
            self.spinner.set_status("thinking")

        while retries_left >= 0:
            try:
                for event in stream:
                    if self._stopped:
                        break

                    if event.type == "token":
                        self.stats.record_token()

                        # Check for thinking indicator before rendering
                        is_thinking = self._thinking_indicator.feed(event.content)
                        if is_thinking:
                            self.stats.record_thinking_token()
                            # Show thinking indicator visually
                            if self.verbose and self._token_counter == 0:
                                self._render_thinking_indicator()

                        if self.verbose and not self.tool_call_buffer and not is_thinking:
                            self._render_token(event.content)

                        self.content += event.content
                        self._token_counter += 1

                        # Update live stats every 10 tokens
                        if self._token_counter % 10 == 0 and self.verbose:
                            now = time.time()
                            if now - self._last_stat_update > 0.5:
                                self._render_stats_inline()
                                self._last_stat_update = now

                        if self.token_display:
                            self.token_display.update(tokens_out=1)

                    elif event.type == "tool_call_start":
                        self.stats.record_tool_call()
                        if self.verbose and self.content:
                            self._safe_write(f"\n\n")
                        calls = (event.tool_call or {}).get("calls", [])
                        self.tool_call_buffer = calls
                        tool_calls_seen = len(calls)

                        for tc in calls:
                            name = tc.get("function", {}).get("name", "?")
                            try:
                                args = json.loads(tc.get("function", {}).get("arguments", "{}"))
                            except json.JSONDecodeError:
                                args = {}

                            line = format_tool_start(name, args)
                            self._safe_write(f"\r{C.CLEAR_LINE}{line}\n")
                            if self.spinner:
                                self.spinner.add_tool(name, args)

                    elif event.type == "done":
                        if self.verbose and self.content and not self.tool_call_buffer:
                            self._safe_write(f"\n")
                        self.stats.finish()
                        break  # Successfully completed

                    elif event.type == "error":
                        self.stats.record_error()
                        err_msg = event.error or "Unknown error"
                        self._last_error = err_msg
                        if self.verbose:
                            self._safe_write(f"\r{C.CLEAR_LINE}{format_error(err_msg)}\n")
                        raise IOError(err_msg)

                # If we got here without error, break the retry loop
                break

            except (IOError, ConnectionError, TimeoutError) as e:
                self.stats.record_error()
                retries_left -= 1
                if retries_left >= 0:
                    self._error_recovery_count += 1
                    if self.verbose:
                        self._safe_write(
                            f"\r{C.CLEAR_LINE}  {C.YELLOW}⟳{C.RESET} "
                            f"{C.DIM}retry {max_retries - retries_left}/{max_retries}"
                            f" after: {e}{C.RESET}\n"
                        )
                    # Reset for retry — keep accumulated content, re-create stream
                    # Note: caller must provide a fresh stream on retry
                    continue
                else:
                    # Out of retries — re-raise so caller sees the error
                    raise

        # Cleanup
        if self.spinner:
            self.spinner.stop()

        # Show final stream stats
        if self.verbose and self.stats.token_count > 0:
            self._safe_write(f"\r{C.CLEAR_LINE}{self.stats.display()}\n")

        return self.content

    async def async_process_stream(
        self,
        stream: AsyncIterator[StreamEvent],
        tools: Optional[List[ToolDef]] = None,
    ) -> str:
        """Async version of process_stream for async LLM providers.

        Args:
            stream: AsyncIterator yielding StreamEvent objects
            tools: Optional tool definitions for rendering

        Returns:
            Concatenated content from all text tokens
        """
        self.content = ""
        self.tool_call_buffer = []
        self._start_time = time.time()
        self._stopped = False
        self._code_tracker = CodeBlockTracker()
        self._thinking_indicator = ThinkingIndicator()
        self._token_counter = 0
        self._last_stat_update = 0.0
        self.stats = StreamStats()
        self.stats.start()

        if self.spinner:
            self.spinner.start("Ao is thinking")
            self.spinner.set_status("thinking")

        async for event in stream:
            if self._stopped:
                break

            if event.type == "token":
                self.stats.record_token()

                is_thinking = self._thinking_indicator.feed(event.content)
                if is_thinking and self.verbose and self._token_counter == 0:
                    self._render_thinking_indicator()

                if self.verbose and not self.tool_call_buffer and not is_thinking:
                    self._render_token(event.content)

                self.content += event.content
                self._token_counter += 1

                if self._token_counter % 10 == 0 and self.verbose:
                    now = time.time()
                    if now - self._last_stat_update > 0.5:
                        self._render_stats_inline()
                        self._last_stat_update = now

            elif event.type == "tool_call_start":
                self.stats.record_tool_call()
                if self.verbose and self.content:
                    self._safe_write("\n\n")
                    
                calls = (event.tool_call or {}).get("calls", [])
                self.tool_call_buffer = calls

                for tc in calls:
                    name = tc.get("function", {}).get("name", "?")
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except (json.JSONDecodeError, KeyError):
                        args = {}
                    line = format_tool_start(name, args)
                    self._safe_write(f"\r{C.CLEAR_LINE}{line}\n")
                    if self.spinner:
                        self.spinner.add_tool(name, args)

            elif event.type == "done":
                if self.verbose and self.content and not self.tool_call_buffer:
                    self._safe_write("\n")
                self.stats.finish()

            elif event.type == "error":
                self.stats.record_error()
                err = event.error or "Unknown error"
                self._last_error = err
                if self.verbose:
                    self._safe_write(f"\r{C.CLEAR_LINE}{format_error(err)}\n")
                    
        if self.spinner:
            self.spinner.stop()

        if self.verbose and self.stats.token_count > 0:
            self._safe_write(f"\r{C.CLEAR_LINE}{self.stats.display()}\n")
            
        return self.content

    def _render_token(self, token: str):
        """Render a single token with code-block awareness."""
        is_code = self._code_tracker.feed(token)

        if is_code:
            # Code block mode: dimmed, monospace feel
            if self._token_counter == 0:
                self._safe_write(f"\r{C.CLEAR_LINE}")
                self._safe_write(f"  {C.DIM}```{self._code_tracker.code_lang}{C.RESET}\n")
                self._safe_write(f"  {C.DIM}│{C.RESET} ")
            self._safe_write(f"{C.GOLD_DIM}{token}{C.RESET}")
        else:
            if self._code_tracker.code_lang and not is_code:
                # Just exited code block, print closing ```
                self._safe_write(f"\n  {C.DIM}```{C.RESET}\n")
                self._safe_write(f"  {C.GOLD}│{C.RESET} ")
                self._code_tracker.code_lang = ""
            elif self._token_counter == 0:
                self._safe_write(f"\r{C.CLEAR_LINE}")
                self._safe_write(f"  {C.GOLD}│{C.RESET} ")
            self._safe_write(token)

        
    def _render_stats_inline(self):
        """Render live streaming stats on a separate line."""
        elapsed = time.time() - self._start_time
        tps = self._token_counter / elapsed if elapsed > 0 else 0
        stats = f"\r{C.SAVE_CURSOR}{C.CLEAR_LINE}  {C.DIM}tokens: {self._token_counter} | {tps:.0f} tok/s | {elapsed:.1f}s{C.RESET}{C.RESTORE_CURSOR}"
        self._safe_write(stats)
        
    def _render_thinking_indicator(self):
        """Render a 'thinking' indicator at stream start for reasoning models."""
        self._safe_write(f"\r{C.CLEAR_LINE}")
        self._safe_write(f"  {C.BLUE}⟐{C.RESET} {C.DIM}reasoning...{C.RESET}\n")
        self._safe_write(f"  {C.DIM}│{C.RESET} ")
        
    def process_tool_result(self, name: str, result: str, duration: float,
                            success: bool = True) -> str:
        """Process and display a tool call result."""
        if self.spinner:
            self.spinner.complete_tool(name, success=success, result=str(result)[:200])

        formatted = format_tool_result(name, result, duration)
        self._safe_write(f"\r{C.CLEAR_LINE}{formatted}\n")
        
        self.tool_results.append({
            "name": name,
            "result": str(result)[:500],
            "duration": duration,
            "success": success,
        })
        return formatted

    def finalize(self):
        """Clean up after stream is complete."""
        if self.spinner:
            self.spinner.stop()
        if self.token_display:
            self.token_display.clear()

    @property
    def elapsed(self) -> float:
        return time.time() - self._start_time

    @property
    def last_error(self) -> Optional[str]:
        """Last error encountered during streaming."""
        return self._last_error

    @property
    def error_recovery_count(self) -> int:
        """Number of automatic retries performed."""
        return self._error_recovery_count

    @property
    def has_errors(self) -> bool:
        """True if any errors occurred during streaming."""
        return self.stats.error_count > 0

    def reset(self):
        """Reset handler state for a fresh streaming session."""
        self.content = ""
        self.tool_call_buffer = []
        self.tool_results = []
        self._stopped = False
        self._last_error = None
        self._error_recovery_count = 0
        self.stats = StreamStats()



def render_markdown(text: str) -> str:
    """Render simple markdown to ANSI-colored text."""
    import re
    # Bold: **text**
    text = re.sub(r'\*\*(.+?)\*\*', lambda m: '\x1b[1;33m' + m.group(1) + '\x1b[0m', text)
    # Italic: *text*  
    text = re.sub(r'\*(.+?)\*', lambda m: '\x1b[3;37m' + m.group(1) + '\x1b[0m', text)
    # Inline code: `text`
    text = re.sub(r'`([^`]+)`', lambda m: '\x1b[36m' + m.group(1) + '\x1b[0m', text)
    # Headers: # text
    text = re.sub(r'^#{1,3}\s+(.+)$', lambda m: '\x1b[1;33m' + m.group(1) + '\x1b[0m', text, flags=re.MULTILINE)
    # Lists: - text
    bullet = '\x1b[33m\xe2\x80\xa2\x1b[0m'
    text = re.sub(r'^-\s+(.+)$', lambda m: ' ' + bullet + ' ' + m.group(1), text, flags=re.MULTILINE)
    return text
