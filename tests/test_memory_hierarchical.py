"""
单元测试: LAAP 层次化记忆系统

覆盖:
  - MemoryItem / Skill / Reflection    数据类行为
  - HierarchicalMemory                  四层记忆系统
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from laap.memory.hierarchical import HierarchicalMemory, MemoryItem, Skill, Reflection


# ═══════════════════════════════════════════════════════════════
# MemoryItem 单元
# ═══════════════════════════════════════════════════════════════

class TestMemoryItem:
    def test_init_defaults(self):
        """MemoryItem 默认值"""
        item = MemoryItem(content="hello")
        assert item.content == "hello"
        assert item.tags == []
        assert item.emotional_valence == 0.0
        assert item.importance == 0.5
        assert item.access_count == 0

    def test_age_increases(self):
        """随时间的推移 age 增加"""
        item = MemoryItem(content="test")
        age1 = item.age
        time.sleep(0.01)
        age2 = item.age
        assert age2 > age1

    def test_to_dict(self):
        """to_dict 返回正确字段"""
        item = MemoryItem(content="hello world", tags=["test", "demo"],
                           emotional_valence=0.5, importance=0.8)
        d = item.to_dict()
        assert "content" in d
        assert "tags" in d
        assert "valence" in d
        assert "importance" in d
        assert "age_s" in d


# ═══════════════════════════════════════════════════════════════
# Skill 单元
# ═══════════════════════════════════════════════════════════════

class TestSkill:
    def test_success_rate_no_attempts(self):
        """无尝试时 success_rate 为 0"""
        s = Skill(name="test")
        assert s.success_rate == 0.0

    def test_success_rate_all_success(self):
        """全部成功时 success_rate 为 1"""
        s = Skill(name="test", success_count=10, fail_count=0)
        assert s.success_rate == 1.0

    def test_success_rate_mixed(self):
        """混合时 success_rate 计算正确"""
        s = Skill(name="test", success_count=7, fail_count=3)
        assert s.success_rate == pytest.approx(0.7)

    def test_to_dict(self):
        """to_dict 返回正确字段"""
        s = Skill(name="code_gen", proficiency=0.85, success_count=10, fail_count=2)
        d = s.to_dict()
        assert d["name"] == "code_gen"
        assert d["proficiency"] == 0.85
        assert d["success_rate"] == pytest.approx(10/12, abs=0.01)


# ═══════════════════════════════════════════════════════════════
# Reflection 单元
# ═══════════════════════════════════════════════════════════════

class TestReflection:
    def test_to_dict(self):
        """to_dict 返回正确字段"""
        ref = Reflection(episode=1, observation="性能下降",
                         hypothesis="增加探索率", outcome="采纳",
                         reward_delta=0.05, adopted=True)
        d = ref.to_dict()
        assert d["episode"] == 1
        assert d["adopted"] is True
        assert d["reward_delta"] == 0.05


# ═══════════════════════════════════════════════════════════════
# HierarchicalMemory 单元 — 核心四层记忆系统
# ═══════════════════════════════════════════════════════════════

class TestHierarchicalMemory:
    def test_init(self):
        """初始化各层为空"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        assert len(mem.wm) == 0
        assert len(mem.episodic) == 0
        assert len(mem.semantic) == 0
        assert len(mem.skills) == 0
        assert len(mem.reflections) == 0

    def test_perceive_adds_to_working_memory(self):
        """perceive 添加到工作记忆"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        mem.perceive("注意这个信息", tags=["important"], importance=0.9)
        assert len(mem.wm) == 1
        assert mem.wm[0].content == "注意这个信息"

    def test_perceive_with_valence(self):
        """perceive 支持情感标记"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        mem.perceive("好消息", valence=0.8, importance=0.7)
        assert mem.wm[0].emotional_valence == 0.8
        assert mem.wm[0].importance == 0.7

    def test_remember_adds_to_episodic(self):
        """remember 添加到情景记忆"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        mem.remember("经历了一件事", tags=["exp"])
        assert len(mem.episodic) == 1
        assert mem.total_items == 1

    def test_recall_by_tags(self):
        """recall 通过标签检索"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        mem.remember("任务A", tags=["task", "urgent"])
        mem.remember("任务B", tags=["task", "normal"])
        mem.remember("闲聊", tags=["chat"])
        results = mem.recall(query_tags=["urgent"])
        assert len(results) == 1
        assert results[0].content == "任务A"

    def test_recall_by_importance_filter(self):
        """recall 支持最小重要性过滤"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        mem.remember("低重要性", importance=0.2)
        mem.remember("高重要性", importance=0.9)
        results = mem.recall(min_importance=0.5)
        assert len(results) == 1
        assert results[0].content == "高重要性"

    def test_recall_increments_access_count(self):
        """recall 增加访问次数"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        mem.remember("test", tags=["t"])
        assert mem.episodic[0].access_count == 0
        mem.recall(query_tags=["t"])
        assert mem.episodic[0].access_count == 1

    def test_recall_returns_empty_for_no_match(self):
        """无匹配时返回空列表"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        mem.remember("test", tags=["a"])
        results = mem.recall(query_tags=["nonexistent"])
        assert results == []

    def test_recall_limit(self):
        """recall 限制返回数量"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        for i in range(10):
            mem.remember(f"item_{i}", tags=["t"])
        results = mem.recall(query_tags=["t"], limit=3)
        assert len(results) == 3

    def test_learn_adds_to_semantic(self):
        """learn 添加到语义记忆"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        mem.learn("python_syntax", "Python 是动态类型语言", importance=0.8)
        assert "python_syntax" in mem.semantic
        assert mem.semantic["python_syntax"].importance == 0.8

    def test_learn_overwrites_existing(self):
        """learn 覆盖已有的语义条目"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        mem.learn("key", "旧内容")
        mem.learn("key", "新内容")
        assert mem.semantic["key"].content == "新内容"

    def test_learn_skill(self):
        """技能学习与查询"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        mem.skills["git_commit"] = Skill(name="git_commit", proficiency=0.0)
        assert "git_commit" in mem.skills
        assert mem.skills["git_commit"].proficiency == 0.0

    def test_skill_success_rate(self):
        """技能成功率计算"""
        sk = Skill(name="test", success_count=8, fail_count=2)
        assert sk.success_rate == 0.8
        assert sk.proficiency == 0.0

    def test_add_reflection(self):
        """添加反思记录"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        ref = Reflection(episode=1, observation="observed",
                         hypothesis="hypothesis")
        mem.reflections.append(ref)
        assert len(mem.reflections) == 1

    def test_recent_reflections(self):
        """获取最近的反思记录"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        for i in range(5):
            mem.reflections.append(Reflection(
                episode=i, observation=f"obs_{i}", hypothesis=f"hyp_{i}"))
        recent = mem.reflections[-3:]
        assert len(recent) == 3
        assert recent[-1].episode == 4

    def test_wm_eviction(self):
        """工作记忆到达上限后自动淘汰旧条目"""
        mem = HierarchicalMemory(wm_size=3, use_rust=False, use_quantum=False)
        for i in range(5):
            mem.perceive(f"item_{i}")
        assert len(mem.wm) == 3
        assert mem.wm[0].content == "item_2"  # 最早的两个被淘汰

    def test_forgotten_counter(self):
        """forgotten 计数器工作"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        assert mem.forgotten == 0

    def test_no_rust_by_default_in_test(self):
        """测试环境中默认不使用 Rust 后端"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        assert mem._rust is None

    def test_no_quantum_by_default_in_test(self):
        """测试环境中默认不使用 QLAM 后端"""
        mem = HierarchicalMemory(use_rust=False, use_quantum=False)
        assert mem._quantum is None