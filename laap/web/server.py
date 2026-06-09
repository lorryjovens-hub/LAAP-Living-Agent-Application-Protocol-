"""
LAAP — Golden Dragon Web Management Server
Professional web UI for configuring and monitoring the LAAP agent.
Serves the golden dragon dashboard + all configuration endpoints.
"""

from __future__ import annotations
import json, logging, os, time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("laap.web")

_HERE = Path(__file__).resolve().parent
_STATIC = _HERE / "static"
_TEMPLATES = _HERE / "templates"
_I18N = _HERE / "i18n"

app = None


def create_app():
    """Create the FastAPI application with all routes."""
    global app
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError:
        print("\n  [!] fastapi not installed. Install with: pip install fastapi uvicorn\n")
        return None

    app = FastAPI(title="LAAP Web UI", version="0.3.1",
                  description="LAAP Golden Dragon Management Interface")

    # ── API Routes (must come BEFORE catch-all) ──

    @app.get("/api/status")
    async def get_status():
        from laap import __version__
        from laap.cli.config_manager import config_manager
        active = config_manager.get_active()
        return {
            "alive": True,
            "version": __version__,
            "uptime": f"{time.time():.0f}s",
            "model": (active.model if active else "N/A"),
            "provider": config_manager.config.active_provider,
            "tools": 18,
            "steps": 0,
            "platforms_connected": 0,
        }

    @app.get("/api/i18n/{lang}")
    async def get_i18n(lang: str):
        lang_file = _I18N / f"{lang}.json"
        if lang_file.exists():
            return json.loads(lang_file.read_text(encoding="utf-8"))
        fallback = _I18N / "en.json"
        if fallback.exists():
            return json.loads(fallback.read_text(encoding="utf-8"))
        return {"error": "i18n not found"}

    @app.get("/api/config")
    async def get_config():
        from laap.cli.config_manager import config_manager
        return config_manager.config.to_dict()

    @app.post("/api/config/llm")
    async def save_llm_config(data: Dict[str, Any]):
        from laap.cli.config_manager import config_manager
        config_manager.set_provider(
            provider_id=data.get("provider", "openai"),
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", ""),
            model=data.get("model", ""),
        )
        return {"success": True}

    @app.post("/api/config/platform/{platform_id}")
    async def configure_platform(platform_id: str, data: Dict[str, Any]):
        config_dir = Path.home() / ".laap" / "platforms"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / f"{platform_id}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"success": True, "platform": platform_id}

    @app.get("/api/platforms")
    async def list_platforms():
        config_dir = Path.home() / ".laap" / "platforms"
        all_platforms = ["telegram", "discord", "slack", "whatsapp", "feishu",
                         "dingtalk", "wecom", "weixin", "matrix", "email", "signal", "sms"]
        result = []
        for pid in all_platforms:
            configured = False
            config = {}
            if config_dir.exists():
                pfile = config_dir / f"{pid}.json"
                if pfile.exists():
                    try:
                        config = json.loads(pfile.read_text(encoding="utf-8"))
                        configured = True
                    except: pass
            result.append({"id": pid, "configured": configured, "config": config})
        return {"platforms": result}

    @app.get("/api/tools")
    async def list_tools():
        tools = [
            {"name": "read_file", "category": "code", "enabled": True},
            {"name": "write_file", "category": "code", "enabled": True},
            {"name": "edit_file", "category": "code", "enabled": True},
            {"name": "create_file", "category": "code", "enabled": True},
            {"name": "list_dir", "category": "code", "enabled": True},
            {"name": "search_code", "category": "code", "enabled": True},
            {"name": "run_command", "category": "shell", "enabled": True},
            {"name": "run_python", "category": "shell", "enabled": True},
            {"name": "git_status", "category": "git", "enabled": True},
            {"name": "git_diff", "category": "git", "enabled": True},
            {"name": "git_commit", "category": "git", "enabled": True},
            {"name": "web_fetch", "category": "web", "enabled": True},
            {"name": "web_search", "category": "web", "enabled": True},
        ]
        return {"tools": tools, "count": len(tools)}

    @app.get("/api/memory")
    async def get_memory():
        return {"episodic": 0, "semantic": 0, "reflective": 0, "procedural": 0}

    @app.post("/api/memory/clear")
    async def clear_memory():
        return {"success": True}

    @app.get("/api/logs")
    async def get_logs():
        log_path = Path.home() / ".laap" / "logs" / "agent.log"
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8").split("\n")[-50:]
            return {"logs": lines}
        return {"logs": ["No logs available"]}

    # ── Static Files ──
    if _STATIC.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

    # ── Main HTML Page (catch-all) ──
    @app.get("/")
    async def serve_index():
        index_path = _TEMPLATES / "index.html"
        if index_path.exists():
            return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>LAAP</h1><p>UI not found</p>")

    logger.info("LAAP Web UI created with %d routes", len(app.routes))
    return app


def serve(host: str = "127.0.0.1", port: int = 8080):
    """Start the LAAP web server."""
    global app
    if app is None:
        app = create_app()
    if app is None:
        return
    try:
        import uvicorn
        # print(f"\n  {'='*50}")
        # print(f"  LAAP Web UI: http://{host}:{port}")
        # print(f"  {'='*50}\n")
        uvicorn.run(app, host=host, port=port, log_level="info")
    except ImportError:
        print("\n  [!] uvicorn not installed. Install with: pip install uvicorn\n")


if app is None:
    app = create_app()
