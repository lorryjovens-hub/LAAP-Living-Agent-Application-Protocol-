"""Tests for LAAP Event Bus"""
import pytest
from laap.events.bus import EventBus, Event


class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("test.event", handler)
        bus.publish_simple("test.event", {"key": "value"})
        assert len(received) == 1
        assert received[0].data["key"] == "value"

    def test_wildcard_subscriber(self):
        bus = EventBus()
        received = []

        def wildcard_handler(event):
            received.append(event.type)

        bus.subscribe("*", wildcard_handler)
        bus.publish_simple("event.a")
        bus.publish_simple("event.b")
        assert len(received) == 2

    def test_unsubscribe(self):
        bus = EventBus()

        def handler(event):
            pass

        bus.subscribe("test", handler)
        bus.unsubscribe("test", handler)
        history = bus.history("test")
        assert history == []

    def test_event_history(self):
        bus = EventBus()
        bus.publish_simple("hist.test")
        bus.publish_simple("hist.test")
        history = bus.history("hist.test")
        assert len(history) == 2

    def test_clear_history(self):
        bus = EventBus()
        bus.publish_simple("test.clear")
        bus.clear_history()
        assert len(bus.history()) == 0

    def test_status(self):
        bus = EventBus()
        bus.publish_simple("test.status")
        status = bus.status
        assert status["total_events"] >= 1
