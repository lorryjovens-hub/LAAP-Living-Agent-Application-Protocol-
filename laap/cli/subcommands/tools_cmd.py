"""Tool management"""
from laap.agent_core.agent import Agent, AgentConfig
def run(args):
    agent = Agent(AgentConfig(name="LAAP-CLI", enable_tools=True))
    tools = agent.tool_mgr.list_tools()
    if getattr(args, 'action', 'list') == "list":
        by_cat = {}
        for t in tools:
            by_cat.setdefault(t.category, []).append(t.name)
        print(f"\nTools: {len(tools)} total")
        for cat, names in sorted(by_cat.items()):
            print(f"  {cat}: {', '.join(names)}")
