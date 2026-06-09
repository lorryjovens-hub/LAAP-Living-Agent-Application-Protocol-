"""
LAAP — REST API 服务

提供 HTTP 接口来管理和监控 LAAP Agent。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    HAVE_FASTAPI = True
except ImportError:
    HAVE_FASTAPI = False
    # 占位
    class FastAPI: pass
    class BaseModel: pass
    class HTTPException(Exception): pass

from laap.agent.base import Agent, AgentConfig
from laap.agent.lifelike import LifelikeAgent, LifelikeConfig
from laap.agent.codex import CodexAgent, CodexConfig
from laap.llm.factory import LLMFactory

logger = logging.getLogger("laap.api")


if not HAVE_FASTAPI:
    app = None
else:
    app = FastAPI(title="LAAP API", version="0.2.0",
                  description="LAAP — Lifeform Autonomous Adaptive Protocol")

    agents: Dict[str, Agent] = {}
    factory = LLMFactory()

    class CreateAgentRequest(BaseModel):
        type: str = "codex"
        name: str = "LAAP-Agent"
        provider: str = ""
        model: str = ""
        rsi_enabled: bool = True
        workspace: str = ""

    class ChatRequest(BaseModel):
        message: str
        system_prompt: str = ""
        use_tools: bool = True

    class StepRequest(BaseModel):
        observation: str
        task_success: Optional[float] = None

    @app.get("/health")
    async def health():
        return {"status": "ok", "agents": len(agents),
                "llm": factory.available}

    @app.post("/agents/create")
    async def create_agent(req: CreateAgentRequest) -> Dict[str, Any]:
        if req.type == "codex":
            config = CodexConfig(name=req.name, workspace_dir=req.workspace)
            agent = CodexAgent(config=config, llm_factory=factory)
        elif req.type == "lifelike":
            config = LifelikeConfig(name=req.name, rsi_enabled=req.rsi_enabled)
            agent = LifelikeAgent(config=config, llm_factory=factory)
        else:
            config = AgentConfig(name=req.name)
            agent = Agent(config=config, llm_factory=factory)
        agents[agent.id] = agent
        return {"agent_id": agent.id, "name": agent.config.name,
                "type": req.type, "status": agent.status()}

    @app.get("/agents")
    async def list_agents() -> List[Dict[str, Any]]:
        return [{"id": aid, "name": a.config.name,
                 "alive": a.alive, "steps": a.step_count}
                for aid, a in agents.items()]

    @app.get("/agents/{agent_id}")
    async def get_agent(agent_id: str) -> Dict[str, Any]:
        agent = agents.get(agent_id)
        if not agent: raise HTTPException(404, "Agent not found")
        if hasattr(agent, 'complete_status'):
            return agent.complete_status()
        return agent.status()

    @app.post("/agents/{agent_id}/chat")
    async def chat_with_agent(agent_id: str, req: ChatRequest) -> Dict[str, Any]:
        agent = agents.get(agent_id)
        if not agent: raise HTTPException(404, "Agent not found")
        response = agent.chat(req.message, req.system_prompt,
                              tools=agent.get_tool_defs() if req.use_tools else None)
        return {"response": response, "steps": agent.step_count}

    @app.post("/agents/{agent_id}/step")
    async def step_agent(agent_id: str, req: StepRequest) -> Dict[str, Any]:
        agent = agents.get(agent_id)
        if not agent: raise HTTPException(404, "Agent not found")
        if isinstance(agent, LifelikeAgent):
            return agent.step(req.observation, req.task_success)
        return {"error": "LifelikeAgent required for step"}

    @app.post("/agents/{agent_id}/rsi")
    async def trigger_rsi(agent_id: str) -> Dict[str, Any]:
        agent = agents.get(agent_id)
        if not agent: raise HTTPException(404, "Agent not found")
        if hasattr(agent, 'rsi') and agent.rsi:
            proposal = agent.rsi.step(agent, force=True)
            return {"proposal": proposal.to_dict() if proposal else None,
                    "rsi_status": agent.rsi.status(),
                    "fitness": agent.evaluator.report(agent) if hasattr(agent, 'evaluator') else None}
        return {"error": "RSI not enabled on this agent"}

    @app.get("/agents/{agent_id}/tools")
    async def list_tools(agent_id: str) -> List[Dict[str, Any]]:
        agent = agents.get(agent_id)
        if not agent: raise HTTPException(404, "Agent not found")
        return [{"name": t.name, "description": t.description[:60],
                 "category": t.category}
                for t in agent.tool_registry.list()]

    @app.on_event("startup")
    async def startup():
        logger.info("LAAP API 服务启动")


def serve(host: str = "127.0.0.1", port: int = 8000):
    """启动 API 服务"""
    if not HAVE_FASTAPI:
        print("需要安装 fastapi 和 uvicorn: pip install fastapi uvicorn")
        return
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    serve()
