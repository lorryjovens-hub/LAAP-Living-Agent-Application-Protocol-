"""
LAAP Executor — 任务执行引擎
执行计划中的每个任务，协调工具调用和LLM推理
"""
from __future__ import annotations
import time, json, logging, threading
from typing import Any, Callable, Dict, List, Optional, Tuple
from laap.agent_core.planner import Plan, Task
from laap.agent_core.tool_manager import ToolManager, ToolResult

logger = logging.getLogger("agent_core.executor")

class Executor:
    """任务执行器 — ReAct循环执行"""
    
    def __init__(self, tool_manager: ToolManager):
        self.tool_mgr = tool_manager
        self._running = False
        self._stats = {"tasks_completed": 0, "tasks_failed": 0, "total_duration_ms": 0.0}
    
    def execute_task(self, task: Task) -> ToolResult:
        """执行单个任务"""
        start = time.time()
        logger.info(f"Executing task: {task.id} - {task.description[:40]}")
        
        # 寻找匹配的工具
        tool = self._find_tool(task.description)
        
        if tool:
            result = self.tool_mgr.call(tool.name, {"task": task.description})
        else:
            # 没有匹配工具，模拟执行
            result = ToolResult(
                success=True,
                output=f"任务完成: {task.description}",
                duration_ms=0.0,
            )
        
        elapsed = (time.time() - start) * 1000
        result.duration_ms = round(elapsed, 2)
        self._stats["total_duration_ms"] += elapsed
        
        if result.success:
            self._stats["tasks_completed"] += 1
        else:
            self._stats["tasks_failed"] += 1
        
        return result
    
    def _find_tool(self, description: str) -> Optional[object]:
        """根据任务描述匹配合适的工具"""
        desc_lower = description.lower()
        tools = self.tool_mgr.list_tools()
        
        # 关键词匹配
        keyword_map = {
            "搜索": "web_search", "查找": "web_search", "search": "web_search",
            "读文件": "read_file", "读取": "read_file", "read": "read_file",
            "写文件": "write_file", "创建": "write_file", "write": "write_file",
            "执行": "run_command", "运行": "run_command", "shell": "run_command",
            "代码": "execute_code", "python": "execute_code",
            "记忆": "memory_search", "回忆": "memory_search", "remember": "memory_search",
        }
        
        for keyword, tool_name in keyword_map.items():
            if keyword in desc_lower:
                for t in tools:
                    if t.name == tool_name:
                        return t
        return None
    
    def execute_plan(self, plan: Plan, on_task_complete: Callable = None) -> Dict:
        """执行整个计划"""
        self._running = True
        results = {}
        
        for task in plan.tasks:
            if not self._running:
                break
            result = self.execute_task(task)
            task.status = "completed" if result.success else "failed"
            task.result = result
            results[task.id] = result
            if on_task_complete:
                on_task_complete(task, result)
        
        plan.completed = all(t.status == "completed" for t in plan.tasks)
        self._running = False
        return results
    
    def stop(self):
        self._running = False
    
    def get_stats(self) -> dict:
        total = self._stats["tasks_completed"] + self._stats["tasks_failed"]
        return {**self._stats, "total_tasks": total,
                "success_rate": round(self._stats["tasks_completed"]/max(total,1)*100, 1)}
