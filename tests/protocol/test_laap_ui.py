"""Tests for LAAP-UI protocol"""
from laap.protocol.laap_ui import *

def test_component_creation():
    comp = Component(id="test", type=ComponentType.TEXT, props={"content": "Hello"})
    assert comp.id == "test"
    assert comp.props["content"] == "Hello"

def test_layout_tree():
    tree = LayoutTree()
    root = Component(id="root", type=ComponentType.CONTAINER)
    tree.set_root(root)
    assert tree.get_root().id == "root"

def test_render_command():
    cmd = RenderCommand(type=RenderOp.UPDATE, component_id="test", props={"content": "new"})
    assert cmd.type == RenderOp.UPDATE

def test_component_factory():
    factory = ComponentFactory()
    btn = factory.create_button("Click Me", "action1")
    assert btn.props["label"] == "Click Me"

def test_theme_definition():
    theme = ThemeDefinition(name="test", colors={"primary": "#FF0000"})
    theme_dict = theme.to_dict()
    assert theme_dict["name"] == "test"
