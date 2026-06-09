"""
LAAP — Agent Base Class
Production agent with rich golden dragon UI, streaming tool call loop,
file system, shell, git, and cognitive engines.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import uuid, time, logging, json, os, sys

from laap.llm.factory import LLMFactory
from laap.llm.provider import Message, ToolDef
from laap.memory.hierarchical import HierarchicalMemory
from laap.memory.manager import MemoryManager
from laap.memory.providers.builtin import BuiltinMemoryProvider
from laap.tools.tool_registry import ToolRegistry, Tool
from laap.cognition.awareness import AwarenessSystem
from laap.plugins.manager import PluginManager
from laap.ui.display import (
    C, get_spinner, format_response, format_tool_start, format_tool_result,
    format_error, format_divider, TokenDisplay, context_indicator,
)
from laap.ui.stream_handler import StreamHandler
import shutil

logger = logging.getLogger("laap.agent")


@dataclass
class AgentConfig:
    name: str = "LAAP-Agent"
    description: str = "A LAAP autonomous agent"
    llm_provider: str = ""
    llm_model: str = ""
    system_prompt: str = ""
    max_tool_rounds: int = 15
    tools_enabled: bool = True
    verbose: bool = True
    exploration_rate: float = 0.2
    learning_rate: float = 0.1
    show_tokens: bool = False


MAX_CONTEXT_ROUNDS = 20  # soft cap — beyond this, compress mid messages

class ToolCallLoop:
    """Streaming LLM tool call loop with rich golden dragon UI.

    Design:
      - Spinner animates while LLM is thinking
      - Tokens stream in real-time after first word
      - Tool calls shown with status icons (running/success/error)
      - Results displayed with duration + preview
      - Final response formatted with golden dragon styling
      - Automatic context compression via sliding window
    """

    def __init__(self, agent: "Agent", max_rounds: int = 15):
        self.agent = agent
        self.max_rounds = max_rounds
        self.round = 0
        self.messages: List[Message] = []
        self.final_response: Optional[str] = None
        self._compress_every = 10  # compress after every N rounds

    def _compress_messages(self):
        """Sliding-window context compression.

        Keeps:
          - System message (if present)
          - Last COMPRESS_KEEP messages
        Collapses everything in between into a single summary message.
        """
        COMPRESS_KEEP = 8
        if len(self.messages) <= MAX_CONTEXT_ROUNDS:
            return
        # Find system message index
        sys_idx = 0
        for i, m in enumerate(self.messages):
            if m.role == "system":
                sys_idx = i
                break
        # Keep: system + last COMPRESS_KEEP messages
        keep = [m for m in self.messages[max(sys_idx, 0):sys_idx+1]] if any(m.role == "system" for m in self.messages) else []
        keep_start = sys_idx + 1 if keep else 0
        tail = self.messages[-COMPRESS_KEEP:]
        mid = self.messages[keep_start:-COMPRESS_KEEP]
        if mid:
            summary = Message(role="system", content=f"[Context summary: {len(mid)} previous messages compressed. History truncated for efficiency.]")
            self.messages = keep + [summary] + tail
        else:
            self.messages = keep + tail
        logger.debug("Compressed: %d → %d messages", len(mid) + len(keep) + len(tail), len(self.messages))

    def run(self, user_input: str, system_prompt: str = "",
            tools: Optional[List[ToolDef]] = None,
            handler: Optional[StreamHandler] = None) -> str:
        if not self.agent.llm:
            # print(f"  {C.DIM}No LLM configured — use /config or set API key{C.RESET}")
            return ""

        self.messages = []
        if system_prompt:
            self.messages.append(Message.system(system_prompt))
        self.messages.append(Message.user(user_input))

        # Stream handler handles ALL UI output
        if handler is None:
            handler = StreamHandler(verbose=self.agent.config.verbose)

        while self.round < self.max_rounds:
            self.round += 1
            content_buf = ""
            tool_calls_result = None
            tool_calls_list = []

            # === Phase 1: LLM Streaming ===
            # Spinner + token streaming

            stream = self.agent.llm.chat_stream(self.messages, tools=tools)

            content_buf = handler.process_stream(stream, tools=tools)
            tool_calls_result = handler.tool_call_buffer if handler.tool_call_buffer else None

            response = Message(role="assistant", content=content_buf,
                              tool_calls=tool_calls_result)
            self.messages.append(response)

            if not response.tool_calls:
                self.final_response = response.content
                return response.content

            # === Phase 2: Tool Execution ===
            # Each tool call shown with spinner, result, timing

            for tc in response.tool_calls:
                func_name = tc["function"]["name"]
                try:
                    func_args = tc["function"]["arguments"]
                    args = json.loads(func_args) if isinstance(func_args, str) else func_args
                except Exception:
                    args = {}

                # Show tool start (skip ANSI when output is piped)
                if sys.stdout.isatty():
                    # print(f"\r{C.CLEAR_LINE}{format_tool_start(func_name, args)}")
                    get_spinner().add_tool(func_name, args)

                # Execute (with permission check + audit)
                if self.agent.config.tools_enabled:
                    from laap.permissions.enforcer import PermissionEnforcer, AccessLevel
                    from laap.utils.audit import get_audit_logger
                    perm = PermissionEnforcer()
                    audit = get_audit_logger()
                    access = perm.check(func_name, args)
                    if access == AccessLevel.DENY:
                        audit.log("permission", func_name, str(args.get("path", "")),
                                  result="denied", details={"reason": "Permission denied"})
                        result = json.dumps({"error": f"Permission denied: {func_name}", "status": "denied"})
                        continue
                    audit.log("tool_exec", func_name, str(args.get("path", "")),
                              result="allowed", details={"args": str(args)[:100]})
                    from laap.permissions.enforcer import enforcer as perm_enforcer
                    # Map tool names to permission resource strings
                    perm_resource = {
                        "run_command": "shell:execute",
                        "run_python": "code:execute",
                        "run_script": "shell:execute",
                        "write_file": "file:write",
                        "edit_file": "file:write",
                        "create_file": "file:write",
                        "delete_file": "file:delete",
                        "git_commit": "git:commit",
                        "git_push": "git:push",
                        "git_branch": "git:commit",
                        "web_fetch": "network:connect",
                        "web_search": "network:connect",
                    }.get(func_name, "code:execute")

                    permitted = perm_enforcer.check(perm_resource, f"Tool: {func_name}")
                    if not permitted:
                        tool_result = json.dumps({"error": f"Permission denied: {func_name}"})
                        # print(f"\r{C.CLEAR_LINE}  {C.RED}✗{C.RESET} {C.DIM}{func_name} blocked (permission){C.RESET}")
                        duration = 0.0
                    else:
                        t0 = time.time()
                        tool_result = self.agent.call_tool(func_name, **args)
                        duration = time.time() - t0
                else:
                    t0 = time.time()
                    tool_result = self.agent.call_tool(func_name, **args)
                    duration = time.time() - t0

                # Show result
                handler.process_tool_result(func_name, tool_result, duration,
                                            success=True)

                self.messages.append(Message.tool_result(
                    content=str(tool_result)[:100000],
                    tool_call_id=tc["id"],
                    name=func_name,
                ))

                if self.agent.awareness:
                    self.agent.awareness.record_event("tool_call", {"tool": func_name})

            # Periodic context compression
            if self._compress_every and self.round % self._compress_every == 0:
                self._compress_messages()

        # Finalize
        handler.finalize()

        # Auto-save session messages if session manager is configured
        if self.agent.session_manager and self.messages:
            sid = self.agent._current_session_id or self.agent.id
            msg_dicts = [m.to_dict() for m in self.messages]
            try:
                self.agent.session_manager.save_messages(sid, msg_dicts)
                logger.debug(f"Auto-saved {len(msg_dicts)} messages to session {sid}")
            except Exception:
                pass

        return self.final_response or "Max rounds reached"

    async def arun(self, user_input: str, system_prompt: str = "",
                   tools: Optional[List[ToolDef]] = None) -> str:
        if not self.agent.llm:
            return "(no LLM available)"
        self.messages = []
        if system_prompt:
            self.messages.append(Message.system(system_prompt))
        self.messages.append(Message.user(user_input))

        handler = StreamHandler(verbose=self.agent.config.verbose)

        while self.round < self.max_rounds:
            self.round += 1
            content_buf = ""
            tool_calls_list = []

            stream = self.agent.llm.chat_stream(self.messages, tools=tools)
            content_buf = handler.process_stream(stream, tools=tools)
            tool_calls = handler.tool_call_buffer if handler.tool_call_buffer else None

            response = Message(role="assistant", content=content_buf, tool_calls=tool_calls)
            self.messages.append(response)

            if not response.tool_calls:
                self.final_response = response.content
                return response.content

            for tc in response.tool_calls:
                func_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except Exception:
                    args = {}
                t0 = time.time()
                if self.agent.config.tools_enabled:
                    from laap.permissions.enforcer import enforcer as perm_enforcer
                    perm_resource = {
                        "run_command": "shell:execute", "run_python": "code:execute",
                        "run_script": "shell:execute", "write_file": "file:write",
                        "edit_file": "file:write", "create_file": "file:write",
                        "delete_file": "file:delete", "git_commit": "git:commit",
                        "git_push": "git:push", "git_branch": "git:commit",
                        "web_fetch": "network:connect", "web_search": "network:connect",
                    }.get(func_name, "code:execute")
                    if not perm_enforcer.check(perm_resource, f"Tool: {func_name}"):
                        tool_result = json.dumps({"error": f"Permission denied: {func_name}"})
                    else:
                        tool_result = self.agent.call_tool(func_name, **args)
                else:
                    tool_result = self.agent.call_tool(func_name, **args)
                duration = time.time() - t0
                handler.process_tool_result(func_name, tool_result, duration)

                self.messages.append(Message.tool_result(
                    content=str(tool_result)[:100000],
                    tool_call_id=tc["id"], name=func_name,
                ))

        handler.finalize()

        # Auto-save session messages
        if self.agent.session_manager and self.messages:
            sid = self.agent._current_session_id or self.agent.id
            try:
                self.agent.session_manager.save_messages(sid, [m.to_dict() for m in self.messages])
            except Exception:
                pass

        return self.final_response or "Max rounds reached"


class Agent:
    """LAAP Agent base class with production capabilities and golden dragon UI."""

    def __init__(self, config: Optional[AgentConfig] = None,
                 llm_factory: Optional[LLMFactory] = None,
                 session_manager: Optional["SessionManager"] = None,
                 show_banner: Optional[bool] = None):
        self.id = str(uuid.uuid4())[:12]
        self.config = config or AgentConfig()
        self.alive = True
        self.step_count = 0
        self.birth_time = time.time()
        self._self_modifications = 0
        self._show_banner = self.config.verbose if show_banner is None else show_banner

        # Session persistence (optional)
        self.session_manager = session_manager
        self._current_session_id: Optional[str] = None

        # Tools
        self.tool_registry = ToolRegistry()

        # Legacy memory (hierarchical, in-memory)
        self.memory = HierarchicalMemory()
        self.memory.load()

        # Persistent memory system
        self.memory_manager = MemoryManager()
        try:
            builtin = BuiltinMemoryProvider()
            self.memory_manager.add_provider(builtin)
            self.memory_manager.initialize_all(
                session_id=self._current_session_id or self.id,
            )
            logger.info("Persistent memory initialized")
        except Exception as e:
            logger.warning(f"Persistent memory init failed: {e}")
            # MemoryManager without providers is still usable

        # Awareness
        self.awareness = AwarenessSystem(agent_id=self.id, name=self.config.name)

        # Plugin system
        self.plugins = PluginManager()

        # Register production tools (guarded against double init)
        self._init_tools()
        self.plugins.trigger("agent:ready", agent=self)

        # LLM
        self.llm_factory = llm_factory or LLMFactory()
        try:
            self.llm = self.llm_factory.get(
                name=self.config.llm_provider or None,
                model=self.config.llm_model or None,
            )
        except Exception:
            self.llm = None
            if self.config.verbose:
                logger.info(f"Agent [{self.id[:8]}] local-only mode")

        # Auto-restore previous session if available
        self._safe_load_session()

        if self._show_banner:
            # Banner output removed (use logger)
            logger.info(f"{C.GOLD}◆{C.RESET} {self.config.name} [{self.id[:8]}] {self.tool_registry.count} tools ready")

    def _init_default_tools(self):
        if getattr(self, '_default_tools_registered', False):
            return
        self._default_tools_registered = True
        # run_python 已由 shell 模块注册（更完善的 ShellExecutor 版本）
        self.register_tool("apply_modification", self.apply_modification_tool,
                          "Apply config modification to self", stop_after=True)

    def _safe_load_session(self):
        """Auto-load latest saved session on startup, if session_manager configured."""
        if not self.session_manager:
            return
        try:
            states = self.session_manager.list_agent_states()
            if states:
                latest = states[-1]
                self.session_manager.load_agent_state(latest, self)
                self._current_session_id = latest
                if self.config.verbose:
                    logger.info(f"恢复会话: {latest}")
        except Exception:
            pass

    def _auto_save(self):
        """Auto-save current state and memory if session_manager configured."""
        self.plugins.trigger("agent:auto_save", agent=self)
        if self.session_manager:
            sid = self._current_session_id or self.id
            try:
                self.session_manager.save_agent_state(sid, self)
            except Exception:
                pass
        self.memory.save()

    def _init_tools(self):
        """Initialize all tools — guarded so subclasses calling super().__init__ don't re-register."""
        if getattr(self, '_tools_initialized', False):
            return
        self._tools_initialized = True
        self._init_default_tools()
        if self.config.tools_enabled:
            from laap.tools.code_edit import register_all as _register_code_tools
            from laap.tools.shell import register_all as _register_shell_tools
            from laap.tools.web import register_all as _register_web_tools
            _register_code_tools(self.tool_registry)
            _register_shell_tools(self.tool_registry)
            _register_web_tools(self.tool_registry)

    def register_tool(self, name: str, handler: Callable, description: str = "",
                      category: str = "custom", stop_after: bool = False):
        from laap.tools.base import infer_json_schema
        from inspect import signature, getdoc
        sig = signature(handler)
        hints = {}
        for pname, p in sig.parameters.items():
            if pname not in ("self", "cls", "agent", "fc"):
                hints[pname] = p.annotation if p.annotation != p.empty else str
        param_descriptions = {}
        doc = getdoc(handler)
        if doc:
            from docstring_parser import parse as doc_parse
            for p in (doc_parse(doc).params or []):
                param_descriptions[p.arg_name] = p.description or ""
        schema = infer_json_schema(hints, param_descriptions)
        tool = Tool(name=name, description=description,
                    parameters={"type": "object", "properties": schema["properties"],
                                "required": schema.get("required", [])},
                    handler=handler, category=category)
        self.tool_registry.register(tool)
        self.memory.register_skill(name, description)

    def call_tool(self, tool_name: str, **kwargs) -> Any:
        try:
            result = self.tool_registry.call(tool_name, **kwargs)
            self.memory.record_skill_result(tool_name, True)
            return result
        except Exception as e:
            self.memory.record_skill_result(tool_name, False)
            return json.dumps({"error": f"{type(e).__name__}: {str(e)[:200]}"})

    def get_tool_defs(self) -> List[ToolDef]:
        return [t.to_tool_def() for t in self.tool_registry.list() if t.handler]

    def chat(self, message: str, system_prompt: str = "",
             tools: Optional[List[ToolDef]] = None,
             max_rounds: Optional[int] = None,
             handler: Optional[StreamHandler] = None) -> str:
        if not self.alive: return "Agent is not alive."
        self.step_count += 1
        if self.awareness:
            self.awareness.record_event("chat", {"message": message[:60]})
        self.plugins.trigger("agent:will_chat", agent=self, message=message)

        # Inject relevant memories into system prompt
        memory_context = self.memory_manager.prefetch_all(
            message, session_id=self._current_session_id or self.id,
        )
        enhanced_prompt = system_prompt or self.config.system_prompt
        if memory_context:
            enhanced_prompt = enhanced_prompt + "\n\n" + memory_context

        # Start turn in memory manager
        self.memory_manager.on_turn_start(self.step_count, message)

        # Merge memory tool schemas into available tools
        memory_tools = self.memory_manager.get_all_tool_schemas()
        all_tools = (tools or self.get_tool_defs()) + memory_tools

        loop = ToolCallLoop(self, max_rounds=max_rounds or self.config.max_tool_rounds)
        result = loop.run(user_input=message,
                          system_prompt=enhanced_prompt,
                          tools=all_tools,
                          handler=handler)

        # Sync turn to memory
        self.memory_manager.sync_all(
            message, result or "",
            session_id=self._current_session_id or self.id,
        )

        self.plugins.trigger("agent:did_chat", agent=self, result=result)
        self._auto_save()
        return result

    def run(self, task: str) -> str:
        self.step_count += 1
        if self.awareness:
            self.awareness.set_task(task)
        return self.chat(task)

    # ── Session Persistence ─────────────────────────────────

    def save_session(self, session_id: Optional[str] = None) -> bool:
        """Persist current agent state and conversation to session storage.

        Args:
            session_id: Optional session ID (defaults to agent ID)

        Returns:
            True if saved successfully
        """
        if not self.session_manager:
            return False
        sid = session_id or self._current_session_id or self.id
        try:
            self.session_manager.save_agent_state(sid, self)
            self._current_session_id = sid
            return True
        except Exception as e:
            logger.warning(f"Session save failed: {e}")
            return False

    def load_session(self, session_id: str) -> bool:
        """Restore agent state from a saved session.

        Args:
            session_id: Session identifier to restore

        Returns:
            True if loaded successfully
        """
        if not self.session_manager:
            return False
        try:
            ok = self.session_manager.load_agent_state(session_id, self)
            if ok:
                self._current_session_id = session_id
            return ok
        except Exception as e:
            logger.warning(f"Session load failed: {e}")
            return False

    def apply_modification(self, modification: Dict[str, Any]) -> bool:
        mod_type = modification.get("type")
        params = modification.get("params", {})
        try:
            if mod_type == "adjust_exploration":
                self.config.exploration_rate = max(0.01, min(0.99, params.get("value", 0.2)))
            elif mod_type == "adjust_learning_rate":
                self.config.learning_rate = max(0.001, min(0.5, params.get("value", 0.1)))
            else:
                logger.warning(f"Unknown mod type: {mod_type}")
                return False
            self._self_modifications += 1
            return True
        except Exception as e:
            logger.error(f"Modification failed: {e}")
            return False

    def apply_modification_tool(self, mod_type: str = "", params: str = "{}") -> str:
        if not mod_type: return "No modification type specified"
        try:
            p = json.loads(params) if isinstance(params, str) else params
            success = self.apply_modification({"type": mod_type, "params": p})
            return f"Modification {'succeeded' if success else 'failed'}"
        except Exception as e: return f"Error: {e}"

    def die(self, reason: str = "unknown"):
        self.alive = False
        self.plugins.trigger("agent:die", agent=self, reason=reason)
        logger.warning(f"Agent [{self.id[:8]}] died: {reason}")
        if self.awareness: self.awareness.record_event("death", {"reason": reason})

    @property
    def age(self) -> float: return time.time() - self.birth_time

    def status(self) -> dict:
        return {"id": self.id, "name": self.config.name, "alive": self.alive,
                "steps": self.step_count, "age_s": round(self.age, 1),
                "self_modifications": self._self_modifications,
                "tools": self.tool_registry.count, "memory": self.memory.to_dict(),
                "awareness": self.awareness.summary() if self.awareness else {}}
