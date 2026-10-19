"""Live RL transitions: decision → enforcement → reward → next observation, and online CEM."""

import numpy as np

from core.controller import SliceController
from scheduler.agent import OnlineCEMPolicy
from scheduler.transitions import TransitionLog, action_from_multipliers

DEMAND = {"healthcare": 30.0, "education": 40.0, "agriculture": 20.0, "general": 40.0}


class VerifyingQos:
    """Unit-test double for the enforcer: records each allocation and reports it verified."""

    def __init__(self, verified=True):
        self.applied, self.verified = [], verified

    def apply_allocation(self, allocation, ceilings=None):
        self.applied.append(dict(allocation))
        return {"allocation": allocation, "failures": [], "mismatches": [], "verified": self.verified}


def _drive(controller, ticks, rewards):
    snapshot = {"queue_bytes": {"education": 20_000}, "service_throughput_mbps": {}}
    context = {"context": "school"}
    for tick in range(1, ticks + 1):
        controller.observe_reward(rewards(tick))     # interval that just ended, as the orchestrator does
        controller.step(tick, snapshot, context, prior_demand=DEMAND)
    controller.finish(ticks, snapshot, "school")


def test_transitions_chain_observations_and_average_interval_rewards():
    controller = SliceController("proposed", capacity=100.0, qos=VerifyingQos(), control_interval_ticks=5)
    controller.start("school", DEMAND)
    _drive(controller, 15, lambda t: float(t))
    records = controller.transitions.records
    assert len(records) == 3              # decisions at 0, 5, 10; the tick-15 one has no measured interval
    for a, b in zip(records, records[1:]):
        assert a["next_obs"] == b["obs"] and a["next_tick"] == b["tick"]
    assert records[0]["reward"] == np.mean([1, 2, 3, 4, 5])          # rewards measured after the decision
    assert records[-1]["done"] and all(len(r["action"]) == 4 for r in records)
    assert len(records[0]["obs"]) == controller._obs_env.observation_space.shape[0]


def test_failed_enforcement_is_logged_but_not_learned():
    learned = []
    log = TransitionLog(learner=lambda c, a, r: learned.append(r))
    log.bind_enforcement(lambda i: {"verified": False})
    log.decision(5, np.zeros(3), [0, 0, 0, 0], "school", {}, 0, applied=True)
    log.reward(10.0)
    log.finish(10, np.ones(3))
    assert log.records[0]["enforcement_verified"] is False and not log.records[0]["learnable"]
    assert learned == []


def test_online_cem_learns_from_live_rewards_and_checkpoints(tmp_path):
    policy = OnlineCEMPolicy(path=str(tmp_path / "online.json"), population=4, elite=2, seed=1)
    good = np.array([0.5, -0.2, 0.0, 0.1])
    for _ in range(3):                                   # 3 updates, reward peaks at `good`
        for _ in range(4):
            mult = policy("school", {})
            action = action_from_multipliers(mult)
            policy.learn("school", action, -float(np.sum((np.array(action) - good) ** 2)))
    assert policy.state["school"]["updates"] == 3
    start = np.log10(np.clip((policy.offline.policy or {}).get("school", np.ones(4)), 0.1, 10))
    assert np.linalg.norm(np.array(policy.state["school"]["mean"]) - good) < np.linalg.norm(start - good)
    policy.save()
    resumed = OnlineCEMPolicy(path=str(tmp_path / "online.json"))
    assert resumed.state["school"]["updates"] == 3


def test_rl_online_scheduler_wires_policy_learning_into_transitions(tmp_path, monkeypatch):
    monkeypatch.setattr(OnlineCEMPolicy, "ONLINE_PATH", str(tmp_path / "online.json"))
    controller = SliceController("rl_online", capacity=100.0, qos=VerifyingQos(), control_interval_ticks=1)
    controller.start("school", DEMAND)
    _drive(controller, 8, lambda t: 50.0 + t)
    assert controller.policy.samples_this_run == len(controller.transitions.records) == 8   # decisions at ticks 0..7
    assert controller.policy.state["school"]["updates"] == 2
    assert (tmp_path / "online.json").exists()
