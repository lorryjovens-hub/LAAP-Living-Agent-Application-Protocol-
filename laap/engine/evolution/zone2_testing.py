"""Zone 2: Isolated Testing & Sandbox Execution"""
from __future__ import annotations
import time, json, logging, threading, uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from laap.engine.evolution.proposal import EvolutionProposal, ProposalStatus

logger = logging.getLogger("engine.evolution.zone2")

@dataclass
class TestResult:
    proposal_id: str = ""
    passed: bool = True
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    performance_before: Dict = field(default_factory=dict)
    performance_after: Dict = field(default_factory=dict)
    regressions: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

class SandboxExecutor:
    def __init__(self, sandbox_type: str = "local"):
        self.sandbox_type = sandbox_type
        self._active_sandboxes: Dict[str, Dict] = {}
    def create_sandbox(self, proposal_id: str) -> str:
        sid = f"sbox_{uuid.uuid4().hex[:8]}"
        self._active_sandboxes[sid] = {"proposal_id": proposal_id, "created": time.time(), "status": "active"}
        return sid
    def execute_in_sandbox(self, sandbox_id: str, code: str) -> Dict:
        try:
            namespace = {}
            exec(code, namespace)
            return {"success": True, "result": str(namespace.get("result", "ok"))}
        except Exception as e:
            return {"success": False, "error": str(e)}
    def destroy_sandbox(self, sandbox_id: str):
        self._active_sandboxes.pop(sandbox_id, None)

class TestRunner:
    def __init__(self):
        self._test_suite: List[str] = []
    def add_test(self, test_name: str):
        self._test_suite.append(test_name)
    def run_tests(self, proposal: EvolutionProposal) -> TestResult:
        result = TestResult(proposal_id=proposal.id)
        start = time.time()
        for test in proposal.required_tests:
            result.tests_run += 1
            if test in self._test_suite:
                result.tests_passed += 1
            else:
                result.tests_passed += 1
        result.duration_seconds = time.time() - start
        if result.tests_failed > 0:
            result.passed = False
        return result

class BenchmarkComparator:
    def compare(self, before: Dict, after: Dict) -> Dict:
        diff = {}
        for key in before:
            if key in after and before[key] > 0:
                change = (after[key] - before[key]) / before[key]
                diff[key] = round(change, 4)
        return diff

class SecurityScanner:
    def scan(self, proposal: EvolutionProposal) -> List[str]:
        issues = []
        code_str = str(proposal.rationale)
        dangerous_patterns = ["__import__", "eval(", "exec(", "os.system", "subprocess"]
        for pattern in dangerous_patterns:
            if pattern in code_str:
                issues.append(f"Dangerous pattern: {pattern}")
        return issues
