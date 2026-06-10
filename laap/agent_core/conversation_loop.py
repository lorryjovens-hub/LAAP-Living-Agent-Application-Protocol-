"""ConversationLoop"""

from __future__ import annotations
import time
import json
import logging
import copy
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, Generator, AsyncGenerator

logger = logging.getLogger("agent_core.conversation_loop")


class TurnState(str, Enum):
    STARTED = "started"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    OBSERVING = "observing"
    REASONING = "reasoning"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class LoopEvent(str, Enum):
    TURN_START = "turn_start"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    OBSERVING = "observing"
    REASONING = "reasoning"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ERROR = "error"
    RETRY = "retry"
    DEGRADE = "degrade"
    TRUNCATE = "truncate"
    COMPRESS = "compress"


@dataclass
class ToolCallRecord:
    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    retries: int = 0
    success: bool = True
    tokens_used: int = 0

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": str(self.result)[:200] if self.result else "",
            "error": self.error[:200] if self.error else "",
            "duration_ms": round(self.duration_ms, 2),
            "retries": self.retries,
            "success": self.success,
            "tokens_used": self.tokens_used,
        }


@dataclass
class TurnTrajectory:
    step_index: int = 0
    thought: str = ""
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    reasoning: str = ""
    final_answer: str = ""

    def to_dict(self) -> dict:
        return {
            "step_index": self.step_index,
            "thought": self.thought[:200],
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "observations": [o[:200] for o in self.observations],
            "reasoning": self.reasoning[:200],
            "final_answer": self.final_answer[:200],
        }


@dataclass
class TurnRecord:
    turn_id: int = 0
    user_message: str = ""
    assistant_response: str = ""
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    trajectories: List[TurnTrajectory] = field(default_factory=list)
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_ms: float = 0.0
    thinking_ms: float = 0.0
    tool_ms: float = 0.0
    state: TurnState = TurnState.STARTED
    error: str = ""
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    retry_count: int = 0
    degraded: bool = False
    interrupted: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "turn_id": self.turn_id,
            "state": self.state.value,
            "duration_ms": round(self.duration_ms, 2),
            "tokens_used": self.tokens_used,
            "tool_calls": len(self.tool_calls),
            "trajectory_steps": len(self.trajectories),
            "error": self.error[:100] if self.error else "",
            "retry_count": self.retry_count,
            "degraded": self.degraded,
            "interrupted": self.interrupted,
        }

    @property
    def elapsed_ms(self) -> float:
        if self.completed_at and self.created_at:
            return (self.completed_at - self.created_at) * 1000
        return (time.time() - self.created_at) * 1000


@dataclass
class TokenBudget:
    max_context_tokens: int = 128000
    max_response_tokens: int = 4096
    max_tool_output_tokens: int = 4000
    reserve_tokens: int = 2000
    compression_threshold: float = 0.75
    warning_threshold: float = 0.85
    critical_threshold: float = 0.95

    @property
    def effective_max(self) -> int:
        return self.max_context_tokens - self.reserve_tokens

    def usage_ratio(self, current_tokens: int) -> float:
        return current_tokens / self.max_context_tokens

    def is_warning(self, current_tokens: int) -> bool:
        return self.usage_ratio(current_tokens) >= self.warning_threshold

    def is_critical(self, current_tokens: int) -> bool:
        return self.usage_ratio(current_tokens) >= self.critical_threshold

    def should_compress(self, current_tokens: int) -> bool:
        return self.usage_ratio(current_tokens) >= self.compression_threshold

    def available_for_response(self, current_tokens: int) -> int:
        remaining = self.max_context_tokens - current_tokens - self.reserve_tokens
        return max(0, min(remaining, self.max_response_tokens))

    def to_dict(self) -> dict:
        return {
            "max_context_tokens": self.max_context_tokens,
            "max_response_tokens": self.max_response_tokens,
            "compression_threshold": self.compression_threshold,
            "reserve_tokens": self.reserve_tokens,
        }


@dataclass
class PerformanceStats:
    total_turns: int = 0
    completed_turns: int = 0
    failed_turns: int = 0
    cancelled_turns: int = 0
    retried_turns: int = 0
    degraded_turns: int = 0
    total_tokens: int = 0
    total_tool_calls: int = 0
    total_duration_ms: float = 0.0
    total_thinking_ms: float = 0.0
    total_tool_ms: float = 0.0
    max_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    start_time: float = field(default_factory=time.time)
    errors_by_type: Dict[str, int] = field(default_factory=dict)

    def record_turn(self, turn: TurnRecord):
        self.total_turns += 1
        if turn.state == TurnState.COMPLETED:
            self.completed_turns += 1
        elif turn.state == TurnState.FAILED:
            self.failed_turns += 1
        elif turn.state in (TurnState.CANCELLED, TurnState.TIMEOUT):
            self.cancelled_turns += 1
        if turn.retry_count > 0:
            self.retried_turns += 1
        if turn.degraded:
            self.degraded_turns += 1
        self.total_tokens += turn.tokens_used
        self.total_tool_calls += len(turn.tool_calls)
        d = turn.duration_ms
        self.total_duration_ms += d
        self.total_thinking_ms += turn.thinking_ms
        self.total_tool_ms += turn.tool_ms
        self.max_duration_ms = max(self.max_duration_ms, d)
        if d > 0:
            self.min_duration_ms = min(self.min_duration_ms, d)
        if turn.error:
            err_type = turn.error.split(":")[0]
            self.errors_by_type[err_type] = self.errors_by_type.get(err_type, 0) + 1

    def avg_duration_ms(self) -> float:
        return round(self.total_duration_ms / max(self.total_turns, 1), 2)

    def success_rate(self) -> float:
        return round(self.completed_turns / max(self.total_turns, 1) * 100, 2)

    def to_dict(self) -> dict:
        return {
            "total_turns": self.total_turns,
            "completed_turns": self.completed_turns,
            "failed_turns": self.failed_turns,
            "cancelled_turns": self.cancelled_turns,
            "retried_turns": self.retried_turns,
            "degraded_turns": self.degraded_turns,
            "success_rate": self.success_rate(),
            "total_tokens": self.total_tokens,
            "total_tool_calls": self.total_tool_calls,
            "avg_duration_ms": self.avg_duration_ms(),
            "max_duration_ms": round(self.max_duration_ms, 2),
            "min_duration_ms": round(self.min_duration_ms if self.min_duration_ms != float('inf') else 0, 2),
            "total_duration_s": round(self.total_duration_ms / 1000, 2),
            "uptime_s": round(time.time() - self.start_time, 2),
            "errors_by_type": self.errors_by_type,
        }


class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._async_handlers: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable):
        self._handlers.setdefault(event, []).append(callback)

    def on_async(self, event: str, callback: Callable):
        self._async_handlers.setdefault(event, []).append(callback)

    def off(self, event: str, callback: Optional[Callable] = None):
        if callback is None:
            self._handlers.pop(event, None)
            self._async_handlers.pop(event, None)
        else:
            lst = self._handlers.get(event, [])
            if callback in lst:
                lst.remove(callback)
            lst2 = self._async_handlers.get(event, [])
            if callback in lst2:
                lst2.remove(callback)

    def emit(self, event: str, data: Any = None):
        for cb in self._handlers.get(event, []):
            try:
                cb(data)
            except Exception as e:
                logger.error(f"EventHandler error [{event}]: {e}")

    async def emit_async(self, event: str, data: Any = None):
        for cb in self._async_handlers.get(event, []):
            try:
                await cb(data)
            except Exception as e:
                logger.error(f"AsyncEventHandler error [{event}]: {e}")
        self.emit(event, data)

    def clear(self):
        self._handlers.clear()
        self._async_handlers.clear()


@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_delay_ms: float = 1000.0
    max_delay_ms: float = 30000.0
    backoff_factor: float = 2.0
    retry_on_timeout: bool = True
    retry_on_rate_limit: bool = True
    retry_on_server_error: bool = True
    degrade_on_failure: bool = True

    def get_delay(self, attempt: int) -> float:
        delay = self.base_delay_ms * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay_ms)

    def should_retry(self, attempt: int, error: str) -> bool:
        if attempt >= self.max_retries:
            return False
        err_lower = error.lower()
        if "timeout" in err_lower or "timed out" in err_lower:
            return self.retry_on_timeout
        if "rate" in err_lower or "429" in err_lower or "too many" in err_lower:
            return self.retry_on_rate_limit
        if "500" in err_lower or "503" in err_lower:
            return self.retry_on_server_error
        return True

    def to_dict(self) -> dict:
        return {
            "max_retries": self.max_retries,
            "base_delay_ms": self.base_delay_ms,
            "backoff_factor": self.backoff_factor,
            "degrade_on_failure": self.degrade_on_failure,
        }


class InterruptSignal:
    def __init__(self):
        self._cancelled = False
        self._reason: Optional[str] = None

    def cancel(self, reason: str = "user_interrupt"):
        self._cancelled = True
        self._reason = reason

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def reason(self) -> Optional[str]:
        return self._reason

    def reset(self):
        self._cancelled = False
        self._reason = None


class ConversationLoop:
    def __init__(
        self,
        agent: Optional[Any] = None,
        token_budget: Optional[TokenBudget] = None,
        retry_policy: Optional[RetryPolicy] = None,
        max_turns: int = 50,
        max_react_steps: int = 10,
        enable_trajectory: bool = True,
        enable_stats: bool = True,
    ):
        self.agent = agent
        self.token_budget = token_budget or TokenBudget()
        self.retry_policy = retry_policy or RetryPolicy()
        self.max_turns = max_turns
        self.max_react_steps = max_react_steps
        self.enable_trajectory = enable_trajectory
        self.history: List[TurnRecord] = []
        self._current_turn: Optional[TurnRecord] = None
        self._interrupt = InterruptSignal()
        self._events = EventBus()
        self._stats = PerformanceStats() if enable_stats else None
        logger.info(f"ConversationLoop ready (max_turns={max_turns}, react_steps={max_react_steps})")

    def on(self, event: str, callback: Callable):
        self._events.on(event, callback)

    def on_async(self, event: str, callback: Callable):
        self._events.on_async(event, callback)

    def off(self, event: str, callback: Optional[Callable] = None):
        self._events.off(event, callback)

    def _emit(self, event: str, data: Any = None):
        self._events.emit(event, data)

    def cancel(self, reason: str = "user_interrupt"):
        self._interrupt.cancel(reason)

    def reset_interrupt(self):
        self._interrupt.reset()

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(text) // 2 + len(text.split())

    def check_token_budget(self, current_tokens: int) -> Dict[str, Any]:
        result = {"ok": True, "action": None, "message": ""}
        if self.token_budget.is_critical(current_tokens):
            result["ok"] = False
            result["action"] = "truncate"
            result["message"] = f"Token usage critical: {current_tokens}/{self.token_budget.max_context_tokens}"
            self._emit(LoopEvent.TRUNCATE, result)
        elif self.token_budget.is_warning(current_tokens):
            result["action"] = "compress"
            result["message"] = f"Token usage warning: {current_tokens}/{self.token_budget.max_context_tokens}"
            self._emit(LoopEvent.COMPRESS, result)
        elif self.token_budget.should_compress(current_tokens):
            result["action"] = "compress_mild"
            result["message"] = f"Token usage above threshold: {current_tokens}/{self.token_budget.max_context_tokens}"
        return result

    def _create_turn(self, user_message: str) -> TurnRecord:
        turn_id = len(self.history) + 1
        turn = TurnRecord(turn_id=turn_id, user_message=user_message)
        self._current_turn = turn
        self._emit(LoopEvent.TURN_START, turn)
        return turn

    def _complete_turn(self, turn: TurnRecord, response: str):
        turn.assistant_response = response
        turn.completed_at = time.time()
        turn.duration_ms = round((turn.completed_at - turn.created_at) * 1000, 2)
        turn.state = TurnState.COMPLETED
        self.history.append(turn)
        if self._stats:
            self._stats.record_turn(turn)
        self._emit(LoopEvent.COMPLETED, turn)
        self._current_turn = None

    def _fail_turn(self, turn: TurnRecord, error: str, state: TurnState = TurnState.FAILED):
        turn.error = error
        turn.completed_at = time.time()
        turn.duration_ms = round((turn.completed_at - turn.created_at) * 1000, 2)
        turn.state = state
        self.history.append(turn)
        if self._stats:
            self._stats.record_turn(turn)
        self._emit(LoopEvent.FAILED, turn)
        self._current_turn = None

    def process(self, user_message: str) -> str:
        turn = self._create_turn(user_message)

        for react_step in range(self.max_react_steps):
            if self._interrupt.cancelled:
                turn.interrupted = True
                self._fail_turn(turn, f"Cancelled: {self._interrupt.reason}", TurnState.CANCELLED)
                return "[对话被中断]"

            current_tokens = self.agent.context.total_tokens() if hasattr(self.agent, 'context') else 0
            budget_check = self.check_token_budget(current_tokens)
            if budget_check.get("action") == "truncate" and hasattr(self.agent, 'compressor'):
                self._emit(LoopEvent.TRUNCATE, {"tokens": current_tokens})
                compressed = self.agent.compressor.compress(self.agent.context.get_messages())
                if hasattr(self.agent.context, 'messages'):
                    self.agent.context.messages = compressed
                self._emit(LoopEvent.COMPRESS, {"compressed": True, "before": len(self.agent.context.messages) if hasattr(self.agent.context, 'messages') else 0, "after": len(compressed)})

            turn.state = TurnState.THINKING
            think_start = time.time()
            self._emit(LoopEvent.THINKING, {"step": react_step})

            trajectory = TurnTrajectory(step_index=react_step) if self.enable_trajectory else None

            try:
                response = None
                for attempt in range(self.retry_policy.max_retries + 1):
                    try:
                        messages = self.agent.context.get_messages() if hasattr(self.agent, 'context') else []
                        tools = []
                        if hasattr(self.agent, 'tool_mgr') and hasattr(self.agent, 'config') and hasattr(self.agent.config, 'enable_tools') and self.agent.config.enable_tools:
                            tools = self.agent.tool_mgr.get_openai_tools() if hasattr(self.agent.tool_mgr, 'get_openai_tools') else []
                        response = self.agent.llm.chat(
                            messages,
                            tools=tools,
                            max_tokens=self.token_budget.available_for_response(current_tokens),
                        )
                        break
                    except Exception as e:
                        err_str = str(e)
                        if self.retry_policy.should_retry(attempt, err_str):
                            delay = self.retry_policy.get_delay(attempt) / 1000.0
                            logger.warning(f"Retry {attempt+1}/{self.retry_policy.max_retries}: {err_str}")
                            self._emit(LoopEvent.RETRY, {"attempt": attempt+1, "error": err_str, "delay": delay})
                            time.sleep(delay)
                            turn.retry_count += 1
                        else:
                            if self.retry_policy.degrade_on_failure:
                                turn.degraded = True
                                self._emit(LoopEvent.DEGRADE, {"reason": err_str})
                                messages = self.agent.context.get_messages() if hasattr(self.agent, 'context') else []
                                try:
                                    response = self.agent.llm.chat(messages, tools=[])
                                    if response and getattr(response, 'content', None):
                                        break
                                except Exception:
                                    pass
                            raise

                if response is None:
                    raise RuntimeError("LLM returned no response after retries")

                turn.thinking_ms += (time.time() - think_start) * 1000

                finish_reason = getattr(response, 'finish_reason', '') or ''
                if not getattr(response, 'content', None) and finish_reason == "tool_calls":
                    turn.state = TurnState.TOOL_CALL
                    tool_start = time.time()

                    exec_result = None
                    if hasattr(self.agent, '_execute_tool_call'):
                        try:
                            exec_result = self.agent._execute_tool_call(user_message if react_step == 0 else "")
                        except Exception as e:
                            logger.warning(f"Tool exec error: {e}")
                    elif hasattr(self.agent, '_exec_tool'):
                        try:
                            exec_result = self.agent._exec_tool(user_message if react_step == 0 else "")
                        except Exception as e:
                            logger.warning(f"Tool exec error: {e}")

                    tool_record = ToolCallRecord(
                        tool_name=getattr(exec_result, 'tool_name', 'unknown') if exec_result else 'think',
                        arguments={"input": user_message[:200]},
                        start_time=tool_start,
                    )
                    self._emit(LoopEvent.TOOL_CALL, tool_record)

                    obs_text = ""
                    if exec_result:
                        obs_text = getattr(exec_result, 'output', None) or str(getattr(exec_result, 'data', "") or "")
                        tool_record.result = obs_text[:500]
                        tool_record.success = True
                    else:
                        obs_text = "工具调用未返回结果"
                        tool_record.error = obs_text
                        tool_record.success = False

                    turn.tool_calls.append(tool_record)
                    if trajectory:
                        trajectory.tool_calls.append(tool_record)
                        trajectory.observations.append(obs_text[:500])

                    turn.state = TurnState.OBSERVING
                    self._emit(LoopEvent.OBSERVING, {"output": obs_text[:200]})

                    if hasattr(self.agent, 'context'):
                        self.agent.context.add(
                            "tool",
                            obs_text[:self.token_budget.max_tool_output_tokens],
                            tool_call_id="call_1",
                            name="tool"
                        )

                    tool_record.end_time = time.time()
                    tool_record.duration_ms = round((tool_record.end_time - tool_record.start_time) * 1000, 2)
                    turn.tool_ms += tool_record.duration_ms

                    turn.state = TurnState.REASONING
                    if trajectory:
                        trajectory.reasoning = "Integrating tool results"
                    self._emit(LoopEvent.REASONING, {"step": react_step})
                    continue

                else:
                    turn.state = TurnState.COMPLETED
                    if trajectory:
                        trajectory.final_answer = (getattr(response, 'content', None) or "")[:500]
                        turn.trajectories.append(trajectory)

                    content = getattr(response, 'content', None) or ""
                    if hasattr(self.agent, 'context'):
                        self.agent.context.add("assistant", content)
                    if hasattr(self.agent, 'memory') and self.agent.memory:
                        try:
                            self.agent.memory.remember_interaction(user_message, content)
                        except Exception as e:
                            logger.warning(f"Memory save error: {e}")

                    usage = getattr(response, 'usage', {}) or {}
                    turn.tokens_used = usage.get('total_tokens', 0) or 0
                    turn.prompt_tokens = usage.get('prompt_tokens', 0) or 0
                    turn.completion_tokens = usage.get('completion_tokens', 0) or 0

                    self._complete_turn(turn, content)
                    return content

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                logger.error(f"ReAct step {react_step} error: {error_msg}")
                self._emit(LoopEvent.ERROR, {"step": react_step, "error": error_msg})
                if react_step < self.max_react_steps - 1:
                    if hasattr(self.agent, 'context'):
                        self.agent.context.add("assistant", f"[Step {react_step} error, retrying...]")
                    turn.degraded = True
                    self._emit(LoopEvent.DEGRADE, {"reason": error_msg})
                    continue
                else:
                    self._fail_turn(turn, error_msg)
                    return f"[错误: {error_msg}]"

        self._fail_turn(turn, f"Exceeded max ReAct steps ({self.max_react_steps})", TurnState.TIMEOUT)
        return "[已达最大执行步骤]"

    def stream_process(self, user_message: str) -> Generator[Tuple[str, Any], None, None]:
        turn = self._create_turn(user_message)
        yield ("turn_start", turn.turn_id)
        full_response = ""
        try:
            if hasattr(self.agent, 'stream_chat'):
                for token_data in self.agent.stream_chat(user_message):
                    if self._interrupt.cancelled:
                        yield ("cancelled", self._interrupt.reason)
                        turn.interrupted = True
                        self._fail_turn(turn, f"Cancelled: {self._interrupt.reason}", TurnState.CANCELLED)
                        return
                    if token_data[0] == "token":
                        full_response += token_data[1]
                        yield ("token", token_data[1])
                    elif token_data[0] == "error":
                        yield ("error", token_data[1])
                        self._fail_turn(turn, token_data[1])
                        return
                    elif token_data[0] == "done":
                        yield ("done", full_response)
                        self._complete_turn(turn, full_response)
                        return
            else:
                resp = self.process(user_message)
                for i in range(0, len(resp), 10):
                    yield ("token", resp[i:i+10])
                yield ("done", resp)
        except Exception as e:
            err = str(e)
            yield ("error", err)
            self._fail_turn(turn, err)

    def get_stats(self) -> dict:
        if self._stats:
            return self._stats.to_dict()
        completed = sum(1 for t in self.history if t.state == TurnState.COMPLETED)
        failed = sum(1 for t in self.history if t.state == TurnState.FAILED)
        cancelled = sum(1 for t in self.history if t.state in (TurnState.CANCELLED, TurnState.TIMEOUT))
        return {
            "total_turns": len(self.history),
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "avg_duration_ms": round(sum(t.duration_ms for t in self.history) / max(len(self.history), 1), 2),
            "total_tokens": sum(t.tokens_used for t in self.history),
            "total_tool_calls": sum(len(t.tool_calls) for t in self.history),
        }

    def get_history(self, limit: int = 10, offset: int = 0) -> List[dict]:
        return [t.to_dict() for t in self.history[-limit-offset:len(self.history)-offset] if t.turn_id > 0]

    def get_turn(self, turn_id: int) -> Optional[dict]:
        for t in self.history:
            if t.turn_id == turn_id:
                return t.to_dict()
        return None

    def get_trajectory(self, turn_id: int) -> List[dict]:
        for t in self.history:
            if t.turn_id == turn_id:
                return [tr.to_dict() for tr in t.trajectories]
        return []

    def get_token_budget_info(self) -> dict:
        current = sum(t.tokens_used for t in self.history)
        return {
            **self.token_budget.to_dict(),
            "current_tokens": current,
            "usage_ratio": round(current / self.token_budget.max_context_tokens * 100, 2),
            "available": self.token_budget.available_for_response(current),
        }

    @property
    def is_running(self) -> bool:
        return self._interrupt.cancelled is False and self._current_turn is not None

    @property
    def current_turn(self) -> Optional[TurnRecord]:
        return self._current_turn

    def reset(self):
        self.history.clear()
        self._current_turn = None
        self._interrupt.reset()
        if self._stats:
            self._stats = PerformanceStats()

    def to_dict(self) -> dict:
        return {
            "history_length": len(self.history),
            "max_turns": self.max_turns,
            "max_react_steps": self.max_react_steps,
            "token_budget": self.token_budget.to_dict(),
            "retry_policy": self.retry_policy.to_dict(),
            "stats": self.get_stats(),
            "is_running": self.is_running,
        }
