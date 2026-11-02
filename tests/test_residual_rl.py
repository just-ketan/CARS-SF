"""Module D: state v2, residual action, direction-aware simulator, live residual policies."""

import numpy as np
import pytest

from core.controller import SliceController
from scheduler.env_dir import DirectionalSlicingEnv, serve_direction
from scheduler.residual import OBS_DIM, apply_residual, build_observation

FLOORS = {"healthcare": 5, "education": 2, "agriculture": 1, "general": 1}
ALLOC = {"uplink": {"healthcare": 94, "education": 0.5, "agriculture": 5, "general": 0.5},
         "downlink": {"healthcare": 0.5, "education": 20, "agriculture": 0.5, "general": 79}}
DISASTER = {"healthcare": 90.0, "education": 5.0, "agriculture": 5.0, "general": 20.0}


@pytest.mark.parametrize("action", [[0, 0, 0, 0], [1, -1, 1, -1], [-1, 1, -1, 1], [0.3, 0.2, -0.7, 1]])
def test_residual_keeps_floors_and_capacity(action):
    out = apply_residual(ALLOC, action, 100, FLOORS)
    for direction, rates in out.items():
        assert sum(rates.values()) <= 100.0 + 0.05
        assert all(rates[s] >= min(FLOORS[s], ALLOC[direction][s]) - 1e-6 for s in rates)


def test_zero_residual_is_the_heuristic():
    assert apply_residual(ALLOC, [0, 0, 0, 0], 100, FLOORS) == ALLOC


def test_state_v2_layout_and_scaling():
    obs = build_observation("disaster", ALLOC, ALLOC, {"healthcare": {"loss_pct": 2.0, "queue_delay_ms": 25.0}},
                            True, 100, {"healthcare": 1.0, "education": 2.0, "agriculture": 2.0, "general": 5.0},
                            {"healthcare": 50, "education": 150, "agriculture": 250, "general": 500})
    assert obs.shape == (OBS_DIM,)
    k = OBS_DIM - 17
    assert obs[k + 8] == pytest.approx(2.0 / 5)         # loss / SLA = 2 → 2/5
    assert obs[k + 12] == pytest.approx(0.5 / 2)        # queue / SLA delay = 0.5 → 0.25
    assert obs[k + 16] == 1.0 and obs[:k].sum() == 1.0


def test_tcp_backs_off_while_udp_overflow_is_loss():
    rng = np.random.default_rng(0)
    demand = np.array([20.0, 20.0, 0, 0])
    alloc = np.array([10.0, 10.0, 40.0, 40.0])
    elastic = np.array([False, True, False, False])
    offered, delivered, dropped, _, _ = serve_direction(rng, demand, alloc, [0, 1, 2, 3], np.zeros(4), np.zeros(4),
                                                        np.full(4, 0.1), 20.0, 1.0, 10, elastic)
    assert dropped[0] > 0 and dropped[1] == 0          # UDP drops; TCP does not
    assert offered[1] < 20.0                           # TCP curtailed its sending instead


def test_simulator_step_uses_the_shared_reward_and_state():
    env = DirectionalSlicingEnv()
    obs, _ = env.reset(seed=3, options={"context": "disaster"})
    assert obs.shape == (OBS_DIM,)
    obs2, reward, _, _, info = env.step(np.zeros(4))
    assert np.isfinite(reward) and set(info["terms"]) >= {"satisfaction", "sla", "loss", "starvation"}
    assert abs(sum(info["allocation"]["uplink"].values()) - 100) < 0.1


class FixedResidual:
    kind, available = "residual", True

    def __init__(self, action):
        self.action, self.seen = action, []

    def residual(self, context, obs):
        self.seen.append(obs)
        return list(self.action)


def test_live_controller_applies_residual_and_logs_v2_transitions(monkeypatch):
    import core.controller as controller_module

    policy = FixedResidual([0.0, 0.0, 1.0, 0.0])
    original = controller_module.make_policy
    monkeypatch.setattr(controller_module, "make_policy",
                        lambda name: policy if name == "ppo_residual" else original(name))
    controller = SliceController("rl_residual", capacity=100.0, control_interval_ticks=2)
    controller.start("disaster", DISASTER)
    heuristic = SliceController("qos_adaptive", capacity=100.0)
    heuristic.start("disaster", DISASTER)
    assert controller.directional_allocation["uplink"]["agriculture"] > \
        heuristic.directional_allocation["uplink"]["agriculture"]
    ctx = {"context": "disaster"}
    for tick in (1, 2, 3, 4):
        controller.observe_reward(80.0)
        controller.step(tick, {"slice_qos": {"healthcare": {"loss_pct": 0.5, "queue_delay_ms": 3.0}}}, ctx,
                        prior_demand=DISASTER)
    controller.finish(4, {}, "disaster")
    records = controller.transitions.records
    assert len(records) >= 2 and all(len(r["obs"]) == OBS_DIM and r["action"] == [0.0, 0.0, 1.0, 0.0]
                                     for r in records)
    assert records[0]["next_obs"] == records[1]["obs"]
    assert policy.seen[1][OBS_DIM - 17 + 8] == pytest.approx(0.5 / 5)    # window loss / SLA in the observation


def test_online_residual_cem_starts_at_the_heuristic(tmp_path):
    from scheduler.agent import OnlineResidualCEM

    policy = OnlineResidualCEM(path=str(tmp_path / "res.json"), init_std=0.0, min_std=0.0)
    assert policy.residual("disaster", None) == [0.0, 0.0, 0.0, 0.0]
    for reward in (1.0, 2.0, 3.0, 4.0):
        policy.learn("disaster", [0.1 * reward] * 4, reward)
    assert policy.state["disaster"]["updates"] == 1
    assert policy.state["disaster"]["mean"][0] == pytest.approx(0.35)


def test_residual_cannot_breach_the_starvation_guard():
    """Evaluation v3 defect: rl_residual cut best-effort TCP to its plain floor (SLA 0.04)."""
    alloc = {"uplink": {"healthcare": 0.5, "education": 0.5, "agriculture": 0.5, "general": 0.5},
             "downlink": {"healthcare": 0.5, "education": 39.0, "agriculture": 0.5, "general": 10.0}}
    protected = {"uplink": {}, "downlink": {"general": 10.0}}
    out = apply_residual(alloc, [0, 1, 0, -1], 50, FLOORS, protected)
    assert out["downlink"]["general"] >= 10.0 - 1e-6


def test_live_residual_respects_allocator_protection(monkeypatch):
    import core.controller as controller_module

    policy = FixedResidual([0.0, 1.0, 0.0, -1.0])               # push education up, general down
    original = controller_module.make_policy
    monkeypatch.setattr(controller_module, "make_policy",
                        lambda name: policy if name == "ppo_residual" else original(name))
    controller = SliceController("rl_residual", capacity=50.0)
    controller.start("school", {"healthcare": 5.0, "education": 80.0, "agriculture": 10.0, "general": 50.0})
    controller._pending_obs = np.zeros(OBS_DIM)
    controller.plan("school", {"healthcare": 5.0, "education": 80.0, "agriculture": 10.0, "general": 50.0})
    assert controller._planned_directional["downlink"]["general"] >= 0.2 * 50 - 0.01
