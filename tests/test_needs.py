
import sys; sys.path.insert(0, "D:/LAAP")
from laap.cognition.needs import NeedDriveSystem, NeedType, Need
def test_need_init():
    n = Need(type=NeedType.CERTAINTY, current_level=0.5)
    assert n.type == NeedType.CERTAINTY
def test_need_drive():
    n = Need(type=NeedType.COMPETENCE, current_level=0.3, target_level=0.8, importance=2.0)
    assert abs(n.compute_drive() - 1.0) < 0.01
def test_need_satisfy():
    n = Need(type=NeedType.ENERGY, current_level=0.3)
    n.satisfy(0.4); assert n.current_level == 0.7
    n.satisfy(0.5); assert n.current_level == 1.0
def test_drive_system():
    nds = NeedDriveSystem()
    assert len(nds.needs) == 5
    assert len(nds.tick()) == 5
def test_dominant():
    nds = NeedDriveSystem()
    nds.needs[NeedType.COMPETENCE].current_level = 0.1
    nds.needs[NeedType.COMPETENCE].importance = 2.0
    dom, _ = nds.get_dominant_need()
    assert dom == NeedType.COMPETENCE
def test_valence():
    nds = NeedDriveSystem()
    for nt in NeedType: nds.needs[nt].current_level = 0.9
    assert nds.emotional_valence > 0.5
