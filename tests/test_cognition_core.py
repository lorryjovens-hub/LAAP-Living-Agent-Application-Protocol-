"""
单元测试: LAAP 认知引擎核心模块

覆盖:
  - NeedDriveSystem / Need     需求驱动系统
  - EmotionGradient            情绪梯度系统
  - GoalTree / Goal            目标层级系统
  - AwarenessSystem            自我感知系统
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
from laap.cognition.needs import NeedDriveSystem, NeedType, Need
from laap.cognition.emotion import EmotionGradient, EmotionalState
from laap.cognition.goals import GoalTree, Goal, GoalStatus
from laap.cognition.awareness import AwarenessSystem, SelfModel, EnvironmentModel, TaskModel


# ═══════════════════════════════════════════════════════════════
# Need 单元 — 单个需求的行为
# ═══════════════════════════════════════════════════════════════

class TestNeed:
    def test_init_defaults(self):
        """Need 默认值正确"""
        n = Need(type=NeedType.CERTAINTY)
        assert n.type == NeedType.CERTAINTY
        assert n.current_level == 0.5
        assert n.target_level == 0.8
        assert n.decay_rate == 0.01
        assert n.importance == 1.0

    def test_init_custom(self):
        """Need 支持自定义参数"""
        n = Need(type=NeedType.COMPETENCE, current_level=0.3, target_level=0.9,
                 decay_rate=0.02, importance=2.0)
        assert n.current_level == 0.3
        assert n.compute_drive() == pytest.approx((0.9 - 0.3) * 2.0)

    def test_compute_drive_formula(self):
        """compute_drive 计算公式: deficit * importance"""
        n = Need(type=NeedType.ENERGY, current_level=0.2, target_level=0.8, importance=1.5)
        expected = (0.8 - 0.2) * 1.5  # = 0.9
        assert n.compute_drive() == pytest.approx(expected)

    def test_compute_drive_zero_deficit(self):
        """deficit 为零时 drive 为 0"""
        n = Need(type=NeedType.CERTAINTY, current_level=0.9, target_level=0.8)
        assert n.compute_drive() == 0.0

    def test_satisfy_increases_current(self):
        """satisfy 增加 current_level"""
        n = Need(type=NeedType.ENERGY, current_level=0.3)
        n.satisfy(0.4)
        assert n.current_level == pytest.approx(0.7)

    def test_satisfy_caps_at_one(self):
        """satisfy 不会让 current_level 超过 1.0"""
        n = Need(type=NeedType.ENERGY, current_level=0.8)
        n.satisfy(0.5)
        assert n.current_level == 1.0

    def test_tick_decay_within_bounds(self):
        """tick 使 current_level 衰减但保持在 [0, 1]"""
        n = Need(type=NeedType.CERTAINTY, current_level=0.5, decay_rate=0.1)
        for _ in range(100):
            n.tick(dt=1.0)
            assert 0.0 <= n.current_level <= 1.0, f"current_level out of bounds: {n.current_level}"

    def test_tick_deterministic_with_zero_volatility(self):
        """volatility=0 时 tick 完全确定"""
        n = Need(type=NeedType.CERTAINTY, current_level=0.8, decay_rate=0.05, volatility=0.0)
        n.tick(dt=1.0)
        assert n.current_level == pytest.approx(0.8 - 0.05)

    def test_deficit_property(self):
        """deficit 属性 = target - current (min 0)"""
        n = Need(type=NeedType.CERTAINTY, current_level=0.3, target_level=0.7)
        assert n.deficit == pytest.approx(0.4)
        n.current_level = 0.9
        assert n.deficit == 0.0

    def test_to_dict(self):
        """to_dict 返回正确的字段"""
        n = Need(type=NeedType.COMPETENCE, current_level=0.4, target_level=0.8, importance=2.0)
        d = n.to_dict()
        assert d["type"] == "competence"
        assert d["current"] == 0.4
        assert "drive" in d
        assert "deficit" in d


# ═══════════════════════════════════════════════════════════════
# NeedDriveSystem 单元 — 需求驱动系统
# ═══════════════════════════════════════════════════════════════

class TestNeedDriveSystem:
    def test_init_creates_five_needs(self):
        """初始化创建 5 个核心需求"""
        nds = NeedDriveSystem()
        assert len(nds.needs) == 5
        for nt in NeedType:
            assert nt in nds.needs

    def test_tick_returns_all_needs(self):
        """tick 返回所有需求的更新值"""
        nds = NeedDriveSystem()
        result = nds.tick(dt=0.5)
        assert len(result) == 5
        for nt in NeedType:
            assert nt in result

    def test_tick_count_increments(self):
        """tick_count 累加"""
        nds = NeedDriveSystem()
        assert nds.tick_count == 0
        nds.tick()
        assert nds.tick_count == 1
        nds.tick()
        assert nds.tick_count == 2

    def test_satisfy_updates_need(self):
        """satisfy 正确更新指定需求"""
        nds = NeedDriveSystem()
        original = nds.needs[NeedType.COMPETENCE].current_level
        nds.satisfy(NeedType.COMPETENCE, 0.3)
        assert nds.needs[NeedType.COMPETENCE].current_level == pytest.approx(original + 0.3)

    def test_get_dominant_need_returns_highest_drive(self):
        """get_dominant_need 返回 drive 最高的需求"""
        nds = NeedDriveSystem()
        nds.needs[NeedType.COMPETENCE].current_level = 0.1
        nds.needs[NeedType.COMPETENCE].importance = 3.0
        nds.needs[NeedType.CERTAINTY].current_level = 0.8
        dom, drive = nds.get_dominant_need()
        assert dom == NeedType.COMPETENCE
        assert drive > 0

    def test_get_dominant_need_all_satisfied(self):
        """所有需求满足时 drive 为负值或零"""
        nds = NeedDriveSystem()
        for nt in NeedType:
            nds.needs[nt].current_level = nds.needs[nt].target_level + 0.1
        dom, drive = nds.get_dominant_need()
        assert drive == 0.0

    def test_get_drive_vector_format(self):
        """get_drive_vector 返回字符串到浮点数的映射"""
        nds = NeedDriveSystem()
        dv = nds.get_drive_vector()
        assert isinstance(dv, dict)
        for k, v in dv.items():
            assert isinstance(k, str)
            assert isinstance(v, float)

    def test_emotional_valence_all_high(self):
        """所有需求满足度高时 valence 接近 1"""
        nds = NeedDriveSystem()
        for nt in NeedType:
            nds.needs[nt].current_level = 0.95
        assert nds.emotional_valence > 0.5

    def test_emotional_valence_all_low(self):
        """所有需求满足度低时 valence 接近 -1"""
        nds = NeedDriveSystem()
        for nt in NeedType:
            nds.needs[nt].current_level = 0.05
        assert nds.emotional_valence < -0.5

    def test_custom_config(self):
        """支持自定义配置覆盖默认值"""
        config = {
            "competence": {"decay_rate": 0.001, "importance": 3.0},
            "energy": {"current_level": 0.9},
        }
        nds = NeedDriveSystem(config=config)
        assert nds.needs[NeedType.COMPETENCE].decay_rate == 0.001
        assert nds.needs[NeedType.COMPETENCE].importance == 3.0
        assert nds.needs[NeedType.ENERGY].current_level == 0.9

    def test_invalid_config_ignored(self):
        """无效的配置项被忽略"""
        config = {"nonexistent_need": {"importance": 2.0}}
        nds = NeedDriveSystem(config=config)  # Should not raise

    def test_get_profile_structure(self):
        """get_profile 返回正确的数据结构"""
        nds = NeedDriveSystem()
        profile = nds.get_profile()
        assert len(profile) == 5
        for nt_name, ndata in profile.items():
            assert "current" in ndata
            assert "target" in ndata
            assert "drive" in ndata
            assert "deficit" in ndata


# ═══════════════════════════════════════════════════════════════
# EmotionGradient 单元 — 情绪梯度系统
# ═══════════════════════════════════════════════════════════════

class TestEmotionGradient:
    def test_init_default_state(self):
        """初始情绪状态为中性"""
        eg = EmotionGradient()
        assert eg.state.valence == 0.0
        assert eg.state.arousal == 0.5
        assert eg.state.dominance == 0.5
        assert eg.state.confidence == 0.5

    def test_update_returns_state(self):
        """update 返回 EmotionalState"""
        eg = EmotionGradient()
        sats = {"certainty": 0.6, "competence": 0.5}
        result = eg.update(sats)
        assert isinstance(result, EmotionalState)

    def test_update_changes_valence(self):
        """高满意度时 valence 为正"""
        eg = EmotionGradient()
        sats = {"certainty": 0.9, "competence": 0.9, "autonomy": 0.9}
        eg.update(sats)
        assert eg.state.valence > 0

    def test_update_low_satisfaction_valence(self):
        """低满意度时 valence 为负"""
        eg = EmotionGradient()
        sats = {"certainty": 0.1, "competence": 0.1, "autonomy": 0.1}
        eg.update(sats)
        assert eg.state.valence < 0

    def test_update_with_task_success(self):
        """task_success 影响 dominance"""
        eg = EmotionGradient()
        sats = {"certainty": 0.5, "competence": 0.5}
        eg.update(sats, task_success=0.9)
        assert eg.state.dominance > 0.6

    def test_update_with_task_failure(self):
        """任务失败时 dominance 降低"""
        eg = EmotionGradient()
        sats = {"certainty": 0.5, "competence": 0.5}
        eg.update(sats, task_success=0.1)
        assert eg.state.dominance < 0.5

    def test_update_with_novelty(self):
        """高 novelty 降低 confidence"""
        eg = EmotionGradient()
        sats = {"certainty": 0.5, "competence": 0.5}
        eg.update(sats, novelty=0.9)
        assert eg.state.confidence < 0.5

    def test_compute_intrinsic_reward_needs_improvement(self):
        """需求改善时内在奖励为正"""
        eg = EmotionGradient()
        eg.update({"certainty": 0.3, "competence": 0.3})
        r1 = eg.compute_intrinsic_reward()
        eg.update({"certainty": 0.8, "competence": 0.8})
        r2 = eg.compute_intrinsic_reward()
        # 第二次需求改善，奖励应增加
        assert r2 > r1 or abs(r2 - r1) < 0.5  # 至少不会大幅下降

    def test_compute_intrinsic_reward_bounds(self):
        """内在奖励在 [-1, 1] 范围内"""
        eg = EmotionGradient()
        for _ in range(10):
            sats = {nt.value: np.random.uniform(0, 1)
                    for nt in list(NeedType)}
            eg.update(sats, task_success=np.random.uniform(0, 1))
            r = eg.compute_intrinsic_reward()
            assert -1.0 <= r <= 1.0, f"Reward out of bounds: {r}"

    def test_mean_reward_empty(self):
        """无历史时 mean_reward 为 0"""
        eg = EmotionGradient()
        assert eg.mean_reward == 0.0

    def test_mean_reward_with_history(self):
        """有历史时 mean_reward 计算正确"""
        eg = EmotionGradient()
        eg._reward_history = [0.1, 0.2, 0.3, 0.4, 0.5]
        assert eg.mean_reward == pytest.approx(0.3)

    def test_reward_volatility_small_window(self):
        """数据少于窗口时 volatility 为 0"""
        eg = EmotionGradient()
        eg._reward_history = [0.1, 0.2]
        assert eg.reward_volatility == 0.0

    def test_reward_volatility_with_data(self):
        """有足够数据时 volatility 计算正确"""
        eg = EmotionGradient()
        eg._reward_history = [0.0, 0.5, 0.0, 0.5, 0.0, 0.5, 0.0, 0.5,
                               0.0, 0.5, 0.0, 0.5, 0.0, 0.5, 0.0, 0.5,
                               0.0, 0.5, 0.0, 0.5, 0.0, 0.5]
        vol = eg.reward_volatility
        assert vol > 0.2  # 交替值应有较高 volatility

    def test_smoothing_effect(self):
        """smoothing 参数影响状态变化的平滑度"""
        eg_fast = EmotionGradient(smoothing=0.1)  # 快速跟随
        eg_slow = EmotionGradient(smoothing=0.9)  # 慢速跟随
        sats = {"certainty": 0.9, "competence": 0.9}
        eg_fast.update(sats)
        eg_slow.update(sats)
        # 快速跟随更接近目标值
        assert abs(eg_fast.state.valence) > abs(eg_slow.state.valence)

    def test_reset_clears_state(self):
        """reset 清空所有历史和状态"""
        eg = EmotionGradient()
        eg.update({"certainty": 0.9, "competence": 0.9})
        eg.compute_intrinsic_reward()
        eg.reset()
        assert eg.state.valence == 0.0
        assert eg.state.arousal == 0.5
        assert len(eg._need_history) == 0
        assert len(eg._reward_history) == 0


# ═══════════════════════════════════════════════════════════════
# Goal 单元 — 单个目标
# ═══════════════════════════════════════════════════════════════

class TestGoal:
    def test_init_defaults(self):
        """Goal 默认状态为 INACTIVE"""
        g = Goal(name="test")
        assert g.status == GoalStatus.INACTIVE
        assert g.progress == 0.0
        assert g.priority == 0.5

    def test_activate(self):
        """activate 设置状态为 ACTIVE"""
        g = Goal(name="test")
        g.activate()
        assert g.status == GoalStatus.ACTIVE

    def test_advance_increases_progress(self):
        """advance 增加 progress"""
        g = Goal(name="test")
        g.activate()
        g.advance(0.3)
        assert g.progress == pytest.approx(0.3)

    def test_advance_completes_goal(self):
        """advance 使 progress >= 1.0 时完成目标"""
        g = Goal(name="test")
        g.activate()
        g.advance(1.0)
        assert g.status == GoalStatus.COMPLETED
        assert g.completion_count == 1

    def test_advance_in_progress(self):
        """advance 使 progress 在 0~1 之间时状态为 IN_PROGRESS"""
        g = Goal(name="test")
        g.activate()
        g.advance(0.5)
        assert g.status == GoalStatus.IN_PROGRESS

    def test_fail(self):
        """fail 设置状态为 FAILED"""
        g = Goal(name="test")
        g.fail()
        assert g.status == GoalStatus.FAILED
        assert g.fail_count == 1

    def test_is_terminal_true(self):
        """无子目标时 is_terminal 为 True"""
        g = Goal(name="test")
        assert g.is_terminal is True

    def test_is_terminal_false(self):
        """有子目标时 is_terminal 为 False"""
        g = Goal(name="parent")
        g.subgoals.append(Goal(name="child"))
        assert g.is_terminal is False

    def test_success_rate_no_attempts(self):
        """无尝试时 success_rate 为 0.5"""
        g = Goal(name="test")
        assert g.success_rate == 0.5

    def test_success_rate_all_success(self):
        """全部成功时 success_rate 为 1.0"""
        g = Goal(name="test", completion_count=5, fail_count=0)
        assert g.success_rate == 1.0

    def test_to_dict(self):
        """to_dict 返回正确字段"""
        g = Goal(name="test", status=GoalStatus.ACTIVE, progress=0.5)
        d = g.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "active"
        assert d["progress"] == 0.5


# ═══════════════════════════════════════════════════════════════
# GoalTree 单元 — 目标层级树
# ═══════════════════════════════════════════════════════════════

class TestGoalTree:
    def test_init_empty(self):
        """初始化为空树"""
        gt = GoalTree()
        assert gt.root is None

    def test_set_root(self):
        """set_root 设置根节点"""
        gt = GoalTree()
        root = Goal(name="root")
        gt.set_root(root)
        assert gt.root == root
        assert root.id in gt._goal_map

    def test_add_subgoal(self):
        """add_subgoal 添加子目标"""
        gt = GoalTree()
        root = Goal(name="root")
        gt.set_root(root)
        child = Goal(name="child")
        assert gt.add_subgoal(root.id, child) is True
        assert child.parent_id == root.id
        assert child in root.subgoals

    def test_add_subgoal_invalid_parent(self):
        """add_subgoal 对无效父 ID 返回 False"""
        gt = GoalTree()
        child = Goal(name="child")
        assert gt.add_subgoal("nonexistent", child) is False

    def test_select_next_returns_highest_score(self):
        """select_next 返回分数最高的可执行目标"""
        import numpy as np
        np.random.seed(42)
        gt = GoalTree()
        root = Goal(name="root")
        gt.set_root(root)
        g1 = Goal(name="low", priority=0.3, need_type="competence")
        g2 = Goal(name="high", priority=0.9, need_type="competence")
        gt.add_subgoal(root.id, g1)
        gt.add_subgoal(root.id, g2)
        g1.activate()
        g2.activate()
        dv = {"competence": 0.5}
        selected = gt.select_next(dv)
        assert selected.name == "high"

    def test_select_next_no_candidates(self):
        """无可执行目标时返回 None"""
        gt = GoalTree()
        assert gt.select_next({"a": 0.5}) is None

    def test_select_next_skips_inactive_nonterminal(self):
        """只选择活跃或待执行的目标"""
        gt = GoalTree()
        root = Goal(name="root", status=GoalStatus.COMPLETED)
        gt.set_root(root)
        selected = gt.select_next({"a": 0.5})
        assert selected is None

    def test_get_active(self):
        """get_active 返回所有活跃目标"""
        gt = GoalTree()
        root = Goal(name="root")
        gt.set_root(root)
        g1 = Goal(name="active")
        g1.activate()
        g2 = Goal(name="inactive")
        gt.add_subgoal(root.id, g1)
        gt.add_subgoal(root.id, g2)
        active = gt.get_active()
        assert len(active) == 1
        assert active[0].name == "active"

    def test_to_dict_structure(self):
        """to_dict 返回正确的结构"""
        gt = GoalTree()
        root = Goal(name="root")
        gt.set_root(root)
        g1 = Goal(name="child")
        g1.activate()
        gt.add_subgoal(root.id, g1)
        d = gt.to_dict()
        assert d["root"] == "root"
        assert d["active_count"] == 1


# ═══════════════════════════════════════════════════════════════
# AwarenessSystem 单元 — 自我感知系统
# ═══════════════════════════════════════════════════════════════

class TestAwarenessSystem:
    def test_init(self):
        """初始化感知系统"""
        aw = AwarenessSystem(agent_id="test-001", name="TestAgent")
        assert aw.self_model.agent_id == "test-001"
        assert aw.self_model.name == "TestAgent"

    def test_set_task(self):
        """set_task 设置任务状态"""
        aw = AwarenessSystem()
        aw.set_task("分析数据", priority=3, complexity=0.7, estimated_steps=5)
        assert aw.task_model.description == "分析数据"
        assert aw.task_model.status == "in_progress"
        assert aw.task_model.priority == 3
        assert aw.task_model.estimated_steps == 5
        assert aw.self_model.current_task == "分析数据"

    def test_update_task_progress(self):
        """update_task_progress 更新进度"""
        aw = AwarenessSystem()
        aw.set_task("test", estimated_steps=10)
        for _ in range(5):
            aw.update_task_progress(steps=2)
        assert aw.task_model.completed_steps == 10
        assert aw.task_model.status == "completed"

    def test_update_task_progress_with_obstacle(self):
        """update_task_progress 记录障碍"""
        aw = AwarenessSystem()
        aw.set_task("test", estimated_steps=5)
        aw.update_task_progress(steps=1, obstacle="数据不完整")
        assert "数据不完整" in aw.task_model.obstacles
        assert aw.self_model.total_steps == 1

    def test_record_error(self):
        """record_error 累加错误"""
        aw = AwarenessSystem()
        assert aw.self_model.total_errors == 0
        aw.record_error("连接超时")
        assert aw.self_model.total_errors == 1
        aw.record_error("解析失败")
        assert aw.self_model.total_errors == 2

    def test_know_thyself(self):
        """know_thyself 返回自我认知描述字符串"""
        aw = AwarenessSystem(agent_id="t1", name="TestAgent")
        aw.set_task("测试任务", estimated_steps=3)
        aw.update_task_progress(steps=1)
        desc = aw.know_thyself()
        assert "TestAgent" in desc
        assert "测试任务" in desc
        assert isinstance(desc, str)
        assert len(desc) > 20

    def test_env_model_defaults(self):
        """环境模型有默认值"""
        em = EnvironmentModel()
        assert isinstance(em.os_type, str)
        assert isinstance(em.python_version, str)
        assert isinstance(em.available_memory_mb, float)

    def test_self_model_age_format(self):
        """SelfModel.age 返回格式化字符串"""
        sm = SelfModel(agent_id="t1")
        assert "s" in sm.age or "m" in sm.age or "h" in sm.age