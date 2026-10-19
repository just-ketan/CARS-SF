"""Demand estimation, allocators, priority engine and the slice controller."""

import pytest

from core.controller import SliceController, scheduler_spec
from self_healing.engine import apply_constraints
from slicing.allocators import DemandAwareAllocator, TgppAllocator, make_allocator
from slicing.demand_estimator import HoltForecaster, MeasuredDemandEstimator
from slicing.priority_engine import PriorityEngine

SERVICES = ("healthcare", "education", "agriculture", "general")


def test_holt_tracks_trend():
    f = HoltForecaster()
    for v in (10, 12, 14, 16, 18):
        f.update(v)
    assert 19 < f.forecast(1) < 22


def test_estimator_probes_up_saturated_elastic_slices():
    est = MeasuredDemandEstimator(prior={s: 10 for s in SERVICES})
    snap = {"interval_s": 1.0, "service_throughput_mbps": {"education": 19.5, "general": 2.0}}
    for _ in range(5):
        est.observe(snap, {"education": 20, "general": 20, "healthcare": 5, "agriculture": 5})
    demand = est.estimate()
    assert demand["education"] > 20          # running at its cap → demand may be higher
    assert demand["general"] == pytest.approx(2.0, abs=0.5)


def test_demand_aware_respects_floors_capacity_and_demand():
    alloc = DemandAwareAllocator({"healthcare": 5, "education": 2, "agriculture": 1, "general": 1})
    result = alloc.allocate(100, {"healthcare": 10, "education": 1, "agriculture": 1, "general": 1},
                            {"healthcare": 150, "education": 40, "agriculture": 10, "general": 30})
    assert sum(result.values()) <= 100.01
    assert all(result[s] >= f for s, f in {"education": 2, "agriculture": 1, "general": 1}.items())
    under = alloc.allocate(100, {s: 1 for s in SERVICES}, {s: 10 for s in SERVICES})
    assert under == {s: 10 for s in SERVICES}


def test_baseline_allocators():
    assert make_allocator("static_equal").allocate(100, {}, {}) == {s: 25.0 for s in SERVICES}
    assert TgppAllocator().allocate(100, {}, {}) == {"URLLC": 20.0, "eMBB": 70.0, "mMTC": 10.0}
    assert make_allocator("none").allocate(100, {}, {}) == {}
    prop = make_allocator("proportional").allocate(100, {"healthcare": 3, "education": 1, "agriculture": 0.5, "general": 0.5}, {})
    assert prop["healthcare"] == 60.0


def test_priority_engine_applies_policy_multipliers():
    engine = PriorityEngine(policy=lambda ctx, state: {"general": 4.0})
    weights = engine.priorities("normal")
    assert weights["general"] == 4.0 and weights["healthcare"] == 5
    assert sum(engine.allocate_bandwidth(100).values()) == pytest.approx(100, abs=0.05)


def test_scheduler_registry_and_aliases():
    assert scheduler_spec("rule")["name"] == "proposed"
    assert scheduler_spec("rl")["name"] == "rl_cem"
    with pytest.raises(ValueError):
        scheduler_spec("nonexistent")


class FakeQoS:
    def __init__(self):
        self.applied = []

    def apply_allocation(self, allocation):
        self.applied.append(allocation)


def test_controller_warmup_interval_and_change_threshold():
    qos = FakeQoS()
    prior = {"healthcare": 20, "education": 20, "agriculture": 20, "general": 20}
    ctl = SliceController("proposed", 100, qos=qos, control_interval_ticks=5)
    ctl.start("normal", prior)
    ramp = {"interval_s": 1.0, "service_throughput_mbps": {s: 1.0 for s in SERVICES}}
    assert ctl.step(1, ramp, {"context": "normal"}, {"state": "normal", "boosts": {}}, prior) is None
    assert qos.applied == []                     # warm-up: no re-plan from a ramping sample
    steady = {"interval_s": 1.0, "service_throughput_mbps": {"healthcare": 5, "education": 40, "agriculture": 5, "general": 40}}
    for t in range(2, 11):
        ctl.step(t, steady, {"context": "normal"}, {"state": "normal", "boosts": {}}, prior)
    assert qos.applied, "measured demand should eventually change the allocation"
    assert qos.applied[-1]["education"] > 20


def test_static_scheduler_never_replans():
    qos = FakeQoS()
    ctl = SliceController("static_equal", 100, qos=qos)
    ctl.start("disaster", {s: 50 for s in SERVICES})
    for t in range(1, 20):
        ctl.step(t, {}, {"context": "school"}, None, {s: 50 for s in SERVICES})
    assert qos.applied == []


def test_healing_constraints_cap_core_and_lend_to_edge():
    locations = {"healthcare": "edge", "agriculture": "edge", "education": "core", "general": "core"}
    alloc = {"healthcare": 30, "education": 30, "agriculture": 10, "general": 30}
    demand = {"healthcare": 60, "education": 40, "agriculture": 20, "general": 40}
    capped = apply_constraints(alloc, demand, 100, {"locations": locations, "core_capacity_mbps": 40})
    assert capped["education"] + capped["general"] <= 40.01
    assert capped["healthcare"] > 30
    down = apply_constraints(alloc, demand, 100, {"locations": locations, "core_down": True},
                             {"education": 2, "general": 1})
    assert down["education"] == 2 and down["general"] == 1
