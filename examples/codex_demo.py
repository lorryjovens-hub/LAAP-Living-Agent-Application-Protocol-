"""
LAAP CodexAgent Demo
展示代码 Agent 的工具和能力
"""
import sys
sys.path.insert(0, r"D:\LAAP")
from laap.agent.codex import CodexAgent

print("=" * 50)
print("LAAP CodexAgent Demo")
print("=" * 50)

agent = CodexAgent()
print(f"\nAgent [{agent.id[:8]}]")
print(f"工具总数: {agent.tool_registry.count}")
print(f"工具类别: {agent.tool_registry.categories}")

print("\n注册的工具:")
for t in agent.tool_registry.list():
    print(f"  {t.name:22s} [{t.category:10s}] {t.description[:40]}")
