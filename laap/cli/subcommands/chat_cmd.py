"""Single chat"""
from laap.agent_core.agent import Agent, AgentConfig
def run(args):
    msg = " ".join(getattr(args, 'message', ["hello"]))
    agent = Agent(AgentConfig(name="LAAP-CLI"))
    print(agent.chat(msg))
