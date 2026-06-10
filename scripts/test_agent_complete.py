"""LAAP Agent 完整测试套件 — 真实DeepSeek API测试"""
import sys, time, json, os
sys.path.insert(0, r"D:\LAAP")

from laap.agent_core.agent import Agent, AgentConfig
from laap.agent_core.llm_provider import LLMConfig, LLMProvider, LLMFactory

print("="*60)
print("LAAP Agent 完整测试 — DeepSeek v4 Flash")
print("="*60)

# 配置DeepSeek
llm_config = LLMConfig(
    provider="deepseek",
    model="deepseek-v4-flash",
    api_key="sk-bb164bea88a04eeaafd993b41a4a2370",
    api_base="https://api.deepseek.com/v1",
    temperature=0.7,
    max_tokens=4096,
)

# 测试1：直接LLM调用
print("\n[测试1] 直接LLM API调用")
llm = LLMProvider(llm_config)
start = time.time()
resp = llm.chat([
    {"role": "system", "content": "你是一个智能助手，请简洁回答。"},
    {"role": "user", "content": "你好！请用一句话介绍你自己。"}
])
elapsed = time.time() - start
print(f"  回复: {resp.content[:100]}...")
print(f"  用时: {elapsed:.2f}s")
print(f"  Token: {resp.usage}")
print(f"  Finish: {resp.finish_reason}")

# 测试2：Agent基础对话
print("\n[测试2] Agent基础对话")
agent_config = AgentConfig(
    name="LAAP-Test-Agent",
    llm_provider="deepseek",
    llm_model="deepseek-v4-flash",
    enable_memory=True,
    enable_tools=True,
)
agent = Agent(agent_config)
agent.llm.config.api_key = "sk-bb164bea88a04eeaafd993b41a4a2370"

start = time.time()
resp1 = agent.chat("你好！请介绍一下你自己")
t1 = time.time() - start
print(f"  Q: 你好！请介绍一下你自己")
print(f"  A: {resp1[:150]}...")
print(f"  用时: {t1:.2f}s")

# 测试3：工具调用测试
print("\n[测试3] 工具系统测试")
tools = agent.tool_mgr.list_tools()
print(f"  工具总数: {len(tools)}")
for t in tools:
    r = agent.tool_mgr.call(t.name, {"thought": "test", "task": "test", "fact": "test", "query": "test",
                                      "path": ".", "content": "test", "command": "echo test",
                                      "code": "print(1)", "result": "done", "summary": "test"})
    status = "✅" if r.success else "❌"
    print(f"  {status} {t.name}: {r.output[:50] if r.output else 'OK'} ({r.duration_ms}ms)")

# 测试4：带工具的多轮对话
print("\n[测试4] 多轮对话测试")
start = time.time()
resp2 = agent.chat("现在几点了？")
t2 = time.time() - start
print(f"  Q: 现在几点了？")
print(f"  A: {resp2[:150]}...")
print(f"  用时: {t2:.2f}s")

start = time.time()
resp3 = agent.chat("你还记得我们刚才聊了什么吗？")
t3 = time.time() - start
print(f"  Q: 你还记得我们刚才聊了什么吗？")
print(f"  A: {resp3[:150]}...")
print(f"  用时: {t3:.2f}s")

# 测试5：记忆系统
print("\n[测试5] 记忆系统测试")
m = agent.memory
m.remember_fact("测试: LAAP是一个数字生命体协议", importance=0.9)
m.remember_fact("用户正在测试Agent的记忆功能", importance=0.8)
stats = m.get_stats()
print(f"  工作记忆: {stats['working_size']} chunks")
print(f"  情景记忆: {stats['episodic_count']} episodes")
print(f"  语义记忆: {stats['semantic_nodes']} concepts")
search = m.search_memory("LAAP")
print(f"  语义回忆: {search['semantic_memory']['found']}")

# 测试6：复杂任务规划
print("\n[测试6] 任务规划测试")
plan = agent.planner.plan("分析当前目录的文件结构", [t.name for t in tools])
print(f"  计划ID: {plan.id}")
print(f"  策略: {plan.strategy.value}")
for i, t in enumerate(plan.tasks):
    print(f"  步骤{i+1}: {t.description}")

# 测试7：Agent完整状态
print("\n[测试7] 系统状态导出")
d = agent.to_dict()
print(f"  Agent: {d['name']}")
print(f"  状态: {d['state']}")
print(f"  统计: {json.dumps(d['stats'], ensure_ascii=False)}")
print(f"  LLM: {json.dumps(d.get('llm', {}), ensure_ascii=False)}")
print(f"  工具: {json.dumps(d['tools'], ensure_ascii=False)}")
print(f"  执行器: {json.dumps(d['executor'], ensure_ascii=False)}")

print(f"\n{'='*60}")
print("🎉 全部测试完成！")
print(f"{'='*60}")
