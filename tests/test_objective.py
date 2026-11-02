"""Tests required by the "close the research objective" mandate (steps 3, 4, 6, 7).

Context-aware allocation, capacity-aware QoS allocation across load regimes, the safety
validator and safe RL hybrid, the learning-disabled control, OVS queue read-back and the
repeated-failure injector. Network-level effects are evaluated in the final matrix; these
tests pin down the decision logic.
"""

import itertools

import numpy as np
import pytest

from core.controller import SliceController
from slicing.allocators import QoSAwareAllocator
from slicing.safety import accept_learned, validate
from tests.test_qos import FakeNet, KernelNet

SERVICES = ("healthcare", "education", "agriculture", "general")
NORMAL = {"healthcare": 20.0, "education": 20.0, "agriculture": 20.0, "general": 20.0}
DISASTER = {"healthcare": 90.0, "education": 5.0, "agriculture": 5.0, "general": 20.0}


def _plan(scheduler, context, demand, capacity=100.0):
    controller = SliceController(scheduler, capacity=capacity)
    controller.start(context, demand)
    return controller


# ---------------------------------------------------------------- step 3: context


def test_same_observation_different_relevant_context_gives_different_valid_decision():
    """Overloaded uplink: who gets the scarce capacity depends on the context's policy."""
    overload = {"healthcare": 70.0, "education": 10.0, "agriculture": 60.0, "general": 10.0}
    harvest, disaster = _plan("qos_aware", "harvest", overload), _plan("qos_aware", "disaster", overload)
    up_h, up_d = harvest.directional_allocation["uplink"], disaster.directional_allocation["uplink"]
    assert up_d["healthcare"] > up_h["healthcare"] and up_h["agriculture"] > up_d["agriculture"]
    for c in (harvest, disaster):
        assert validate(c.directional_allocation, 100.0, c._planned_protected) == []


def test_irrelevant_context_change_causes_no_reconfiguration():
    """When every SLA target fits, switching context must not move any rate."""
    a = _plan("qos_aware", "normal", NORMAL).directional_allocation
    b = _plan("qos_aware", "school", NORMAL).directional_allocation
    assert a == b


def test_clock_change_without_context_change_does_not_replan():
    controller = SliceController("qos_adaptive", capacity=100.0, control_interval_ticks=50)
    controller.start("normal", NORMAL)
    for tick in range(1, 6):
        controller.step(tick, {}, {"context": "normal", "clock": f"10:0{tick}"}, prior_demand=NORMAL)
    assert len(controller.history) == 1


@pytest.mark.parametrize("context", ["normal", "school", "harvest", "disaster", "medical_emergency", "fiber_cut"])
def test_context_never_breaks_capacity_or_safety(context):
    rng = np.random.default_rng(7)
    for _ in range(25):
        demand = {s: float(v) for s, v in zip(SERVICES, rng.uniform(0, 120, 4))}
        controller = _plan("qos_adaptive", context, demand)
        assert validate(controller.directional_allocation, 100.0, controller._planned_protected) == []


def test_context_blind_controller_ignores_context():
    blind = SliceController("qos_blind", capacity=100.0)
    assert blind.context_blind and not blind.context_aware
    blind.start("normal", NORMAL)
    before = blind.directional_allocation
    blind.plan("disaster", DISASTER, directional_demands=None)
    assert blind._planned_info["uplink"]["policy"] == "proportional"     # normal's policy, not disaster's
    assert before is not None


# ---------------------------------------------------------- step 4: capacity-aware QoS


def _alloc(capacity, demand, priorities=None, policy="priority", headroom=None):
    allocator = QoSAwareAllocator()
    allocator.policy = policy
    if headroom:
        allocator.headroom.update(headroom)
    priorities = priorities or {"healthcare": 10, "education": 1, "agriculture": 1, "general": 1}
    return allocator, allocator.allocate(capacity, priorities, demand)


@pytest.mark.parametrize("load", [0.2, 0.6, 0.85])
def test_feasible_low_and_high_load_meet_every_target(load):
    demand = {s: 100 * load / 4 / 1.1 for s in SERVICES}
    allocator, alloc = _alloc(100, demand)
    assert allocator.regime == "sla_feasible"
    assert all(alloc[s] >= demand[s] * 1.1 - 0.01 for s in SERVICES)


def test_capacity_boundary_keeps_every_mean_demand():
    demand = {"healthcare": 90, "education": 0, "agriculture": 5, "general": 0}
    for policy in ("priority", "proportional"):
        allocator, alloc = _alloc(100, demand, policy=policy)
        assert allocator.regime == "mean_feasible"
        assert alloc["healthcare"] >= 90 and alloc["agriculture"] >= 5
        assert abs(sum(alloc.values()) - 100) < 0.05


def test_sustained_overload_degrades_explicitly_without_starvation():
    demand = {"healthcare": 0, "education": 80, "agriculture": 0, "general": 50}
    for policy in ("priority", "proportional"):
        allocator, alloc = _alloc(50, demand, priorities={"healthcare": 5, "education": 5, "agriculture": 2,
                                                          "general": 1}, policy=policy)
        assert allocator.regime == "overload" and set(allocator.degraded) == {"education", "general"}
        assert alloc["general"] >= 0.2 * 50 - 0.01 and alloc["education"] >= 0.2 * 80 - 0.01
        assert allocator.audit["policy"] == policy


def test_proportional_policy_shares_the_shortfall_equally():
    demand = {"healthcare": 0, "education": 80, "agriculture": 0, "general": 50}
    _, alloc = _alloc(50, demand, priorities={"healthcare": 5, "education": 5, "agriculture": 2, "general": 1},
                      policy="proportional")
    assert abs(alloc["education"] / 80 - alloc["general"] / 50) < 0.03


def test_sudden_burst_raises_headroom_through_the_loss_loop():
    controller = _plan("qos_aware", "disaster", DISASTER)
    before = controller.allocator.headroom["healthcare"]
    for _ in range(5):
        controller._observe_qos({"slice_qos": {"healthcare": {"loss_pct": 6.0}}})
    controller._adapt_headroom()
    assert controller.allocator.headroom["healthcare"] > before


def test_asymmetric_congestion_is_handled_per_direction():
    demand = {"healthcare": 40.0, "education": 120.0, "agriculture": 10.0, "general": 30.0}
    controller = _plan("qos_aware", "school", demand)
    info = controller._planned_info
    assert info["uplink"]["regime"] == "sla_feasible" and info["downlink"]["regime"] == "overload"


def test_emergency_transition_switches_policy_and_stays_safe():
    controller = SliceController("qos_adaptive", capacity=100.0, control_interval_ticks=50)
    controller.start("normal", NORMAL)
    controller.step(1, {}, {"context": "disaster"}, prior_demand=DISASTER)
    assert controller._planned_info["uplink"]["policy"] == "priority"
    assert validate(controller._planned_directional, 100.0, controller._planned_protected) == []


def test_misleading_low_tcp_estimate_does_not_starve():
    controller = _plan("qos_aware", "school", {"healthcare": 5.0, "education": 80.0, "agriculture": 10.0,
                                                "general": 50.0}, capacity=50.0)
    misleading = {"uplink": {s: 0.0 for s in SERVICES},
                  "downlink": {"healthcare": 0.0, "education": 80.0, "agriculture": 0.0, "general": 0.5}}
    controller.plan("school", {}, directional_demands=misleading)
    assert controller._planned_directional["downlink"]["general"] >= 0.2 * 50 - 0.01


def test_stale_telemetry_is_not_read_as_zero_demand():
    from slicing.demand_estimator import MeasuredDemandEstimator
    est = MeasuredDemandEstimator(prior=DISASTER)
    est.observe({"telemetry_health": {"services_without_counters": ["healthcare"]}}, {}, None)
    assert est.estimate_directional()["uplink"]["healthcare"] == pytest.approx(90.0)


def test_small_changes_do_not_reconfigure():
    class Counting:
        def __init__(self):
            self.calls = 0

        def apply_allocation(self, allocation, **kw):
            self.calls += 1
            return {"verified": True, "failures": [], "mismatches": []}

    qos = Counting()
    # oracle demand: the plan inputs are identical every interval, isolating the hysteresis
    controller = SliceController("qos_aware", capacity=100.0, qos=qos, control_interval_ticks=1, demand_mode="oracle")
    controller.start("normal", NORMAL)
    for tick in range(1, 8):
        controller.step(tick, {}, {"context": "normal"}, prior_demand=NORMAL)
    assert qos.calls == 0                  # identical plans: nothing re-applied


def test_invalid_plan_is_never_actuated():
    assert validate({"uplink": {"healthcare": 80, "general": 30}}, 100) != []
    assert validate({"uplink": {"healthcare": float("nan")}}, 100) != []
    assert validate({"uplink": {"general": 2.0}}, 100, {"uplink": {"general": 10.0}}) != []


# --------------------------------------------------------------- step 6: safe hybrid RL


def test_safe_hybrid_rejects_proposals_that_hurt_at_risk_slices_or_move_too_much():
    heuristic = {"uplink": {"healthcare": 90, "education": 1, "agriculture": 8, "general": 1}}
    protected = {"uplink": {"healthcare": 18, "education": 0.5, "agriculture": 1, "general": 0.5}}
    small = {"uplink": {"healthcare": 92, "education": 1, "agriculture": 6, "general": 1}}
    takes_from_risk = {"uplink": {"healthcare": 92, "education": 1, "agriculture": 6, "general": 1}}
    big = {"uplink": {"healthcare": 60, "education": 1, "agriculture": 38, "general": 1}}
    assert accept_learned(small, heuristic, 100, protected, set(), set())[0]
    assert not accept_learned(takes_from_risk, heuristic, 100, protected, {"agriculture"}, set())[0]
    assert not accept_learned(big, heuristic, 100, protected, set(), set())[0]


def test_safe_hybrid_scheduler_falls_back_to_the_heuristic(monkeypatch):
    import core.controller as cm

    class Wild:
        kind, available = "residual", True

        def residual(self, context, obs):
            return [-1.0, 1.0, 1.0, 1.0]

    original = cm.make_policy
    monkeypatch.setattr(cm, "make_policy", lambda n: Wild() if n == "ppo_residual" else original(n))
    hybrid = SliceController("rl_residual_safe", capacity=100.0)
    hybrid.start("disaster", DISASTER)
    heuristic = SliceController("qos_adaptive", capacity=100.0)
    heuristic.start("disaster", DISASTER)
    assert hybrid.hybrid_stats["rejected"] == 1
    assert hybrid.directional_allocation == heuristic.directional_allocation


def test_learning_disabled_control_explores_but_never_updates(tmp_path):
    from scheduler.agent import OnlineResidualCEM
    frozen = OnlineResidualCEM(path=str(tmp_path / "x.json"), learning=False)
    for r in range(8):
        frozen.learn("disaster", frozen.residual("disaster", None), float(r))
    assert frozen.state["disaster"]["updates"] == 0 and frozen.samples_this_run == 8
    frozen.save()
    assert not (tmp_path / "x.json").exists()


def test_reward_weights_are_configurable():
    from scheduler.reward import SliceOutcome, compute_reward
    outcome = {"healthcare": SliceOutcome(10, 10, 80.0, 0.0, 10)}
    base, _ = compute_reward(outcome, {"healthcare": 1}, {"healthcare": 50}, 100)
    heavy, _ = compute_reward(outcome, {"healthcare": 1}, {"healthcare": 50}, 100, reward_weights={"sla": 20.0})
    assert heavy == pytest.approx(base - 10.0)


# ------------------------------------------------------- step 7: actuation and faults


class OvsSwitch:
    """Fake switch that stores OVS queue other-config like ovsdb and reports exit codes."""

    def __init__(self, name):
        self.name, self.commands, self.queues = name, [], {}

    def cmd(self, command):
        import re
        self.commands.append(command)
        if command.startswith("ovs-vsctl get queue"):
            q = re.search(r"queues:(\d+)", command).group(1)
            rate, ceil = self.queues.get(q, (None, None))
            return f'{{max-rate="{ceil}", min-rate="{rate}"}}' if rate else "{}"
        m = re.search(r"queues:(\d+)\) other-config:min-rate=(\d+) other-config:max-rate=(\d+)", command)
        if m:
            self.queues[m.group(1)] = (m.group(2), m.group(3))
        return "__rc=0" if "__rc" in command else ""


class OvsNet(FakeNet):
    def __init__(self):
        self.switches = {n: OvsSwitch(n) for n in ("s_rural", "s_edge")}


def test_ovs_backend_applies_per_direction_and_reads_queues_back():
    from slicing.qos_enforcer import QoSEnforcer
    qos = QoSEnforcer(net=OvsNet(), backend="ovs")
    qos.setup_htb(100)
    directional = {"uplink": {"healthcare": 90, "education": 1, "agriculture": 8, "general": 1},
                   "downlink": {"healthcare": 1, "education": 30, "agriculture": 1, "general": 68}}
    result = qos.apply_allocation({}, directional=directional)
    assert result["verified"] is True and not result["mismatches"]
    assert qos.net.get("s_rural").queues["1"][0] == str(90_000_000)
    assert qos.net.get("s_edge").queues["4"][0] == str(68_000_000)


def test_repeated_fiber_cut_injects_and_repairs_twice():
    from self_healing.injector import FaultInjector

    class LinkNet:
        def __init__(self):
            self.commands = []

        def get(self, name):
            net = self

            class S:
                def cmd(self, c):
                    net.commands.append(c)
                    return ""
            return S()

    net = LinkNet()
    injector = FaultInjector(net, spec={"type": "repeated_fiber_cut", "cycles": [[0.1, 0.3], [0.6, 0.8]]},
                             duration=20)
    for tick in range(1, 21):
        injector.evaluate_scenario({"tick": tick})
    events = [e["event"] for e in injector.events]
    assert events == ["fiber_cut", "repair", "fiber_cut", "repair"]
