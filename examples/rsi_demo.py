"""
LAAP RSI Self-Improvement Demo
展示 Agent 如何通过递归自我改进优化自身
"""
import sys
sys.path.insert(0, r"D:\LAAP")
from laap.agent.lifelike import LifelikeAgent, LifelikeConfig
from laap.evaluation.fitness import FitnessEvaluator

print("=" * 50)
print("LAAP RSI Self-Improvement Demo")
print("=" * 50)

agent = LifelikeAgent(config=LifelikeConfig(
    name="RSI-Learner", rsi_enabled=True, rsi_interval=10, reflection_interval=5
))
ev = FitnessEvaluator()
print(f"\n初始适应度: {ev.composite_fitness(agent):.4f}")

for i in range(50):
    r = agent.step(f"exp_{i}", task_success=0.5 + 0.3 * ((i % 5) / 5.0))
    if r.get("rsi"):
        print(f"  step {i:2d}: RSI={r['rsi']['hypothesis'][:45]}")

if agent.rsi:
    s = agent.rsi.status()
    print(f"\nRSI 报告:")
    print(f"  提案: {s['total']}, 采纳: {s['adopted']}")
    print(f"  采纳率: {s['adoption_rate']:.1%}")
    print(f"  信息整合度: {s['info_integration']:.3f}")
    print(f"  适应度: {ev.composite_fitness(agent):.4f}")
