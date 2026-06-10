"""Tests for UI components"""
from laap.engine.render.components import *
from laap.engine.render.tui_renderer import *

def test_component_factory():
    btn = ComponentFactory.button("Submit", "submit_form")
    assert btn.type == ComponentType.BUTTON
    assert btn.props["label"] == "Submit"

def test_tui_render():
    renderer = TUIRenderer()
    text = ComponentFactory.text("Hello World")
    output = renderer.render(text)
    assert "Hello World" in output
