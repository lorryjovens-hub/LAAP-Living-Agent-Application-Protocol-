"""LAAP — Subagent Tree Visualization for TUI

Displays hierarchical subagent/delegation trees in the TUI
with status icons, timing, and collapsible nodes.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rich.text import Text
from rich.style import Style
from rich.tree import Tree
from rich.table import Table
from rich.panel import Panel

from laap.ui.dragon_art import GOLD, GOLD_BRIGHT, GOLD_DIM, GOLD_LIGHT, CRIMSON, BG_DARK

# ── Node States ──────────────────────────────────────────────

@dataclass
class SubagentNode:
    """A single node in the subagent execution tree."""
    id: str
    name: str
    status: str = "pending"  # pending, running, completed, error
    parent_id: Optional[str] = None
    children: List["SubagentNode"] = field(default_factory=list)
    result: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    depth: int = 0

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def icon(self) -> str:
        icons = {
            "pending": "\u23f3",
            "running": "\U0001f504",
            "completed": "\u2705",
            "error": "\u274c",
        }
        return icons.get(self.status, "\u2753")

    @property
    def color(self) -> str:
        colors = {
            "pending": GOLD_DIM,
            "running": GOLD_BRIGHT,
            "completed": GOLD,
            "error": CRIMSON,
        }
        return colors.get(self.status, "#888")


class SubagentTree:
    """Manages and renders a tree of subagent tasks."""

    def __init__(self):
        self._nodes: Dict[str, SubagentNode] = {}
        self._roots: List[str] = []

    def add_task(self, task_id: str, name: str,
                 parent_id: Optional[str] = None) -> SubagentNode:
        """Add a task node to the tree."""
        node = SubagentNode(
            id=task_id, name=name, status="pending",
            parent_id=parent_id, started_at=time.time(),
            depth=(self._nodes[parent_id].depth + 1) if parent_id and parent_id in self._nodes else 0,
        )
        self._nodes[task_id] = node

        if parent_id and parent_id in self._nodes:
            self._nodes[parent_id].children.append(node)
        else:
            self._roots.append(task_id)

        return node

    def update_status(self, task_id: str, status: str,
                      result: Optional[str] = None,
                      error: Optional[str] = None):
        """Update task status."""
        node = self._nodes.get(task_id)
        if not node:
            return
        node.status = status
        if result:
            node.result = result[:200]
        if error:
            node.error = error
        if status in ("completed", "error"):
            node.completed_at = time.time()

    def to_rich_tree(self) -> Tree:
        """Convert to Rich Tree for TUI rendering."""
        if not self._roots:
            tree = Tree("No active sub-tasks", style=Style(color=GOLD_DIM))
            return tree

        tree = Tree(
            "\U0001f409 Sub-Agent Tasks",
            style=Style(color=GOLD_BRIGHT, bold=True),
        )

        for root_id in self._roots:
            self._add_node_to_tree(tree, root_id)

        return tree

    def _add_node_to_tree(self, parent_tree: Tree, node_id: str):
        """Recursively add nodes to the Rich tree."""
        node = self._nodes.get(node_id)
        if not node:
            return

        dur = f" ({node.duration:.1f}s)" if node.duration else ""
        label = Text()
        label.append(f" {node.icon} ", style=Style(color=node.color))
        label.append(f"{node.name}", style=Style(color=node.color, bold=(node.status == "running")))
        label.append(f"{dur}", style=Style(color=GOLD_DIM))

        if node.result:
            label.append(f"\n    {node.result[:60]}", style=Style(color=GOLD_DIM))
        if node.error:
            label.append(f"\n    \u274c {node.error[:60]}", style=Style(color=CRIMSON))

        branch = parent_tree.add(label)
        for child in node.children:
            self._add_node_to_tree(branch, child.id)

    def to_dict(self) -> Dict:
        """Serialize tree state."""
        return {
            "nodes": {k: {
                "id": v.id, "name": v.name, "status": v.status,
                "parent_id": v.parent_id,
                "duration": v.duration,
                "depth": v.depth,
            } for k, v in self._nodes.items()},
            "roots": self._roots,
        }

    def clear(self):
        self._nodes.clear()
        self._roots.clear()
