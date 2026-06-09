"""
LAAP — CodexAgent：代码生成与自我进化 Agent

类似 Claude Code 的能力，但具有自我意识：
  - 代码生成、编辑、执行
  - 文件系统操作
  - 自我修改代码
  - RSI 驱动的进化
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging, os, sys, textwrap, json

from laap.agent.lifelike import LifelikeAgent, LifelikeConfig
from laap.evolution.sandbox import Sandbox
from laap.tools import registry as global_registry

logger = logging.getLogger("laap.agent.codex")


class CodexConfig(LifelikeConfig):
    workspace_dir: str = ""
    sandbox_timeout: int = 30
    auto_register_all_tools: bool = True


class CodexAgent(LifelikeAgent):
    """具有代码生成和自我进化能力的 Agent"""

    def __init__(self, config: Optional[CodexConfig] = None,
                 llm_factory=None, show_banner: Optional[bool] = None):
        super().__init__(config or CodexConfig(), llm_factory,
                         show_banner=show_banner)
        self.config: CodexConfig = self.config

        # 沙盒
        self.sandbox = Sandbox(
            workdir=self.config.workspace_dir or None,
            timeout=self.config.sandbox_timeout,
        )

        # 自动注册所有内置工具
        if self.config.auto_register_all_tools:
            self._register_code_tools()

        # 当前编辑的文件
        self.current_file: Optional[str] = None

        logger.info(f"CodexAgent [{self.id[:8]}] 代码引擎就绪")

    def _register_code_tools(self):
        """注册代码工具集 — 只注册 CodexAgent 独有工具，基础工具由 Agent.__init__ 注册"""
        if getattr(self, '_codex_tools_registered', False):
            return
        self._codex_tools_registered = True

        # 注册自定义代码相关工具（基础工具 code_edit/shell/web 已由 Agent.__init__ 注册）
        self.register_tool("write_code", self._write_code,
                           "生成代码并写入文件，同时执行语法检查",
                           category="code")
        self.register_tool("self_modify", self._self_modify_code,
                           "修改自身的代码以实现自我进化",
                           category="code", stop_after=True)
        self.register_tool("run_tests", self._run_tests,
                           "运行测试验证代码正确性",
                           category="code")
        self.register_tool("install_deps", self._install_deps,
                           "安装 Python 依赖",
                           category="code")

    def _write_code(self, file_path: str, code: str,
                    check_syntax: bool = True) -> str:
        """生成代码文件

        Args:
            file_path: 文件路径
            code: 代码内容
            check_syntax: 是否做语法检查
        """
        abs_path = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(code)
        lines = code.count("\n") + 1
        msg = f"Written: {abs_path} ({lines} lines)"

        if check_syntax and file_path.endswith(".py"):
            try:
                compile(code, abs_path, "exec")
                msg += " [syntax OK]"
            except SyntaxError as e:
                msg += f" [syntax error: {e}]"

        logger.info(msg)
        return msg

    def _self_modify_code(self, file_path: str, old_code: str,
                          new_code: str, reason: str = "") -> str:
        """修改自身代码文件以实现自我进化

        Args:
            file_path: 要修改的文件路径
            old_code: 要替换的旧代码
            new_code: 新代码
            reason: 修改原因
        """
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return f"Error: file not found: {abs_path}"

        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()

        if old_code not in content:
            return f"Error: old_code not found in {file_path}"

        new_content = content.replace(old_code, new_code, 1)

        # 语法检查
        if file_path.endswith(".py"):
            try:
                compile(new_content, abs_path, "exec")
            except SyntaxError as e:
                return f"Syntax error in modified code: {e}"

        # 写入
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        self._self_modifications += 1
        self.awareness.record_event("self_modify", {
            "file": file_path, "reason": reason[:60] if reason else "",
        })
        logger.info(f"Self-modification #{self._self_modifications}: {file_path}")
        return f"Self-modified: {abs_path}"

    def _run_tests(self, test_dir: str = "", pattern: str = "test_*.py") -> str:
        """运行测试

        Args:
            test_dir: 测试目录
            pattern: 测试文件匹配模式
        """
        import subprocess
        try:
            cmd = ["python", "-m", "pytest", pattern, "-v", "--tb=short"]
            if test_dir:
                cmd = ["python", "-m", "pytest", test_dir, "-v", "--tb=short"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
            )
            output = (result.stdout + "\n" + result.stderr)[-2000:]
            passed = "passed" in result.stdout.lower() or "failed" not in result.stdout.lower()
            return f"{'PASS' if passed else 'FAIL'}\n{output}"
        except subprocess.TimeoutExpired:
            return "Test timeout (60s)"
        except Exception as e:
            return f"Test error: {e}"

    def _install_deps(self, packages: str) -> str:
        """安装 Python 依赖

        Args:
            packages: 包名（空格分隔）
        """
        import subprocess
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install"] + packages.split(),
                capture_output=True, text=True, timeout=120,
            )
            return result.stdout[-1000:] or result.stderr[-1000:] or "Done"
        except subprocess.TimeoutExpired:
            return "Install timeout"
        except Exception as e:
            return f"Install error: {e}"

    def generate_code(self, prompt: str, language: str = "python",
                      system_prompt: str = "") -> str:
        """用 LLM 生成代码"""
        sp = system_prompt or (
            f"你是一个 {language} 代码生成专家。"
            f"只输出代码，不要解释。代码必须完整、可直接运行。"
        )
        response = self.chat(prompt, system_prompt=sp,
                             tools=None)  # 代码生成不需要工具
        return response

    def review_code(self, code: str) -> str:
        """审查代码"""
        return self.chat(
            f"审查以下代码的安全性、性能和正确性：\n```python\n{code}\n```",
            system_prompt="你是一个代码审查专家。列出每个问题的严重程度和修复建议。",
            tools=None,
        )

    def status(self) -> dict:
        s = super().complete_status()
        s.update({
            "workspace": self.config.workspace_dir or os.getcwd(),
            "sandbox": self.sandbox.workdir,
            "tools_count": self.tool_registry.count,
        })
        return s
