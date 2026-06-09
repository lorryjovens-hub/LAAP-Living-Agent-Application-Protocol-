"""
LAAP Basic LifelikeAgent Demo
需求驱动的类生命 Agent 展示
"""
import sys
sys.path.insert(0, r"D:\LAAP")
from laap.agent.lifelike import LifelikeAgent

print("=" * 50)
print("LAAP Psi LifelikeAgent Demo")
print("=" * 50)

agent = LifelikeAgent()
print(f"\nAgent [{agent.id[:8]}] 诞生")
print("\n初始需求:")
for nt, nd in agent.needs.get_profile().items():
    print(f"  {nt:12s}: level={nd['current']:.2f} drive={nd['drive']:.3f}")

print("\n运行 20 步...")
for i in range(20):
    r = agent.step(f"step_{i}", task_success=0.5 + 0.2 * ((i % 3) - 1))
    if i % 5 == 0:
        e = r["emotional_state"]
        print(f"  step {i:2d}: {r['action']:10s} need={r['dominant_need']:10s} "
              f"V={e['valence']:+.2f} reward={r['intrinsic_reward']:+.3f}")

print(f"\n结果: {agent.step_count} steps, 总奖励={sum(agent._reward_history):.2f}")
print(f"情绪: {agent.emotion_gradient.state.to_dict()}")
