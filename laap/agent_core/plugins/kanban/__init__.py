"""Kanban Plugin — 看板任务管理"""
import logging, json, time
from laap.agent_core.plugins.hooks import HookRegistry, HookPoint
logger = logging.getLogger("plugins.kanban")

_board = {"todo": [], "doing": [], "done": []}

def init_plugin(agent=None, config=None):
    logger.info("Kanban plugin initialized")
    return {"status": "ok"}

def add_task(title: str, column: str = "todo") -> dict:
    task = {"id": hash(title + str(time.time())) % 10000, "title": title, "created": time.time()}
    if column in _board:
        _board[column].append(task)
    return task

def move_task(task_id: int, to_column: str) -> bool:
    for col in _board:
        for task in _board[col]:
            if task["id"] == task_id:
                _board[col].remove(task)
                if to_column in _board:
                    _board[to_column].append(task)
                return True
    return False

def get_board() -> dict:
    return {k: len(v) for k, v in _board.items()}

def shutdown():
    pass
