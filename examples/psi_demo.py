"""
PSI 需求驱动 Agent 自主行动流程模拟演示

展示 LAAP 的认知循环：
  感知 → 需求评估 → 情绪涌现 → 行动选择 → 学习满足需求 → 自我反思 → RSI 进化

运行: python examples/psi_demo.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from laap.agent.lifelike import LifelikeAgent, LifelikeConfig
from laap.cognition.needs import NeedType


def simulate_scenario():
    """模拟一个完整的 PSI 认知循环场景"""
    print("=" * 72)
    print("  LAAP PSI 需求驱动 Agent 自主行动模拟")
    print("  Lifeform Autonomous Adaptive Protocol")
    print("=" * 72)
    print()

    # ── 1. 创建 Agent ──
    config = LifelikeConfig(
        name="PSI-Demo",
        rsi_enabled=True,
        rsi_interval=5,
        reflection_interval=3,
        need_config={
            "competence": {"current_level": 0.3, "importance": 1.8},  # 胜任感低落
            "certainty":  {"current_level": 0.4, "importance": 1.3},  # 确定性不足
            "energy":     {"current_level": 0.7, "importance": 1.0},  # 能量充足
        },
    )
    agent = LifelikeAgent(config=config)
    print(f"  Agent [{agent.id[:8]}] 已初始化")
    print()

    # ── 2. 模拟多步认知循环 ──
    scenarios = [
        ("🟢 收到简单分析任务", 0.3, ["task", "analysis"]),
        ("🟡 遇到困难问题，进展缓慢", -0.2, ["task", "difficult"]),
        ("🔴 多次尝试失败，需要反思", -0.5, ["task", "failure"]),
        ("🟢 调整策略后找到突破口", 0.6, ["task", "breakthrough"]),
        ("🟢 任务完成，获得正反馈", 0.9, ["task", "success"]),
        ("🟡 新任务到来，环境变化", 0.1, ["task", "new", "uncertainty"]),
        ("🟢 运用已有经验快速解决", 0.7, ["task", "success"]),
    ]

    for i, (obs, success, tags) in enumerate(scenarios):
        print(f"  ── Step {i+1} ─────────────────────────────────────")
        print(f"  输入: {obs}")
        print()

        result = agent.step(obs, task_success=success, tags=tags)

        # 需求状态
        needs = agent.needs.get_profile()
        dominant_nt, dominant_drive = agent.needs.get_dominant_need()
        print(f"  需求状态:")
        for nt_name, ndata in needs.items():
            bar = "█" * int(ndata["current"] * 20) + "░" * (20 - int(ndata["current"] * 20))
            marker = " ◀ 主导" if nt_name == dominant_nt.value else ""
            print(f"    {nt_name:12s} |{bar}| {ndata['current']:.2f}  (drive={ndata['drive']:.2f}){marker}")
        print()

        # 情绪状态
        emo = result["emotional_state"]
        print(f"  情绪状态: valence={emo['valence']:+.3f}  arousal={emo['arousal']:.3f}  "
              f"dominance={emo['dominance']:.3f}  confidence={emo['confidence']:.3f}")
        print(f"  内在奖励: {result['intrinsic_reward']:+.4f}")
        print()

        # 行为
        print(f"  选择行动: {result['action']}")
        print(f"  行动结果: {result['action_result']}")
        print()

        # 反思 (如果有)
        if result.get("reflection"):
            ref = result["reflection"]
            print(f"  💭 自我反思 [步 {ref['episode']}]:")
            print(f"     观察: {ref['observation']}")
            print(f"     假设: {ref['hypothesis']}")
            print()

        # RSI (如果有)
        if result.get("rsi"):
            rsi = result["rsi"]
            print(f"  🧬 RSI 自我改进 [步 {rsi['episode']}]:")
            print(f"     假设: {rsi['hypothesis']}")
            print(f"     期望影响: {rsi['expected_impact']:.3f}")
            if rsi["tested"]:
                print(f"     测试结果: {rsi['test_result']}")
                print(f"     已采纳: {rsi['adopted']}")
            print()

        time.sleep(0.5)

    # ── 3. 最终总结 ──
    print("=" * 72)
    print("  模拟总结")
    print("=" * 72)
    print()

    # 综合评估
    eval_report = agent.evaluator.report(agent)
    print(f"  综合适应度: {eval_report['fitness']:.4f}")
    print(f"  各维度得分:")
    for k, v in eval_report["scores"].items():
        bar = "█" * int(v * 20) + "░" * (20 - int(v * 20))
        print(f"    {k:20s} |{bar}| {v:.3f}")
    print()

    # RSI 统计
    if agent.rsi:
        print(f"  RSI 进化引擎:")
        print(f"    总提案数: {len(agent.rsi.proposals)}")
        print(f"    已采纳: {agent.rsi.adopted_count}")
        print(f"    测试次数: {agent.rsi.test_count}")
        if agent.rsi.fitness_history:
            fit = agent.rsi.fitness_history
            trend = fit[-1] - fit[0]
            trend_str = "↑ 上升" if trend > 0.02 else ("↓ 下降" if trend < -0.02 else "→ 平台期")
            print(f"    适应度趋势: {trend_str} ({trend:+.4f})")
        print()

    # 学习到的需求变化
    print(f"  需求变化 (初始 → 最终):")
    for nt in NeedType:
        ndata = needs[nt.value]
        initial = {"certainty": 0.4, "competence": 0.3, "autonomy": 0.5,
                    "relatedness": 0.5, "energy": 0.7}
        init_val = initial.get(nt.value, 0.5)
        delta = ndata["current"] - init_val
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        print(f"    {nt.value:12s}: {init_val:.2f} {arrow} {ndata['current']:.2f} ({delta:+.2f})")
    print()

    print("  模拟完成。Agent 展示了 PSI 认知循环：")
    print("    需求驱动 → 情绪涌现 → 自主行动 → 学习满足 → 反思进化")
    print()


if __name__ == "__main__":
    simulate_scenario()