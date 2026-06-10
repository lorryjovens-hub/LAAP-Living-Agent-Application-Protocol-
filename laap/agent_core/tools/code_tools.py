"""Code Tools — 代码执行/分析工具"""
from __future__ import annotations
import sys, io, time, contextlib, logging, subprocess, tempfile, os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.tools.code")

def execute_python(code: str, timeout: int = 10) -> str:
    """执行Python代码并返回输出"""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    result = {"stdout": "", "stderr": "", "error": "", "timed_out": False}
    try:
        compiled = compile(code, "<exec>", "exec")
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            start = time.time()
            exec(compiled, {"__builtins__": __builtins__})
            elapsed = time.time() - start
        result["stdout"] = stdout_capture.getvalue()[:2000]
        result["stderr"] = stderr_capture.getvalue()[:500]
        result["elapsed"] = round(elapsed, 3)
    except Exception as e:
        result["error"] = str(e)[:500]
        result["stdout"] = stdout_capture.getvalue()[:1000]
    return json.dumps(result, ensure_ascii=False)

def run_shell(command: str, timeout: int = 10) -> str:
    """运行Shell命令"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, timeout=timeout)
        return json.dumps({
            "stdout": result.stdout.decode(errors='replace')[:2000],
            "stderr": result.stderr.decode(errors='replace')[:500],
            "returncode": result.returncode,
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Timeout after {timeout}s"})
    except Exception as e:
        return json.dumps({"error": str(e)[:500]})

import json as _json

TOOL_DEFS = [
    {"name":"execute_python","fn":execute_python,"desc":"执行Python代码","params":{"code":{"type":"string"},"timeout":{"type":"integer"}},"req":["code"]},
    {"name":"run_shell","fn":run_shell,"desc":"运行Shell命令","params":{"command":{"type":"string"},"timeout":{"type":"integer"}},"req":["command"]},
]
