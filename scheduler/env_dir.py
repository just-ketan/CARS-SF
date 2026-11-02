"""
Direction-aware slicing simulator for the residual RL policy (Gymnasium).

What it models, and why (each item fixes a gap of ``env_seq`` found on the
emulated network):

* Full duplex: each direction of the rural uplink has capacity C and its own
  allocation; services load the direction their applications use
  (``slicing/directions.py``).
* Sub-second bursts: a 5 s control step is simulated as 50 × 100 ms sub-steps.
  Each slice's offered rate per sub-step is its mean demand × a mean-preserving
  lognormal factor with slice-specific burstiness σ_s, calibrated against the
  per-slice loss measured on Mininet (``scheduler/calibrate_bursts.py``).
* HTB: every slice is served up to its rate; spare capacity is lent in HTB
  priority order (healthcare first) up to the link rate (ceil = C).
* CoDel-like queues: CoDel drops only once the queue has stayed above its
  target for an interval, so a slice's queue may hold about
  rate × (target + interval) before the excess is dropped (loss); the queue
  adds queueing delay.

The base allocation is the live ``QoSAwareAllocator`` (demands first, priority
order, burst headroom 1.1) on the demand *estimate* (last step's mean offered
load, as the live estimator); the policy's residual action is applied with
``scheduler.residual.apply_residual``. Reward is the shared
``scheduler.reward.compute_reward`` with loss SLAs. The observation is the
shared state v2 (``scheduler.residual.build_observation``).

``state="semantic"`` uses scheduler/semantic.py instead of state v2.
``triggered=True`` applies the action only while a class is in a persistent QoS
violation, as the live loop does (one 5 s step spans the monitor's persistence window).
``include_failures=True`` adds the failure scenarios with a coarse model: fiber cut and
backhaul degradation move core-bound traffic to a 50 Mb/s, 20 ms slower backup path for
part of the visit; a core switch failure leaves core-bound services undeliverable.

Not modelled: TCP congestion control (elastic slices are treated as their offered rate).
"""

from __future__ import annotations

import json
import os

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from core.config import load_scenarios, load_yaml
from scheduler.residual import OBS_DIM, SERVICES, apply_residual, build_observation
from scheduler.reward import SliceOutcome, compute_reward
from scheduler.semantic import SEMANTIC_OBS_DIM, build_semantic_observation
from slicing.allocators import QoSAwareAllocator
from slicing.directions import DIRECTIONS, dominant_direction, elastic_directions, split_demand

BURST_PATH = os.path.join(os.path.dirname(__file__), "models", "burst_calibration.json")
DEFAULT_BURSTINESS = {"healthcare": 0.35, "education": 0.3, "agriculture": 0.6, "general": 0.4}
PROP_DELAY_MS = {"healthcare": 8.0, "education": 28.0, "agriculture": 8.0, "general": 28.0}
EVALUATED_SCENARIOS = ("normal", "school", "harvest", "disaster", "medical_emergency",
                       "fiber_cut", "backhaul_degradation", "core_switch_failure")
CORE_SERVICES = ("education", "general")
BACKUP_CAPACITY_MBPS, BACKUP_EXTRA_DELAY_MS, FAILURE_ACTIVE_PROB = 50.0, 20.0, 0.6


def load_borrow_efficiency() -> float:
    if os.path.exists(BURST_PATH):
        with open(BURST_PATH, encoding="utf-8") as handle:
            return float(json.load(handle).get("borrow_efficiency", 1.0))
    return 1.0


def load_burstiness() -> dict[str, float]:
    if os.path.exists(BURST_PATH):
        with open(BURST_PATH, encoding="utf-8") as handle:
            return {**DEFAULT_BURSTINESS, **json.load(handle).get("sigma", {})}
    return dict(DEFAULT_BURSTINESS)


def serve_direction(rng, demand, alloc, prio_order, sigma, queue, target_s, capacity, dt_s, substeps,
                    elastic=None, borrow_efficiency=1.0):
    """Simulate one control step on one direction. Returns per-slice (offered, delivered, dropped,
    mean queueing delay ms) in Mbit and the queue left over (Mbit).

    Elastic (TCP) slices back off instead of overflowing: their excess beyond the
    standing-queue limit is not sent (curtailed throughput, no loss).

    ``borrow_efficiency`` is the share of idle capacity a class can actually
    borrow within a sub-step. Kernel HTB at ~100 Mb/s does not lend instantly
    (burst/quantum granularity), so bursts above a class's own rate partly queue
    even when the link has room; the value is fitted from live loss."""
    elastic = np.zeros(len(SERVICES), dtype=bool) if elastic is None else elastic
    n = len(SERVICES)
    sub = dt_s / substeps
    offered = np.zeros(n); delivered = np.zeros(n); dropped = np.zeros(n); delay_acc = np.zeros(n)
    for _ in range(substeps):
        factor = np.exp(sigma * rng.standard_normal(n) - sigma ** 2 / 2)
        arrivals = demand * factor * sub
        offered += arrivals
        want = queue + arrivals
        served = np.minimum(want, alloc * sub)
        spare = max(capacity * sub - served.sum(), 0.0) * borrow_efficiency
        for i in prio_order:                       # HTB lends spare by priority, ceil = C
            extra = min(spare, want[i] - served[i])
            served[i] += extra
            spare -= extra
        queue = want - served
        rate = np.maximum(served / sub, np.maximum(alloc, 0.1))
        # CoDel drops only after the queue has stayed above `target` for an `interval`,
        # so it tolerates bursts of about rate × (target + interval).
        limit = target_s * rate
        over = np.maximum(queue - limit, 0.0)
        dropped += np.where(elastic, 0.0, over)
        offered -= np.where(elastic, over, 0.0)    # TCP never sent what it backed off from
        queue = queue - over
        delivered += served
        delay_acc += queue / rate * 1000
    return offered, delivered, dropped, delay_acc / substeps, queue


class DirectionalSlicingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, capacity: float = 100.0, dt_s: float = 5.0, substeps: int = 50,
                 episode_steps: int = 60, context_stay_prob: float = 0.92, seed: int | None = None,
                 contexts: list[str] | None = None, reward_weights: dict[str, float] | None = None,
                 load_scale: float = 1.0, state: str = "v2", triggered: bool = False,
                 include_failures: bool = False):
        super().__init__()
        scenarios = {s["id"]: s for s in load_scenarios()}
        self.all_contexts = list(scenarios)
        # Failure scenarios are not modelled here; train on the operating contexts.
        self.contexts = contexts or [c for c in self.all_contexts if not scenarios[c].get("failure")
                                     or (include_failures and c in EVALUATED_SCENARIOS)]
        self.failure_context = {c: bool(scenarios[c].get("failure")) for c in self.all_contexts}
        self.state, self.triggered = state, triggered
        self.priorities = {c: scenarios[c]["priority_weights"] for c in self.all_contexts}
        self.degradation = {c: scenarios[c].get("degradation", "priority") for c in self.all_contexts}
        self.reward_weights = reward_weights
        self.load_scale = load_scale         # evaluation under workload shift (> 1 = heavier than designed)
        self.mean_demand = {c: scenarios[c]["demand_mbps"] for c in self.all_contexts}
        slices = load_yaml("slices.yaml")["service_slices"]
        self.floors = {s: slices[s]["min_mbps"] for s in SERVICES}
        self.sla_delay = {s: float(slices[s]["sla"]["latency_ms"]) for s in SERVICES}
        self.sla_loss = {s: float(slices[s]["sla"]["loss_pct"]) for s in SERVICES}
        # burst tolerance (target + interval) per slice, from the slice's CoDel profile
        self.target_s = np.array([(slices[s].get("queue", {}).get("target_ms", 5)
                                   + slices[s].get("queue", {}).get("interval_ms", 100)) / 1000 for s in SERVICES])
        self.htb_order = sorted(range(len(SERVICES)), key=lambda i: slices[SERVICES[i]]["htb_prio"])
        self.sigma = np.array([load_burstiness()[s] for s in SERVICES])
        self.borrow_efficiency = load_borrow_efficiency()
        elastic = elastic_directions()
        self.elastic = {d: np.array([d in elastic[s] for s in SERVICES]) for d in DIRECTIONS}
        self.capacity, self.dt, self.substeps = capacity, dt_s, substeps
        self.episode_steps, self.stay_prob = episode_steps, context_stay_prob
        self.allocator = QoSAwareAllocator(self.floors)
        dim = SEMANTIC_OBS_DIM if state == "semantic" else OBS_DIM
        self.observation_space = spaces.Box(0.0, 2.0, shape=(dim,), dtype=np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(4,), dtype=np.float32)
        self.rng = np.random.default_rng(seed)
        self.fixed_context: str | None = None

    # ---------------------------------------------------------------- gym API

    def reset(self, *, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        options = options or {}
        self.fixed_context = options.get("context")
        self.context = self.fixed_context or self.contexts[self.rng.integers(len(self.contexts))]
        self.noise = np.zeros(len(SERVICES))
        self.queues = {d: np.zeros(len(SERVICES)) for d in DIRECTIONS}
        self.t = 0
        self.prev_flat = None
        self.qos = {s: {"loss_pct": 0.0, "queue_delay_ms": 0.0} for s in SERVICES}
        self.persistent: set[str] = set()
        self._draw_failure()
        self.demand = self._draw_demand()
        self.estimate = split_demand(dict(zip(SERVICES, self.demand)))      # starts at the design prior
        self.allocation = self._base_allocation()
        return self._obs(), {}

    def step(self, action):
        base = self._base_allocation()
        rl_on = not self.triggered or bool(self.persistent)
        alloc = apply_residual(base, action, self.capacity, self.floors, self.protected) if rl_on else base
        true_split = split_demand(dict(zip(SERVICES, self.demand)))
        if self.on_backup:
            # Core-bound traffic shares the smaller backup path.
            core = sum(true_split[d][s] for d in DIRECTIONS for s in CORE_SERVICES)
            scale = min(1.0, BACKUP_CAPACITY_MBPS / core) if core > 0 else 1.0
            for d in DIRECTIONS:
                for s in CORE_SERVICES:
                    true_split[d][s] *= scale
        results = {}
        for d in DIRECTIONS:
            demand = np.array([true_split[d][s] for s in SERVICES])
            rates = np.array([alloc[d][s] for s in SERVICES])
            offered, delivered, dropped, delay, self.queues[d] = serve_direction(
                self.rng, demand, rates, self.htb_order, self.sigma, self.queues[d],
                self.target_s, self.capacity, self.dt, self.substeps, self.elastic[d], self.borrow_efficiency)
            results[d] = (offered, delivered, dropped, delay)

        flat = {s: alloc[dominant_direction(s)][s] for s in SERVICES}
        outcomes, qos = {}, {}
        for i, s in enumerate(SERVICES):
            dom = dominant_direction(s)
            offered = sum(results[d][0][i] for d in DIRECTIONS)
            dropped = sum(results[d][2][i] for d in DIRECTIONS)
            loss = 100.0 * dropped / offered if offered > 1e-9 else 0.0
            queue_ms = float(results[dom][3][i])
            qos[s] = {"loss_pct": loss, "queue_delay_ms": queue_ms}
            core_lost = self.core_down and s in CORE_SERVICES
            extra = BACKUP_EXTRA_DELAY_MS if self.on_backup and s in CORE_SERVICES else 0.0
            outcomes[s] = SliceOutcome(
                demand_mbps=float(self.demand[i]),
                delivered_mbps=0.0 if core_lost else float(sum(results[d][1][i] for d in DIRECTIONS) / self.dt),
                delay_ms=None if core_lost else PROP_DELAY_MS[s] + extra + queue_ms, loss_pct=loss,
                allocation_mbps=flat[s],
                previous_allocation_mbps=None if self.prev_flat is None else self.prev_flat[s],
            )
        reward, info = compute_reward(outcomes, self.priorities[self.context], self.sla_delay,
                                      self.capacity, self.sla_loss, self.reward_weights)
        # The live estimator reports last interval's mean offered load per direction.
        self.estimate = {d: {s: float(results[d][0][i] / self.dt) for i, s in enumerate(SERVICES)}
                         for d in DIRECTIONS}
        self.qos, self.allocation, self.prev_flat = qos, alloc, flat
        self.persistent = {s for s, o in outcomes.items()
                           if o.delay_ms is None or o.delay_ms > self.sla_delay[s] or o.loss_pct > self.sla_loss[s]}
        self._advance()
        self.t += 1
        info.update({"context": self.context, "allocation": alloc, "qos": qos,
                     "sla_violations_count": len(info["sla_violations"])})
        return self._obs(), reward, False, self.t >= self.episode_steps, info

    # ------------------------------------------------------------ dynamics

    def _base_allocation(self) -> dict[str, dict[str, float]]:
        priorities = self.priorities[self.context]
        base, self.protected = {}, {}
        design = split_demand(self.mean_demand[self.context])
        self.allocator.policy = self.degradation[self.context]
        for d in DIRECTIONS:
            # Same guard anchoring as the live controller: elastic slices' design demand.
            self.allocator.reference = {s: design[d][s] for s in SERVICES if self.elastic[d][SERVICES.index(s)]}
            base[d] = self.allocator.allocate(self.capacity, priorities, self.estimate[d])
            self.protected[d] = dict(self.allocator.protected)
        return base

    def _draw_demand(self) -> np.ndarray:
        mean = np.array([self.mean_demand[self.context][s] for s in SERVICES], dtype=float) * self.load_scale
        return np.maximum(mean * (1 + self.noise), 0.1)

    def _advance(self):
        if self.fixed_context is None and self.rng.random() > self.stay_prob:
            self.context = self.contexts[self.rng.integers(len(self.contexts))]
            self._draw_failure()
        # Step-to-step drift of the mean offered load is small on the testbed (design rates);
        # sub-second variability is the burst model's job.
        self.noise = np.clip(0.7 * self.noise + self.rng.normal(0, 0.03, len(SERVICES)), -0.3, 0.3)
        self.demand = self._draw_demand()

    def _draw_failure(self):
        active = self.failure_context[self.context] and self.rng.random() < FAILURE_ACTIVE_PROB
        self.on_backup = active and self.context in ("fiber_cut", "backhaul_degradation")
        self.core_down = active and self.context == "core_switch_failure"

    def _obs(self) -> np.ndarray:
        if self.state == "semantic":
            return build_semantic_observation(
                self.priorities[self.context], self.degradation[self.context], self.failure_context[self.context],
                self.on_backup, self.estimate, self.allocation, self.qos, self.persistent, self.capacity,
                self.sla_loss, self.sla_delay)
        return build_observation(self.context, self.estimate, self.allocation, self.qos, self.on_backup,
                                 self.capacity, self.sla_loss, self.sla_delay, self.all_contexts)


def evaluate_residual(policy, episodes: int = 20, seed: int = 1000, **env_kwargs) -> dict:
    """Per-episode reward, SLA violations and per-slice loss of ``policy(obs, env) -> action``."""
    env = DirectionalSlicingEnv(**env_kwargs)
    rewards, violations, losses = [], [], []
    for ep in range(episodes):
        obs, _ = env.reset(seed=seed + ep)
        total, v, loss, done = 0.0, 0, {s: [] for s in SERVICES}, False
        while not done:
            obs, reward, _, done, info = env.step(policy(obs, env))
            total += reward
            v += info["sla_violations_count"]
            for s in SERVICES:
                loss[s].append(info["qos"][s]["loss_pct"])
        rewards.append(total)
        violations.append(v)
        losses.append({s: float(np.mean(loss[s])) for s in SERVICES})
    return {
        "mean_reward": round(float(np.mean(rewards)), 2),
        "std_reward": round(float(np.std(rewards)), 2),
        "sla_violations_per_episode": round(float(np.mean(violations)), 2),
        "mean_loss_pct": {s: round(float(np.mean([l[s] for l in losses])), 3) for s in SERVICES},
        "episode_rewards": [round(float(r), 3) for r in rewards],
    }
