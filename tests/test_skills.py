"""Skills system tests — 5+ test functions covering hub, market, template."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestSkillHub:
    """Skill hub tests."""

    def test_hub_create(self):
        from laap.skills.hub import SkillHub
        hub = SkillHub()
        assert hub.skills == {}

    def test_hub_register_skill(self):
        from laap.skills.hub import SkillHub
        hub = SkillHub()
        skill = MagicMock()
        skill.name = "test_skill"
        hub.register(skill)
        assert "test_skill" in hub.skills

    def test_hub_get_skill(self):
        from laap.skills.hub import SkillHub
        hub = SkillHub()
        skill = MagicMock()
        skill.name = "my_skill"
        hub.register(skill)
        result = hub.get("my_skill")
        assert result is skill

    def test_hub_list_skills(self):
        from laap.skills.hub import SkillHub
        hub = SkillHub()
        s1 = MagicMock(); s1.name = "skill_a"
        s2 = MagicMock(); s2.name = "skill_b"
        hub.register(s1)
        hub.register(s2)
        names = hub.list_skills()
        assert "skill_a" in names
        assert "skill_b" in names


class TestSkillMarket:
    """Skill marketplace tests."""

    def test_market_create(self):
        from laap.skills.hub import SkillMarket
        market = SkillMarket()
        assert market is not None

    def test_market_browse(self):
        from laap.skills.hub import SkillMarket
        market = SkillMarket()
        items = market.browse()
        assert isinstance(items, list)


class TestSkillTemplate:
    """Skill template tests."""

    def test_template_create(self):
        from laap.skills.template import SkillTemplate
        template = SkillTemplate(name="greeter", description="A greeting skill")
        assert template.name == "greeter"

    def test_template_instantiate(self):
        from laap.skills.template import SkillTemplate
        template = SkillTemplate(name="greeter", description="A greeting skill")
        skill = template.instantiate(config={"language": "en"})
        assert skill is not None
        assert skill.name == "greeter"
