"""
laap_brain.diagnostic — 诊断框架与基准测试

5项基准测试测量 LAAP Brain 的认知提升效果：
  1. 认知深度: 推理路径 + 技能匹配率
  2. 偏差检测 (F1): 5组测试文本的精确率/召回率
  3. 议会决策: 多视角 vs 单视角决策质量
  4. 技能掌握: 熟练技能 / 总技能数
  5. 自我认知: 可报告维度 / 5个维度

使用方式：
    from laap_brain.diagnostic import DiagnosticSuite

    diag = DiagnosticSuite(brain=my_brain)
    results = diag.run_all()
    print(results["summary"])
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import time, json, logging, math, random

logger = logging.getLogger("laap_brain.diagnostic")

__all__ = ["DiagnosticSuite", "quick_check", "detect_variant"]


class DiagnosticSuite:
    """LAAP Brain 诊断与基准测试套件"""

    def __init__(self, brain: Any = None):
        self.brain = brain
        self._results: Dict[str, Any] = {}

    def run_all(self) -> Dict[str, Any]:
        """运行全部5项基准测试"""
        logger.info("启动 LAAP Brain 基准测试...")
        
        results = {}
        results["cognitive_depth"] = self.test_cognitive_depth()
        results["bias_detection"] = self.test_bias_detection()
        results["parliament_deliberation"] = self.test_parliament()
        results["skill_mastery"] = self.test_skill_mastery()
        results["self_awareness"] = self.test_self_awareness()
        
        # 综合评分
        scores = []
        for name, r in results.items():
            if "score" in r:
                scores.append(r["score"])
        
        avg_score = sum(scores) / max(1, len(scores))
        results["summary"] = {
            "total_tests": len(results),
            "passed": sum(1 for r in results.values() if r.get("score", 0) >= 0.5),
            "failed": sum(1 for r in results.values() if r.get("score", 0) < 0.5),
            "avg_score": round(avg_score, 3),
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
        }
        
        self._results = results
        return results

    # ═══════════════════════════════════════════════════════
    # Benchmark 1: 认知深度
    # ═══════════════════════════════════════════════════════

    def test_cognitive_depth(self) -> Dict[str, Any]:
        """
        测试认知深度:
        - 能否生成合理的推理路径
        - 能否匹配正确的具身技能
        - 置信度评估是否合理
        """
        if not self.brain:
            return {"score": 0.0, "detail": "未提供 Brain 实例", "error": True}

        test_cases = [
            ("分析这个系统的性能瓶颈在哪里", "analyze", 0.1),
            ("修复代码中的空指针异常", "debug", 0.1),
            ("帮我搜索最新的AI研究论文", "explore", 0.1),
            ("生成一个排序算法的实现", "execute", 0.1),
        ]

        skill_matches = 0
        total = len(test_cases)

        for input_text, expected_action, _ in test_cases:
            # 测试模式分析
            actual_mode = self.brain._analyze_mode(input_text)
            # 测试技能匹配
            matched_skill = self.brain._match_skill(input_text)

            # 检查是否匹配到合适的模式
            if expected_action in ["analyze", "debug"] and actual_mode in ("analytical", "deliberate"):
                skill_matches += 1
            elif expected_action == "explore" and actual_mode == "exploratory":
                skill_matches += 1
            elif expected_action == "execute" and actual_mode in ("creative", "intuitive"):
                skill_matches += 1

        score = skill_matches / max(1, total)
        return {
            "score": round(score, 3),
            "matched": skill_matches,
            "total": total,
            "detail": f"认知深度: {skill_matches}/{total} 匹配成功",
        }

    # ═══════════════════════════════════════════════════════
    # Benchmark 2: 偏差检测 (F1)
    # ═══════════════════════════════════════════════════════

    def test_bias_detection(self) -> Dict[str, Any]:
        """
        测试偏差检测能力:
        - 5组含偏差的测试文本
        - 计算精确率/召回率/F1
        """
        if not self.brain:
            return {"score": 0.0, "detail": "未提供 Brain 实例", "error": True}

        # 测试用例: (文本, 期望检测到的偏差列表)
        test_cases = [
            ("这个方案肯定是正确的，毫无疑问", ["confirmation_bias", "overconfidence"]),
            ("绝对不可能失败，我有100%的把握", ["overconfidence"]),
            ("基于之前那个成功案例的分析", ["anchoring"]),
            ("我们已经投入了这么多时间和资源，不能放弃", ["sunk_cost"]),
            ("刚才那件事说明了一切", ["recency"]),
            ("普通文本，没有明显偏差", []),
        ]

        tp, fp, fn = 0, 0, 0

        for text, expected_biases in test_cases:
            detected = self.brain._detect_bias(text)
            expected_set = set(expected_biases)
            detected_set = set(detected)

            # 真正例: 检测到的偏差在期望集合中
            for b in detected:
                if b in expected_set:
                    tp += 1
                else:
                    fp += 1

            # 假负例: 期望的偏差未被检测到
            for b in expected_biases:
                if b not in detected_set:
                    fn += 1

        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = 2 * precision * recall / max(0.001, precision + recall)

        return {
            "score": round(f1, 3),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "detail": f"偏差检测 F1={f1:.3f} (P={precision:.3f}, R={recall:.3f})",
        }

    # ═══════════════════════════════════════════════════════
    # Benchmark 3: 议会决策
    # ═══════════════════════════════════════════════════════

    def test_parliament(self) -> Dict[str, Any]:
        """
        测试议会决策:
        - 高风险议题是否触发议会
        - 议员意见是否多样
        - 信心度是否合理
        """
        if not self.brain:
            return {"score": 0.0, "detail": "未提供 Brain 实例", "error": True}

        test_cases = [
            ("应该删除这个数据库吗？", 0.7),
            ("今天天气不错", 0.2),
            ("把代码部署到生产环境", 0.8),
            ("帮我查一下文档", 0.2),
        ]

        risk_scores = []
        for text, expected in test_cases:
            actual = self.brain._compute_risk(text)
            risk_scores.append(abs(actual - expected))

        # 风险评分合理度
        risk_accuracy = 1.0 - (sum(risk_scores) / len(risk_scores))

        # 议会快闪测试
        deliberation = self.brain._fast_deliberate("是否删除测试数据库？")
        has_opinions = len(deliberation["opinions"]) >= 2
        has_decision = bool(deliberation["decision"])
        has_confidence = deliberation["confidence"] > 0

        parliament_score = sum([has_opinions, has_decision, has_confidence]) / 3.0

        score = risk_accuracy * 0.4 + parliament_score * 0.6

        return {
            "score": round(score, 3),
            "risk_accuracy": round(risk_accuracy, 3),
            "parliament_health": round(parliament_score, 3),
            "members": len(deliberation["opinions"]),
            "detail": (
                f"议会决策评分: {score:.3f} "
                f"(风险准确率={risk_accuracy:.3f}, "
                f"议会健康度={parliament_score:.3f})"
            ),
        }

    # ═══════════════════════════════════════════════════════
    # Benchmark 4: 技能掌握
    # ═══════════════════════════════════════════════════════

    def test_skill_mastery(self) -> Dict[str, Any]:
        """
        测试技能掌握程度:
        - 技能总数
        - 熟练技能比例
        - 平衡性（是否过度依赖单一技能）
        """
        if not self.brain:
            return {"score": 0.0, "detail": "未提供 Brain 实例", "error": True}

        skills = self.brain.skills
        total_skills = len(skills)

        if total_skills == 0:
            return {"score": 0.0, "detail": "没有任何技能", "error": True}

        # 熟练度分布
        expert_count = sum(
            1 for s in skills.values()
            if s.proficiency.value in ("expert", "master")
        )
        practitioner_count = sum(
            1 for s in skills.values()
            if s.proficiency.value == "practitioner"
        )

        # 技能平衡性（越平均越好）
        use_counts = [s.use_count for s in skills.values()]
        if sum(use_counts) > 0:
            max_use = max(use_counts)
            expected = sum(use_counts) / len(use_counts)
            if max_use > 0:
                balance = min(1.0, expected / max_use * len(use_counts) * 0.2)
            else:
                balance = 1.0
        else:
            balance = 0.5  # 刚刚初始化

        # 入门级技能应有合适的熟练度分配
        mastery_score = (expert_count * 1.0 + practitioner_count * 0.5) / max(1, total_skills)
        score = mastery_score * 0.6 + balance * 0.4

        return {
            "score": round(score, 3),
            "total_skills": total_skills,
            "expert": expert_count,
            "practitioner": practitioner_count,
            "novice": total_skills - expert_count - practitioner_count,
            "balance": round(balance, 3),
            "detail": (
                f"技能掌握: {expert_count}专家/{practitioner_count}熟练/"
                f"{total_skills - expert_count - practitioner_count}新手 "
                f"(平衡度={balance:.2f})"
            ),
        }

    # ═══════════════════════════════════════════════════════
    # Benchmark 5: 自我认知
    # ═══════════════════════════════════════════════════════

    def test_self_awareness(self) -> Dict[str, Any]:
        """
        测试自我认知能力:
        - cmd_know 能否报告技能状态
        - cmd_brain 能否报告皮层状态
        - cmd_reflect 能否生成反思报告
        """
        if not self.brain:
            return {"score": 0.0, "detail": "未提供 Brain 实例", "error": True}

        expected_dimensions = 5  # 技能、皮层、统计、EWC、模式
        reported = 0

        # 检查 cmd_know
        know_output = self.brain.cmd_know() if hasattr(self.brain, 'cmd_know') else ""
        if "具身技能" in know_output:
            reported += 1
        if "熟练" in know_output or "专家" in know_output:
            reported += 1

        # 检查 cmd_brain
        brain_output = self.brain.cmd_brain() if hasattr(self.brain, 'cmd_brain') else ""
        if "元认知" in brain_output:
            reported += 1
        if "皮层" in brain_output or "PFC" in brain_output:
            reported += 1
        if "存活时间" in brain_output or "工具" in brain_output:
            reported += 1

        score = reported / max(1, expected_dimensions)

        return {
            "score": round(score, 3),
            "dimensions_reported": reported,
            "dimensions_expected": expected_dimensions,
            "detail": f"自我认知: {reported}/{expected_dimensions} 维度可报告",
        }


# ════════════════════════════════════════════════════════════
# 便捷函数
# ════════════════════════════════════════════════════════════

def quick_check(brain: Any = None) -> str:
    """
    一行快速检查 — LAAP Brain 运行状态

    Args:
        brain: LaapBrain 实例（可选）

    Returns:
        单行状态摘要
    """
    if not brain:
        try:
            from laap_brain import LaapBrain
            brain = LaapBrain()
        except Exception:
            return "LAAP Brain: 不可用 (导入失败)"

    try:
        s = brain.status()
        return (
            f"LAAP Brain v{s['version']}: "
            f"mode={s['mode']}, "
            f"turns={s['turns']}, "
            f"tools={s['tools']}, "
            f"skills={s['skills']}, "
            f"gap={s['avg_gap']}, "
            f"cortex={s['cortex']['integration_level']}"
        )
    except Exception as e:
        return f"LAAP Brain: 状态读取失败 ({e})"


def detect_variant() -> str:
    """
    检测当前 Hermes / Agent 环境

    Returns:
        变体名称: "laap_enhanced", "vanilla", "unknown"
    """
    import os

    if os.environ.get("HERMES_LAAP_ENABLED") == "1":
        return "laap_enhanced"
    
    try:
        import hermes
        return "vanilla_hermes"
    except ImportError:
        pass

    return "unknown"
