"""
Sequential slicing environment (Gymnasium) for the Learning Engine.

Unlike ``SlicingEnv`` (a contextual bandit), actions here have consequences
that carry over: unserved demand accumulates as backlog (queueing delay, then
overflow loss), demand is autocorrelated, contexts switch as a Markov chain and
the backhaul can fail, halving core-bound capacity for a while. The controller
logic is the one used live: priority multipliers → demand-aware allocation
with floors → self-healing constraints.

Calibration (``scheduler/models/calibration.json``, from Mininet feedback logs)
sets propagation delays and the delivered/allocated efficiency.
"""

from __future__ import annotations

import json
import os

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from core.config import load_scenarios, load_yaml
from self_healing.engine import apply_constraints, service_locations
from scheduler.reward import SliceOutcome, compute_reward
from slicing.allocators import DemandAwareAllocator

SERVICES = ("healthcare", "education", "agriculture", "general")
CALIBRATION_PATH = os.path.join(os.path.dirname(__file__), "models", "calibration.json")
DEFAULT_CALIBRATION = {
    "efficiency": 1.0,
    "prop_delay_ms": {"healthcare": 8.0, "education": 28.0, "agriculture": 8.0, "general": 28.0},
}


def load_calibration() -> dict:
    if os.path.exists(CALIBRATION_PATH):
        with open(CALIBRATION_PATH, encoding="utf-8") as handle:
            return {**DEFAULT_CALIBRATION, **json.load(handle)}
    return dict(DEFAULT_CALIBRATION)


class SequentialSlicingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        capacity: float = 100.0,
        backup_capacity: float = 50.0,
        dt_s: float = 5.0,
        episode_steps: int = 120,
        context_stay_prob: float = 0.92,
        failure_prob: float = 0.02,
        failure_steps: int = 10,
        buffer_s: float = 0.1,
        seed: int | None = None,
    ):
        super().__init__()
        scenarios = {s["id"]: s for s in load_scenarios()}
        self.contexts = list(scenarios)
        self.priorities = {c: scenarios[c]["priority_weights"] for c in self.contexts}
        self.mean_demand = {c: scenarios[c]["demand_mbps"] for c in self.contexts}
        slices = load_yaml("slices.yaml")["service_slices"]
        self.sla_latency = {s: slices[s]["sla"]["latency_ms"] for s in SERVICES}
        self.floors = {s: slices[s]["min_mbps"] for s in SERVICES}
        self.allocator = DemandAwareAllocator(self.floors)
        self.locations = service_locations()
        self.calibration = load_calibration()

        self.capacity, self.backup_capacity = capacity, backup_capacity
        self.dt, self.episode_steps = dt_s, episode_steps
        self.stay_prob, self.failure_prob, self.failure_steps = context_stay_prob, failure_prob, failure_steps
        self.buffer_s = buffer_s

        n = len(self.contexts)
        self.observation_space = spaces.Box(0.0, 10.0, shape=(n + 13,), dtype=np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(4,), dtype=np.float32)
        self.rng = np.random.default_rng(seed)
        self.fixed_context: str | None = None

    # ----------------------------------------------------------------- gym API

    def reset(self, *, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        options = options or {}
        self.fixed_context = options.get("context")
        self.context = self.fixed_context or self.contexts[self.rng.integers(len(self.contexts))]
        self.noise = np.zeros(4)
        self.backlog = np.zeros(4)
        self.allocation = np.full(4, self.capacity / 4)
        self.failure_left = 0
        self.first_step = True
        self.t = 0
        self.demand = self._draw_demand()
        return self._obs(), {}

    def step(self, action):
        multipliers = self.action_to_multipliers(action)
        base = self.priorities[self.context]
        priorities = {s: base[s] * multipliers[s] for s in SERVICES}
        demand = dict(zip(SERVICES, self.demand))
        # Allocate for link-level demand (calibrated overhead), as the live controller does.
        eff = self.calibration["efficiency"]
        allocation = self.allocator.allocate(
            self.capacity, priorities, {s: d / eff for s, d in demand.items()}
        )
        constraints = {
            "locations": self.locations,
            "core_capacity_mbps": self.backup_capacity if self.failure_left else None,
        }
        allocation = apply_constraints(allocation, demand, self.capacity, constraints, self.floors)
        alloc = np.array([allocation[s] for s in SERVICES])

        reward, info = self._serve(alloc)
        self.allocation = alloc
        self.first_step = False
        self._advance()
        self.t += 1
        truncated = self.t >= self.episode_steps
        info.update({"context": self.context, "allocation": allocation})
        return self._obs(), reward, False, truncated, info

    # ------------------------------------------------------------- dynamics

    @staticmethod
    def action_to_multipliers(action) -> dict[str, float]:
        action = np.clip(np.asarray(action, dtype=float), -1, 1)
        return {s: float(10 ** action[i]) for i, s in enumerate(SERVICES)}

    def _draw_demand(self) -> np.ndarray:
        mean = np.array([self.mean_demand[self.context][s] for s in SERVICES], dtype=float)
        return np.maximum(mean * (1 + self.noise), 0.1)

    def _advance(self):
        if self.fixed_context is None and self.rng.random() > self.stay_prob:
            self.context = self.contexts[self.rng.integers(len(self.contexts))]
        self.noise = 0.7 * self.noise + self.rng.normal(0, 0.15, 4)
        self.demand = self._draw_demand()
        if self.failure_left:
            self.failure_left -= 1
        elif self.rng.random() < self.failure_prob:
            self.failure_left = self.failure_steps

    def _serve(self, alloc: np.ndarray) -> tuple[float, dict]:
        """Work-conserving service, as HTB with ceil = link capacity behaves.

        Each slice is first served up to its allocation; capacity left idle is
        then lent to still-backlogged slices in proportion to their priority.
        """
        eff = self.calibration["efficiency"]
        weights_raw = np.array([self.priorities[self.context][s] for s in SERVICES], dtype=float)
        arrivals = self.demand * self.dt + self.backlog
        served = np.minimum(alloc * eff * self.dt, arrivals)
        spare = max(self.capacity * eff * self.dt - served.sum(), 0.0)
        core_cap = self.backup_capacity * eff * self.dt if self.failure_left else None
        for _ in range(4):
            want = arrivals - served
            if core_cap is not None:
                core_mask = np.array([self.locations.get(s) == "core" for s in SERVICES])
                core_room = max(core_cap - served[core_mask].sum(), 0.0)
                if core_room <= 1e-9:
                    want = np.where(core_mask, 0.0, want)
            active = want > 1e-9
            if spare <= 1e-9 or not active.any():
                break
            share = spare * weights_raw * active / (weights_raw * active).sum()
            extra = np.minimum(share, want)
            served += extra
            spare -= extra.sum()
        backlog = arrivals - served
        service_rate = np.maximum(served / self.dt, 1e-3)
        buffer = np.maximum(alloc * eff, 1.0) * self.buffer_s
        overflow = np.maximum(backlog - buffer, 0)
        self.backlog = backlog - overflow
        capacity_rate = service_rate

        loss_pct = overflow / np.maximum(self.demand * self.dt, 1e-6) * 100
        prop = np.array([self.calibration["prop_delay_ms"][s] for s in SERVICES])
        delay = prop + self.backlog / capacity_rate * 1000
        delivered = served / self.dt
        outcomes = {
            s: SliceOutcome(
                demand_mbps=float(self.demand[i]),
                delivered_mbps=float(delivered[i]),
                delay_ms=float(delay[i]),
                loss_pct=float(loss_pct[i]),
                allocation_mbps=float(alloc[i]),
                previous_allocation_mbps=None if self.first_step else float(self.allocation[i]),
            )
            for i, s in enumerate(SERVICES)
        }
        reward, reward_info = compute_reward(
            outcomes, self.priorities[self.context], self.sla_latency, self.capacity
        )
        return reward, {
            "satisfaction": reward_info["satisfaction"],
            "delay_ms": dict(zip(SERVICES, delay.round(1))),
            "loss_pct": dict(zip(SERVICES, loss_pct.round(2))),
            "sla_violations": len(reward_info["sla_violations"]),
            "starved": reward_info["starved"],
            "reward_terms": reward_info["terms"],
        }

    def _obs(self) -> np.ndarray:
        one_hot = np.zeros(len(self.contexts))
        one_hot[self.contexts.index(self.context)] = 1
        return np.concatenate([
            one_hot,
            self.demand / self.capacity,
            np.minimum(self.backlog / (self.capacity * self.buffer_s), 10),
            self.allocation / self.capacity,
            [1.0 if self.failure_left else 0.0],
        ]).astype(np.float32)

    def observation_from_live(
        self,
        context: str,
        demands: dict[str, float],
        allocation: dict[str, float],
        backlog_bytes: dict[str, float] | None = None,
        on_backup: bool = False,
    ) -> np.ndarray:
        """Build an observation from live controller state (same layout as training)."""
        one_hot = np.zeros(len(self.contexts))
        if context in self.contexts:
            one_hot[self.contexts.index(context)] = 1
        backlog_mbit = np.array([(backlog_bytes or {}).get(s, 0) * 8 / 1e6 for s in SERVICES])
        return np.concatenate([
            one_hot,
            np.array([demands.get(s, 0.0) for s in SERVICES]) / self.capacity,
            np.minimum(backlog_mbit / (self.capacity * self.buffer_s), 10),
            np.array([allocation.get(s, self.capacity / 4) for s in SERVICES]) / self.capacity,
            [1.0 if on_backup else 0.0],
        ]).astype(np.float32)


def evaluate_policy(policy, episodes: int = 20, seed: int = 1000, **env_kwargs) -> dict:
    """Mean episode reward/satisfaction/SLA violations of ``policy(obs, env) -> action``."""
    env = SequentialSlicingEnv(**env_kwargs)
    rewards, violations, sat = [], [], []
    for ep in range(episodes):
        obs, _ = env.reset(seed=seed + ep)
        total, v, s, done = 0.0, 0, [], False
        while not done:
            obs, reward, _, done, info = env.step(policy(obs, env))
            total += reward
            v += info["sla_violations"]
            s.append(np.mean(list(info["satisfaction"].values())))
        rewards.append(total)
        violations.append(v)
        sat.append(np.mean(s))
    return {
        "mean_reward": round(float(np.mean(rewards)), 2),
        "std_reward": round(float(np.std(rewards)), 2),
        "sla_violations_per_episode": round(float(np.mean(violations)), 2),
        "mean_satisfaction": round(float(np.mean(sat)), 4),
        "episode_rewards": [round(float(r), 3) for r in rewards],
    }
