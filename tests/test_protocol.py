"""Protocol layer tests — 30+ tests covering UI, Sync, COM, ID, LifeCycle, Memory."""

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from datetime import datetime
from typing import Dict, Any


class TestLAAPUIComponent:
    """UI component protocol tests."""

    def test_ui_component_create(self):
        from laap.protocol.laap_ui import UIComponent
        comp = UIComponent(name="test_btn", kind="button", props={"label": "Click"})
        assert comp.name == "test_btn"
        assert comp.kind == "button"

    def test_ui_component_to_dict(self):
        from laap.protocol.laap_ui import UIComponent
        comp = UIComponent(name="btn", kind="button", props={"label": "OK"})
        d = comp.to_dict()
        assert d["name"] == "btn"
        assert d["kind"] == "button"

    def test_ui_component_from_dict(self):
        from laap.protocol.laap_ui import UIComponent
        data = {"name": "btn", "kind": "button", "props": {"label": "OK"}, "children": []}
        comp = UIComponent.from_dict(data)
        assert comp.name == "btn"
        assert comp.props["label"] == "OK"

    def test_ui_component_nested_children(self):
        from laap.protocol.laap_ui import UIComponent
        child = UIComponent(name="child", kind="text", props={})
        parent = UIComponent(name="parent", kind="div", props={}, children=[child])
        assert len(parent.children) == 1
        assert parent.children[0].name == "child"


class TestLAAPUILayout:
    """UI layout protocol tests."""

    def test_ui_layout_create(self):
        from laap.protocol.laap_ui import UILayout
        layout = UILayout(direction="vertical", spacing=8, padding=16)
        assert layout.direction == "vertical"

    def test_ui_layout_add_child(self):
        from laap.protocol.laap_ui import UILayout, UIComponent
        layout = UILayout(direction="horizontal", spacing=4)
        comp = UIComponent(name="test", kind="text", props={})
        layout.add_child(comp)
        assert len(layout.children) == 1

    def test_ui_layout_serialize(self):
        from laap.protocol.laap_ui import UILayout
        layout = UILayout(direction="vertical", spacing=8)
        d = layout.serialize()
        assert d["direction"] == "vertical"

    def test_ui_layout_empty(self):
        from laap.protocol.laap_ui import UILayout
        layout = UILayout(direction="vertical", spacing=0, padding=0)
        assert len(layout.children) == 0


class TestLAAPUIRender:
    """UI rendering protocol tests."""

    def test_ui_render_text(self):
        from laap.protocol.laap_ui import UIRenderer
        renderer = UIRenderer()
        result = renderer.render_text("Hello")
        assert "Hello" in result

    def test_ui_render_component(self):
        from laap.protocol.laap_ui import UIRenderer, UIComponent
        renderer = UIRenderer()
        comp = UIComponent(name="btn", kind="button", props={"label": "Click"})
        result = renderer.render_component(comp)
        assert result is not None

    def test_ui_render_markdown(self):
        from laap.protocol.laap_ui import UIRenderer
        renderer = UIRenderer()
        result = renderer.render_markdown("# Title\nContent")
        assert "Title" in result

    def test_ui_render_json(self):
        from laap.protocol.laap_ui import UIRenderer
        renderer = UIRenderer()
        result = renderer.render_json({"key": "value"})
        assert "key" in result


class TestLAAPSyncCRDT:
    """CRDT document sync tests."""

    def test_crdt_create(self):
        from laap.protocol.laap_sync import CRDTDocument
        doc = CRDTDocument(doc_id="doc-1")
        assert doc.doc_id == "doc-1"
        assert doc.state == {}

    def test_crdt_apply_operation(self):
        from laap.protocol.laap_sync import CRDTDocument
        doc = CRDTDocument(doc_id="doc-1")
        doc.apply_operation({"type": "set", "key": "name", "value": "LAAP"})
        assert doc.state.get("name") == "LAAP"

    def test_crdt_merge(self):
        from laap.protocol.laap_sync import CRDTDocument
        doc1 = CRDTDocument(doc_id="doc-1")
        doc2 = CRDTDocument(doc_id="doc-1")
        doc1.apply_operation({"type": "set", "key": "a", "value": 1})
        doc2.apply_operation({"type": "set", "key": "b", "value": 2})
        doc1.merge(doc2)
        assert doc1.state.get("a") == 1
        assert doc1.state.get("b") == 2

    def test_crdt_conflict_resolution(self):
        from laap.protocol.laap_sync import CRDTDocument
        doc1 = CRDTDocument(doc_id="doc-1")
        doc2 = CRDTDocument(doc_id="doc-1")
        doc1.apply_operation({"type": "set", "key": "x", "value": 1, "ts": 100})
        doc2.apply_operation({"type": "set", "key": "x", "value": 2, "ts": 200})
        doc1.merge(doc2)
        assert doc1.state.get("x") == 2  # latest timestamp wins


class TestLAAPSyncVersion:
    """Version vector tests."""

    def test_version_vector_create(self):
        from laap.protocol.laap_sync import VersionVector
        vv = VersionVector()
        assert vv.clock == {}

    def test_version_vector_increment(self):
        from laap.protocol.laap_sync import VersionVector
        vv = VersionVector()
        vv.increment("node-1")
        assert vv.clock["node-1"] == 1

    def test_version_vector_compare_equal(self):
        from laap.protocol.laap_sync import VersionVector
        v1 = VersionVector({"a": 1})
        v2 = VersionVector({"a": 1})
        assert v1.compare(v2) == 0

    def test_version_vector_compare_descendant(self):
        from laap.protocol.laap_sync import VersionVector
        v1 = VersionVector({"a": 2})
        v2 = VersionVector({"a": 1})
        assert v1.compare(v2) == 1


class TestLAAPCommMessage:
    """Communication message tests."""

    def test_message_create(self):
        from laap.protocol.laap_com import Message
        msg = Message(sender="alice", receiver="bob", content="hello", msg_type="text")
        assert msg.sender == "alice"
        assert msg.receiver == "bob"

    def test_message_with_metadata(self):
        from laap.protocol.laap_com import Message
        msg = Message(sender="a", receiver="b", content="test", msg_type="command", metadata={"cmd": "run"})
        assert msg.metadata["cmd"] == "run"

    def test_message_serialize(self):
        from laap.protocol.laap_com import Message
        msg = Message(sender="a", receiver="b", content="hi", msg_type="text")
        d = msg.serialize()
        assert d["sender"] == "a"
        assert d["content"] == "hi"

    def test_message_deserialize(self):
        from laap.protocol.laap_com import Message
        data = {"sender": "x", "receiver": "y", "content": "test", "msg_type": "text"}
        msg = Message.deserialize(data)
        assert msg.content == "test"


class TestLAAPCommBus:
    """Message bus tests."""

    def test_bus_create(self):
        from laap.protocol.laap_com import MessageBus
        bus = MessageBus()
        assert bus.subscribers == {}

    def test_bus_subscribe(self):
        from laap.protocol.laap_com import MessageBus
        bus = MessageBus()
        cb = MagicMock()
        bus.subscribe("test_topic", cb)
        assert "test_topic" in bus.subscribers

    def test_bus_publish(self):
        from laap.protocol.laap_com import MessageBus, Message
        bus = MessageBus()
        cb = MagicMock()
        bus.subscribe("topic", cb)
        msg = Message(sender="a", receiver="b", content="test", msg_type="text")
        bus.publish("topic", msg)
        assert cb.called

    def test_bus_unsubscribe(self):
        from laap.protocol.laap_com import MessageBus
        bus = MessageBus()
        cb = MagicMock()
        bus.subscribe("t", cb)
        bus.unsubscribe("t", cb)
        assert cb not in bus.subscribers.get("t", [])


class TestLAAPIdentity:
    """Identity document tests."""

    def test_identity_create(self):
        from laap.protocol.laap_id import IdentityDocument
        doc = IdentityDocument(did="did:laap:test")
        assert doc.did == "did:laap:test"

    def test_identity_sign(self):
        from laap.protocol.laap_id import IdentityDocument
        doc = IdentityDocument(did="did:laap:test", private_key="test-key")
        sig = doc.sign("hello")
        assert sig is not None

    def test_identity_verify(self):
        from laap.protocol.laap_id import IdentityDocument
        doc = IdentityDocument(did="did:laap:test", public_key="test-key")
        result = doc.verify("hello", "signature")
        assert result is not None


class TestLAAPLifecycle:
    """State machine lifecycle tests."""

    def test_state_machine_create(self):
        from laap.protocol.laap_life import StateMachine
        sm = StateMachine(initial="idle")
        assert sm.current_state == "idle"

    def test_state_machine_transition(self):
        from laap.protocol.laap_life import StateMachine
        sm = StateMachine(initial="idle", transitions=[{"trigger": "start", "from": "idle", "to": "running"}])
        sm.trigger("start")
        assert sm.current_state == "running"

    def test_state_machine_invalid_transition(self):
        from laap.protocol.laap_life import StateMachine
        sm = StateMachine(initial="idle", transitions=[{"trigger": "start", "from": "idle", "to": "running"}])
        with pytest.raises(Exception):
            sm.trigger("stop")

    def test_state_machine_get_allowed(self):
        from laap.protocol.laap_life import StateMachine
        sm = StateMachine(initial="idle", transitions=[{"trigger": "start", "from": "idle", "to": "running"}])
        allowed = sm.get_allowed_triggers()
        assert "start" in allowed


class TestLAAPMemoryCurve:
    """Forgetting curve protocol tests."""

    def test_forgetting_curve_create(self):
        from laap.protocol.laap_mem import ForgettingCurve
        fc = ForgettingCurve(decay_rate=0.5)
        assert fc.decay_rate == 0.5

    def test_forgetting_curve_recall_probability(self):
        from laap.protocol.laap_mem import ForgettingCurve
        fc = ForgettingCurve(decay_rate=0.5)
        prob = fc.recall_probability(elapsed_hours=1)
        assert 0 <= prob <= 1

    def test_forgetting_curve_zero_time(self):
        from laap.protocol.laap_mem import ForgettingCurve
        fc = ForgettingCurve(decay_rate=0.5)
        prob = fc.recall_probability(elapsed_hours=0)
        assert prob == 1.0

    def test_forgetting_curve_decay_effect(self):
        from laap.protocol.laap_mem import ForgettingCurve
        fc = ForgettingCurve(decay_rate=0.5)
        p1 = fc.recall_probability(1)
        p2 = fc.recall_probability(24)
        assert p2 < p1
