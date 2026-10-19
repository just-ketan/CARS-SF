"""Context changes slicing decisions, and the context-unaware baseline does not see it."""

from core.controller import SliceController

DEMAND = {"healthcare": 60.0, "education": 40.0, "agriculture": 20.0, "general": 40.0}


def test_context_changes_priorities_and_allocation():
    controller = SliceController("proposed", capacity=100.0)
    normal, p_normal = controller.plan("normal", DEMAND)
    disaster, p_disaster = controller.plan("disaster", DEMAND)
    assert p_normal != p_disaster and normal != disaster
    assert disaster["healthcare"] > normal["healthcare"]
    assert abs(sum(disaster.values()) - 100.0) < 0.05          # capacity respected


def test_context_unaware_baseline_ignores_context():
    unaware = SliceController("context_unaware", capacity=100.0)
    assert not unaware.context_aware
    assert unaware.plan("disaster", DEMAND) == unaware.plan("normal", DEMAND)
    assert unaware.plan("normal", DEMAND) == SliceController("proposed", capacity=100.0).plan("normal", DEMAND)
