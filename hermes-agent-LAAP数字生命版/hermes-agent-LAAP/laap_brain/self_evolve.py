"""
LAAP Self-Evolution & Auto-Healing Engine (Bridge-Integrated)
══════════════════════════════════════════════════════════════

Closed-loop system that runs inside agi_bridge.after_turn/after_tool:

  Monitor → Analyze → Act → Learn → Monitor (loop)
     │          │        │       │
     │          │        │       └─ 更新技能/记忆/知识图谱
     │          │        └─ 自动修复已知错误模式    
     │          └─ 检测重复错误 + 任务模式
     └─ 记录每次工具调用 + 对话结果

Auto-Heal patterns (built-in):
  - '_laap_bridge' not found → 已修复 (加类级默认值)
  - 'logger = logging.getLogger' → 已修复 (加括号)
  - 'expected an indented block' → 已修复 (缩进修正)
  - AttributeError → 自动 try/except 保护建议
"""

from __future__ import annotations
import json, os, time, logging, threading
from typing import Any, Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger("laap_brain.self_evolve")

# ── Auto-Heal Patterns ──
# Format: (error_substring, suggestion, severity)
HEAL_PATTERNS = [
    ("_laap_bridge", "类级默认值: _laap_bridge = None", 3),
    ("no attribute", "检查对象是否有该属性，加 hasattr() 保护", 2),
    ("IndentationError", "检查代码缩进层级是否一致", 2),
    ("NameError", "检查导入和变量定义顺序", 2),
    ("ImportError", "检查 sys.path 和包安装状态", 1),
    ("maximum recursion", "检查递归终止条件和缓存设计", 3),
    ("division by zero", "除零保护: if denominator != 0", 1),
    ("FileNotFoundError", "文件操作加 os.path.exists() 检查", 1),
    ("PermissionError", "检查文件权限和目录可写性", 1),
    ("Timeout", "超时保护: 设置 timeout 参数", 1),
    ("ConnectionError", "网络操作加重试机制", 1),
    ("KeyError", "字典访问用 .get() 替代 []", 1),
]


class SelfEvolveEngine:
    """
    Self-evolution + auto-healing loop for bridge-mounted LAAP.
    Runs inside after_turn and after_tool hooks.
    """

    def __init__(self, agent=None, hermes_home: str = None):
        self.agent = agent
        self.hermes_home = hermes_home or os.path.expanduser(
            "~/AppData/Local/hermes/profiles/laap-avatar")
        
        # Stats
        self.total_interactions = 0
        self.total_tools = 0
        self.total_errors = 0
        self.total_heals = 0
        self.total_skills = 0
        
        # Tracking
        self._tool_history: List[Dict] = []
        self._error_history: List[Dict] = []
        self._session_start = time.time()
        self._last_skill_check = 0
        self._last_memory_clean = 0
        
        # Learning data
        self._error_patterns: Dict[str, int] = defaultdict(int)
        self._tool_patterns: Dict[str, int] = defaultdict(int)
        self._domain_counts: Dict[str, int] = defaultdict(int)
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Load persistence
        self._load()

    def _load(self):
        """Load saved learning data."""
        path = os.path.join(self.hermes_home, ".self_evolve.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                self.total_interactions = data.get("interactions", 0)
                self.total_tools = data.get("tools", 0)
                self.total_errors = data.get("errors", 0)
                self.total_heals = data.get("heals", 0)
                self.total_skills = data.get("skills", 0)
                self._error_patterns = defaultdict(int, data.get("error_patterns", {}))
                self._tool_patterns = defaultdict(int, data.get("tool_patterns", {}))
                self._tool_history = data.get("tool_history", [])[-50:]
                self._error_history = data.get("error_history", [])[-50:]
            except: pass

    def _save(self):
        """Save learning data."""
        path = os.path.join(self.hermes_home, ".self_evolve.json")
        try:
            with open(path, "w") as f:
                json.dump({
                    "interactions": self.total_interactions,
                    "tools": self.total_tools,
                    "errors": self.total_errors,
                    "heals": self.total_heals,
                    "skills": self.total_skills,
                    "error_patterns": dict(self._error_patterns),
                    "tool_patterns": dict(self._tool_patterns),
                    "tool_history": self._tool_history[-50:],
                    "error_history": self._error_history[-50:],
                    "last_updated": time.time(),
                }, f, indent=2)
        except: pass

    def record_interaction(self, domain: str, duration: float, success: bool,
                           error: str = None, tier: int = 2):
        """Record a conversation turn (called by after_turn)."""
        with self._lock:
            self.total_interactions += 1
            self._domain_counts[domain] += 1
            
            if error:
                self.total_errors += 1
                entry = {
                    "time": time.time(),
                    "domain": domain,
                    "error": str(error)[:200],
                    "tier": tier,
                }
                self._error_history.append(entry)
                
                # Track error pattern
                for pattern, _, _ in HEAL_PATTERNS:
                    if pattern.lower() in str(error).lower():
                        self._error_patterns[pattern] += 1
                        break
                else:
                    # Unknown error pattern
                    key = str(error)[:50]
                    self._error_patterns[key] += 1
            
            # Periodic save + auto-actions
            if self.total_interactions % 10 == 0:
                self._auto_heal_check()
            if self.total_interactions % 25 == 0:
                self._auto_skill_check()
            if self.total_interactions % 50 == 0:
                self._auto_memory_clean()
                self._save()

    def record_tool(self, tool_name: str, duration: float, success: bool,
                    error: str = None):
        """Record a tool call (called by after_tool)."""
        with self._lock:
            self.total_tools += 1
            self._tool_patterns[tool_name] += 1
            self._tool_history.append({
                "tool": tool_name,
                "time": time.time(),
                "duration": round(duration, 2),
                "success": success,
                "error": str(error)[:100] if error else None,
            })

    def _auto_heal_check(self):
        """Check for frequent errors and generate fix suggestions."""
        if not self._error_patterns:
            return
        
        # Find most frequent error pattern
        most_common = max(self._error_patterns, key=self._error_patterns.get)
        count = self._error_patterns[most_common]
        
        if count < 3:
            return  # Need at least 3 occurrences to trigger heal
        
        # Check if we have a known fix
        for pattern, suggestion, severity in HEAL_PATTERNS:
            if pattern.lower() in most_common.lower() or most_common.lower() in pattern.lower():
                self.total_heals += 1
                logger.info(f"[Self-Evolve] Auto-heal #{self.total_heals}: "
                           f"'{most_common[:40]}' ({count}x) → {suggestion}")
                
                # Save fix suggestion to agent
                if self.agent and hasattr(self.agent, '_pending_fixes'):
                    self.agent._pending_fixes.append({
                        "pattern": most_common,
                        "count": count,
                        "suggestion": suggestion,
                        "severity": severity,
                        "time": time.time(),
                    })
                break

    def _auto_skill_check(self):
        """Auto-create skills for repeated task patterns."""
        # If a tool has been used >20 times, create a skill for it
        for tool, count in sorted(self._tool_patterns.items(), key=lambda x: -x[1]):
            if count >= 20 and hasattr(self.agent, 'learning_loop'):
                try:
                    skill_name = f"auto-tool-{tool.lower().replace('_', '-')}"
                    skill_path = os.path.join(self.hermes_home, "skills", "auto", f"{skill_name}.md")
                    os.makedirs(os.path.dirname(skill_path), exist_ok=True)
                    
                    content = f"""---
name: {skill_name}
description: "Auto-created skill for frequently used tool: {tool} (used {count}x)"
version: 1.0.0
---

# {tool} — Auto Skill (Used {count}x)

This skill was automatically created by the Self-Evolve Engine.
{tool} has been called {count} times across {self.total_interactions} interactions.

## Usage Tips
- This tool is used frequently — consider optimizing its invocation
- Track record: {count}x calls with {self.total_errors} errors
"""
                    with open(skill_path, "w") as f:
                        f.write(content)
                    
                    self.total_skills += 1
                    logger.info(f"[Self-Evolve] Auto-skill #{self.total_skills}: {skill_name} ({count}x)")
                except: pass
                break  # One skill per check cycle

    def _auto_memory_clean(self):
        """Auto-clean and summarize old data to stay within limits."""
        # Trim tool history
        self._tool_history = self._tool_history[-100:]
        # Trim error history
        self._error_history = self._error_history[-50:]
        
        # Reset low-frequency error patterns (< 3 occurrences)
        stale = [k for k, v in self._error_patterns.items() if v < 3 and k not in [p[0] for p in HEAL_PATTERNS]]
        for k in stale:
            del self._error_patterns[k]

    def get_heal_report(self) -> str:
        """Generate a human-readable heal summary."""
        lines = []
        lines.append(f"**Self-Evolve Engine** (运行 {time.time()-self._session_start:.0f}s)")
        lines.append(f"- 交互: {self.total_interactions} | 工具: {self.total_tools} | 错误: {self.total_errors}")
        lines.append(f"- 自愈: {self.total_heals}次 | 自动技能: {self.total_skills}个")
        
        if self._error_patterns:
            lines.append("\n**频繁错误:**")
            for pat, cnt in sorted(self._error_patterns.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"  - {pat[:40]}: {cnt}x")
        
        if self._tool_patterns:
            lines.append("\n**常用工具:**")
            for tool, cnt in sorted(self._tool_patterns.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"  - {tool}: {cnt}x")
        
        if hasattr(self.agent, '_pending_fixes') and self.agent._pending_fixes:
            lines.append("\n**待处理修复:**")
            for fix in self.agent._pending_fixes[-3:]:
                lines.append(f"  - [{fix['severity']}] {fix['suggestion'][:50]}")
        
        return "\n".join(lines)


def integrate_self_evolve(agent) -> SelfEvolveEngine:
    """Attach SelfEvolveEngine to a Hermes agent."""
    hermes_home = os.environ.get("HERMES_HOME") or os.path.expanduser(
        "~/AppData/Local/hermes/profiles/laap-avatar")
    engine = SelfEvolveEngine(agent=agent, hermes_home=hermes_home)
    agent.self_evolve = engine
    agent._pending_fixes = []
    logger.info(f"[Self-Evolve] Engine integrated: {hermes_home}")
    return engine
