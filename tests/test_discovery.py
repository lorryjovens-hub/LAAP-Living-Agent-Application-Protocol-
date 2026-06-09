"""Tests for LAAP Model Discovery Engine"""
import pytest
from laap.llm.discovery import ModelDiscovery, DiscoveredModel, DiscoveryResult


class TestDiscoveredModel:
    def test_create(self):
        m = DiscoveredModel(id="gpt-5.4", provider="openai")
        assert m.id == "gpt-5.4"
        assert m.provider == "openai"
        assert not m.verified

    def test_to_dict(self):
        m = DiscoveredModel(id="test-model", provider="test", verified=True)
        d = m.to_dict()
        assert d["id"] == "test-model"
        assert d["verified"]

    def test_with_aliases(self):
        m = DiscoveredModel(id="claude-opus-4-8", provider="anthropic", aliases=["claude-opus-latest"])
        assert len(m.aliases) == 1


class TestDiscoveryResult:
    def test_empty(self):
        r = DiscoveryResult(provider="test", total_found=0, models=[], new_models=[], errors=[], duration_ms=0.0)
        assert r.provider == "test"
        assert r.total_found == 0
        assert r.new_models == []

    def test_with_models(self):
        models = [
            DiscoveredModel(id="model-a", provider="test", verified=True),
            DiscoveredModel(id="model-b", provider="test", verified=False),
        ]
        r = DiscoveryResult(
            provider="test", total_found=2, models=models,
            new_models=["model-a", "model-b"], errors=[], duration_ms=100.0,
        )
        assert r.total_found == 2
        assert len(r.new_models) == 2


class TestModelDiscovery:
    def test_init(self):
        d = ModelDiscovery()
        assert d.total_discovered == 0
        assert d.cached_providers == []

    def test_clear_cache(self):
        d = ModelDiscovery()
        d.clear_cache()
        assert d.cached_providers == []

    def test_provider_endpoints(self):
        d = ModelDiscovery()
        assert "openai" in d.MODELS_ENDPOINT_PROVIDERS
        assert "anthropic" in d.STATIC_PROVIDERS

    def test_discover_static_provider(self):
        d = ModelDiscovery()
        result = d.discover_provider("anthropic")
        assert result.total_found == 0
        assert len(result.errors) > 0  # Static provider, no API endpoint

    def test_ping_unknown_model(self):
        d = ModelDiscovery()
        success, msg = d.ping_model("nonexistent-model-xyz")
        assert not success
        assert "Unknown" in msg

    def test_status(self):
        d = ModelDiscovery()
        status = d.status()
        assert "cached_providers" in status
        assert "total_discovered" in status
