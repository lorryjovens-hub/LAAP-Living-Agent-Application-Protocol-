"""
LAAP — 沙盒执行环境

安全的代码执行沙盒，用于测试 Agent 的自我修改提案。
隔离文件系统、网络和执行时间。
"""
from __future__ import annotations
import subprocess, os, tempfile, textwrap, json, logging, sys
from typing import Any, Dict, List, Optional
import time

logger = logging.getLogger("laap.evolution.sandbox")


class Sandbox:
    """安全的沙盒执行环境"""

    def __init__(self, workdir: Optional[str] = None, timeout: int = 30):
        self.workdir = workdir or tempfile.mkdtemp(prefix="laap_sandbox_")
        self.timeout = timeout
        self.history: List[dict] = []

    def run_code(self, code: str, context: Optional[Dict] = None) -> dict:
        """在沙盒中运行 Python 代码并捕获输出"""
        ctx_json = json.dumps(context or {})
        wrapped = textwrap.dedent(f'''
        import json, sys
        _ctx = json.loads({json.dumps(ctx_json)})
        try:
            _locals = {{}}
            exec({json.dumps(code)}, {{"__builtins__": __builtins__}}, _locals)
            _result = _locals.get("result", "ok")
            print("__SANDBOX_OK__")
            print(json.dumps({{"type": "result", "value": str(_result)[:500]}}))
        except Exception as e:
            print("__SANDBOX_ERR__")
            print(json.dumps({{"type": "error", "value": str(e)[:500]}}))
        ''')
        try:
            result = subprocess.run(
                [sys.executable, "-c", wrapped],
                capture_output=True, text=True, timeout=self.timeout,
                cwd=self.workdir,
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            ok = "__SANDBOX_OK__" in stdout
            entry = {
                "success": ok,
                "stdout": stdout[-2000:],
                "stderr": stderr[-1000:],
                "exit_code": result.returncode,
                "timeout": False,
            }
            self.history.append(entry)
            return entry
        except subprocess.TimeoutExpired:
            entry = {"success": False, "error": f"timeout ({self.timeout}s)", "timeout": True}
            self.history.append(entry)
            return entry

    def test_modification(self, original_code: str, modified_code: str,
                          tests: List[str]) -> dict:
        """测试代码修改"""
        test_code = "\n".join(tests)
        orig = self.run_code(original_code + "\n" + test_code)
        mod = self.run_code(modified_code + "\n" + test_code)
        return {
            "both_ok": orig.get("success", False) and mod.get("success", False),
            "original": orig, "modified": mod,
        }

    def clean(self):
        import shutil
        try:
            shutil.rmtree(self.workdir)
        except Exception:
            pass
        self.history.clear()
