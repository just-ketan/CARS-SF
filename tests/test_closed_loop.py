"""The closed loop: QoS violation monitor, RL trigger, safety gate, semantic state and the
5G transport enforcement commands. Behaviour on the live 5G stack is validated by
experiments/validate_32.py; these tests pin down the decision logic."""

import sys
from pathlib import Path

import numpy as np
import pytest

from core.controller import SliceController
from monitoring.qos_monitor import CLEAR_TICKS, PERSIST_TICKS, QoSViolationMonitor, load_thresholds
from scheduler.semantic import SEMANTIC_OBS_DIM, build_semantic_observation
from slicing.safety import accept_learned

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "deployment" / "5g"))

SERVICES = ("healthcare", "education", "agriculture", "general")
DISASTER = {"healthcare": 90.0, "education": 5.0, "agriculture": 5.0, "general": 20.0}


def _snap(loss=0.0, rtt=10.0, service="healthcare", jitter=None):
    return {"slice_qos": {s: {"loss_pct": loss if s == service else 0.0, "queue_delay_ms": 0.0,
                              "delivered_mbps": 10.0} for s in SERVICES},
            "service_rtt_ms": {s: rtt if s == service else 10.0 for s in SERVICES},
            "service_jitter_ms": {s: jitter for s in SERVICES}}


# --------------------------------------------------------------------- thresholds


def test_thresholds_cover_every_class_and_scenario():
    table = load_thresholds()
    evaluated = ("normal", "school", "harvest", "disaster", "medical_emergency", "fiber_cut",
                 "backhaul_degradation", "core_switch_failure")
    assert sum(len(table[s]) for s in evaluated) == 32
    assert table["disaster"]["healthcare"]["latency_ms"] == 40 < table["normal"]["healthcare"]["latency_ms"]


def test_a_threshold_override_can_never_relax_the_baseline(tmp_path, monkeypatch):
    import monitoring.qos_monitor as m
    real = m.load_yaml
    monkeypatch.setattr(m, "load_yaml", lambda name: {"overrides": {"disaster": {"healthcare": {"loss_pct": 9.0}}}}
                        if name == "qos_thresholds.yaml" else real(name))
    with pytest.raises(ValueError, match="relaxes"):
        load_thresholds()


# ------------------------------------------------- transient vs persistent violations


def test_short_breach_is_transient_and_never_persistent():
    monitor = QoSViolationMonitor()
    for tick in range(1, PERSIST_TICKS):
        status = monitor.observe(tick, _snap(loss=5.0), "normal")
    assert status["healthcare"]["status"] == "transient" and monitor.persistent() == set()
    monitor.observe(PERSIST_TICKS, _snap(), "normal")
    assert monitor.episodes[0]["persistent"] is False


def test_sustained_breach_becomes_persistent_and_needs_clean_ticks_to_end():
    monitor = QoSViolationMonitor()
    for tick in range(1, PERSIST_TICKS + 1):
        monitor.observe(tick, _snap(loss=5.0), "normal")
    assert monitor.persistent() == {"healthcare"}
    for offset in range(1, CLEAR_TICKS):
        monitor.observe(PERSIST_TICKS + offset, _snap(), "normal")
        assert monitor.persistent() == {"healthcare"}       # one good tick does not end it
    monitor.observe(PERSIST_TICKS + CLEAR_TICKS, _snap(), "normal")
    assert monitor.persistent() == set()
    assert monitor.summary()["persistent_episodes"] == 1 and monitor.episodes[0]["metrics"] == ["loss"]


def test_latency_jitter_and_throughput_are_all_detected():
    monitor = QoSViolationMonitor()
    assert monitor.observe(1, _snap(rtt=200.0), "normal")["healthcare"]["breaches"] == ["latency"]
    assert "jitter" in monitor.observe(2, _snap(jitter=100.0), "normal")["healthcare"]["breaches"]
    starved = monitor.observe(3, _snap(), "normal", demand={"healthcare": 100.0})
    assert "throughput" in starved["healthcare"]["breaches"]


def test_scenario_threshold_applies():
    monitor = QoSViolationMonitor()
    assert monitor.observe(1, _snap(rtt=90.0), "normal")["healthcare"]["status"] == "ok"
    assert monitor.observe(2, _snap(rtt=90.0), "disaster")["healthcare"]["breaches"] == ["latency"]


def test_tcp_throughput_is_not_a_violation_because_tcp_adapts():
    monitor = QoSViolationMonitor(elastic={"general"})
    snap = _snap()
    assert "throughput" not in monitor.observe(1, snap, "normal", demand={"general": 100.0})["general"]["breaches"]


# ------------------------------------------------------------------ the RL trigger


class Spy:
    kind, available = "residual", True
    state_version = "v2"

    def __init__(self):
        self.calls, self.learned = 0, []

    def residual(self, context, obs):
        self.calls += 1
        return [0.2, 0.0, -0.2, 0.0]

    def learn(self, context, action, reward):
        self.learned.append(reward)


@pytest.fixture
def loop(monkeypatch):
    import core.controller as cm
    spy, original = Spy(), cm.make_policy
    monkeypatch.setattr(cm, "make_policy", lambda n: spy if n == "closed_loop" else original(n))
    controller = SliceController("closed_loop", capacity=100.0, control_interval_ticks=5)
    controller.start("disaster", DISASTER)
    return controller, spy


def _run(controller, ticks, start=1, **snap):
    for tick in range(start, start + ticks):
        controller.observe_reward(50.0)
        controller.step(tick, _snap(**snap), {"context": "disaster"}, prior_demand=DISASTER)


def test_rl_is_not_consulted_while_qos_is_met(loop):
    controller, spy = loop
    _run(controller, 12)
    assert spy.calls == 0 and not controller.rl_active


def test_persistent_violation_triggers_rl_and_recovery_hands_back(loop):
    controller, spy = loop
    _run(controller, PERSIST_TICKS, loss=5.0)
    assert controller.rl_active and spy.calls >= 1
    assert any(h["reason"].startswith("sla risk: persistent violation") for h in controller.history)
    _run(controller, CLEAR_TICKS + 1, start=PERSIST_TICKS + 1)
    assert not controller.rl_active
    assert any("rules resume" in h["reason"] for h in controller.history)


def test_later_measurements_score_whether_the_adaptation_helped(loop):
    controller, _ = loop
    _run(controller, PERSIST_TICKS, loss=5.0)
    _run(controller, controller.ADAPTATION_WINDOW_TICKS + 1, start=PERSIST_TICKS + 1)
    record = controller.adaptations[0]
    assert record["violating"] == ["healthcare"] and record["improved"] is True and record["restored"] is True


def test_only_rl_decisions_reach_the_learner(loop):
    controller, spy = loop
    _run(controller, 12)                                    # rules only
    assert spy.learned == []
    _run(controller, 12, start=13, loss=5.0)
    assert spy.learned                                       # verified RL transitions only


def test_closed_loop_policy_learns_the_offset_not_the_ppo_action(tmp_path):
    from scheduler.agent import ClosedLoopResidualPolicy

    policy = ClosedLoopResidualPolicy(path=str(tmp_path / "online.json"))

    class Model:
        @staticmethod
        def predict(obs, deterministic=True):
            return np.array([0.5, 0.0, 0.0, 0.0]), None

    policy.model = Model()
    actions = [policy.residual("disaster", None) for _ in range(4)]
    for i, action in enumerate(actions):
        policy.learn("disaster", [round(a, 4) for a in action], float(i))
    context = policy.state["disaster"]
    assert context["updates"] == 1 and abs(np.mean(context["mean"])) < 0.5     # offsets, centred on 0


# ---------------------------------------------------------------------- safety gate


BASE = {"uplink": {"healthcare": 80.0, "education": 1.0, "agriculture": 18.0, "general": 1.0}}
TAKE_AG = {"uplink": {"healthcare": 90.0, "education": 1.0, "agriculture": 8.0, "general": 1.0}}
TAKE_HC = {"uplink": {"healthcare": 70.0, "education": 1.0, "agriculture": 28.0, "general": 1.0}}
PRIORITY = {"healthcare": 10, "education": 2, "agriculture": 1, "general": 1}


def test_rebalancing_toward_a_more_critical_violating_slice_is_allowed():
    assert accept_learned(TAKE_AG, BASE, 100, None, {"healthcare", "agriculture"}, set(), priorities=PRIORITY)[0]


def test_capacity_is_never_taken_from_a_more_critical_violating_slice():
    assert not accept_learned(TAKE_HC, BASE, 100, None, {"healthcare", "agriculture"}, set(), priorities=PRIORITY)[0]


# -------------------------------------------------------------------- semantic state


def test_semantic_state_has_no_scenario_identity_and_describes_the_situation():
    demand = {"uplink": {"healthcare": 90}, "downlink": {"general": 20}}
    alloc = {"uplink": {"healthcare": 90}, "downlink": {"general": 20}}
    slas = {s: 1.0 for s in SERVICES}
    obs = build_semantic_observation({"healthcare": 10, "education": 2, "agriculture": 1, "general": 1}, "priority",
                                     True, True, demand, alloc, {}, {"healthcare"}, 100, slas, slas, 0.8)
    assert obs.shape == (SEMANTIC_OBS_DIM,)
    assert obs[0] == 1.0 and obs[1] == pytest.approx(0.2) and tuple(obs[4:7]) == (1.0, 1.0, 1.0)
    assert obs[23] == 1.0 and obs[-1] == pytest.approx(0.8)


@pytest.mark.parametrize("state", ["v2", "semantic"])
def test_simulator_covers_all_eight_scenarios_and_ignores_actions_without_a_violation(state):
    from scheduler.env_dir import EVALUATED_SCENARIOS, DirectionalSlicingEnv

    env = DirectionalSlicingEnv(state=state, triggered=True, include_failures=True, seed=3)
    assert set(env.contexts) == set(EVALUATED_SCENARIOS) and len(env.contexts) == 8
    allocations = []
    for action in (np.zeros(4), np.ones(4)):             # QoS met: the action has no effect
        env.reset(seed=1, options={"context": "normal"})
        allocations.append(env.step(action)[4]["allocation"])
    assert allocations[0] == allocations[1]


# ------------------------------------------------------------- 5G transport commands


class Recorder:
    def __init__(self, name):
        self.name, self.commands = name, []

    def cmd(self, command):
        self.commands.append(command)
        return "__rc=0" if "__rc" in command else ""


class FakeNet:
    def __init__(self):
        self.nodes = {}

    def get(self, name):
        return self.nodes.setdefault(name, Recorder(name))


class FakeTopo:
    n3_cell = "eth9"


def _qos(classification="host"):
    from stack5g import Transport5GQoS
    qos = Transport5GQoS(FakeNet(), FakeTopo(), classification=classification)
    qos.setup_htb(100)
    return qos


def test_uplink_filters_match_the_inner_header_inside_gtp():
    from stack5g import INNER_SRC_AT
    cell = _qos().net.get("cell_site").commands
    slice_rule = [c for c in cell if "0x0a3c0000 0xffffff00" in c and "flowid 1:10" in c]
    assert INNER_SRC_AT == 56 and any(f"at {INNER_SRC_AT}" in c and "dport 2152" in c for c in slice_rule)
    assert any("stab overhead -44" in c for c in cell)              # user-plane accounting


def test_slicenet_mode_has_no_address_rules_for_data_only_for_probes():
    from stack5g import ICMP_PRIO, SLICE_PRIO
    commands = _qos("slicenet_all").net.get("cell_site").commands
    assert not any(f"prio {SLICE_PRIO} " in c for c in commands)
    assert any(f"prio {ICMP_PRIO} " in c for c in commands)


def test_a_flow_is_steered_at_both_points_and_can_be_reclassified():
    qos = _qos("slicenet_all")
    flow = ("10.61.0.2", "10.85.0.100", 6, 40000, 5005)
    assert qos.classify_flow(flow, "education") is True
    assert qos.flow_rules[flow] == "education"
    cell, upf = qos.net.get("cell_site").commands, qos.net.get("upf_tap").commands
    assert "0x9c40138d" in cell[-1] and "flower src_ip 10.85.0.100 dst_ip 10.61.0.2" in upf[-1]
    assert qos.classify_flow(flow, "general", replace=True) is True
    assert "tc filter del" in cell[-1] and "tc filter replace" in upf[-1]
