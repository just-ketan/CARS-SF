"""
Slice Controller: the closed control loop of architecture.md §6–7.

    context ─▶ demand estimate ─▶ priority matrix ─▶ allocation ─▶ QoS policy
       ▲                                                              │
       └──────── telemetry / monitoring / self-healing feedback ◀─────┘

Components are composed from ``registries/schedulers.yaml``; every one of
them can be swapped independently (see core/interfaces.py).
"""

from __future__ import annotations

from typing import Any

from core.config import load_yaml
from self_healing.engine import apply_constraints, ceilings_for
from slicing.allocators import make_allocator
from slicing.demand_estimator import MeasuredDemandEstimator, OracleDemandEstimator
from slicing.priority_engine import PriorityEngine
from scheduler.transitions import TransitionLog, action_from_multipliers

CHANGE_THRESHOLD_MBPS = 1.0


def scheduler_spec(name: str) -> dict[str, Any]:
    registry = load_yaml("schedulers.yaml")
    name = registry.get("aliases", {}).get(name, name)
    if name not in registry["schedulers"]:
        raise ValueError(f"unknown scheduler {name}; choose from {sorted(registry['schedulers'])}")
    return {"name": name, **registry["schedulers"][name]}


def make_policy(name: str):
    if name in (None, "none"):
        return None
    from scheduler.agent import CEMPolicy, PPOPolicy

    if name == "cem_online":
        from scheduler.agent import OnlineCEMPolicy
        return OnlineCEMPolicy()
    policy = CEMPolicy() if name == "cem" else PPOPolicy() if name == "ppo" else None
    if policy is None:
        raise ValueError(f"unknown policy {name}")
    return policy if policy.available else None


class SliceController:
    def __init__(
        self,
        scheduler: str = "proposed",
        capacity: float = 100.0,
        qos=None,
        demand_mode: str = "measured",
        control_interval_ticks: int = 5,
        efficiency: float = 1.0,
        context_aware: bool = True,
    ):
        self.spec = scheduler_spec(scheduler)
        self.name = self.spec["name"]
        self.capacity = capacity
        self.qos = qos
        self.demand_mode = demand_mode
        self.interval = max(1, control_interval_ticks)
        self.efficiency = efficiency
        self.context_aware = context_aware and bool(self.spec.get("context_aware", True))
        self.allocator = make_allocator(self.spec["allocator"])
        self.policy = make_policy(self.spec["policy"])
        self.policy_fallback = self.spec["policy"] != "none" and self.policy is None
        self.priority_engine = PriorityEngine(policy=self.policy)
        self.floors = getattr(self.allocator, "floors", {})
        self.context: str | None = None
        self.estimator = None
        self.allocation: dict[str, float] = {}
        self.history: list[dict[str, Any]] = []
        self._last_constraint_key = ("normal", ())
        self.enforcement_failures = 0
        self._estimator_since = 0
        self.transitions = TransitionLog(learner=getattr(self.policy, "learn", None))
        self.transitions.bind_enforcement(lambda i: self.history[i].get("enforcement") if i < len(self.history) else None)
        self._obs_env = None

    # ------------------------------------------------------------- planning

    def _new_estimator(self, prior: dict[str, float]):
        if self.demand_mode == "oracle" or not self.spec["adaptive"]:
            return OracleDemandEstimator(prior)
        return MeasuredDemandEstimator(prior)

    def plan(
        self,
        context: str,
        demands: dict[str, float],
        constraints: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], dict[str, float]]:
        # Ablation: without context awareness the "normal" priority matrix is used throughout.
        priority_context = context if self.context_aware else "normal"
        priorities = self.priority_engine.priorities(priority_context, {**(state or {}), "demands": demands})
        for service, multiplier in (constraints or {}).get("boosts", {}).items():
            if service in priorities:
                priorities[service] *= multiplier
        link_demand = {s: d / self.efficiency for s, d in demands.items()}
        allocation = self.allocator.allocate(self.capacity, priorities, link_demand)
        if constraints and self.spec["healing"] and self.spec["class_mode"] == "service":
            allocation = apply_constraints(allocation, link_demand, self.capacity, constraints, self.floors)
        return allocation, priorities

    def start(self, context: str, prior_demand: dict[str, float]) -> dict[str, float]:
        self.context = context
        self.estimator = self._new_estimator(prior_demand)
        self._estimator_since = 0
        state = {"allocation": {}, "backlog_bytes": {}, "on_backup": False}
        obs = self.observation(context, prior_demand, state)
        self.allocation, priorities = self.plan(context, prior_demand, state=state)
        self._record(0, "initial", prior_demand, priorities)
        self.transitions.decision(0, obs, action_from_multipliers(self.priority_engine.last_multipliers),
                                  context, self.allocation, len(self.history) - 1, applied=True)
        return self.allocation

    # ------------------------------------------------------------ RL interface

    def observation(self, context: str, demands: dict[str, float], state: dict[str, Any]):
        """The RL state: the simulator's observation layout built from live controller state."""
        if self._obs_env is None:
            from scheduler.env_seq import SequentialSlicingEnv
            self._obs_env = SequentialSlicingEnv(capacity=self.capacity)
        return self._obs_env.observation_from_live(
            context, demands, state.get("allocation") or {}, state.get("backlog_bytes"), state.get("on_backup", False),
        )

    def observe_reward(self, reward: float):
        self.transitions.reward(reward)

    def finish(self, tick: int, snapshot: dict[str, Any], context: str, constraints=None):
        state = self._state(snapshot, constraints)
        demands = self.estimator.estimate() or dict(self.estimator.prior)
        self.transitions.finish(tick, self.observation(context, demands, state))
        if hasattr(self.policy, "save"):
            self.policy.save()

    def _state(self, snapshot: dict[str, Any], constraints) -> dict[str, Any]:
        return {
            "allocation": self.allocation,
            "backlog_bytes": snapshot.get("queue_bytes", {}),
            "on_backup": (constraints or {}).get("state") in ("on_backup", "degraded"),
        }

    # -------------------------------------------------------------- control

    def step(
        self,
        tick: int,
        snapshot: dict[str, Any],
        context_state: dict[str, Any],
        constraints: dict[str, Any] | None = None,
        prior_demand: dict[str, float] | None = None,
    ) -> dict[str, float] | None:
        """Fold one tick of telemetry in; returns the new allocation if it changed."""
        context = context_state["context"]
        self.estimator.observe(snapshot, self.allocation)
        if not self.spec["adaptive"]:
            return None

        reason = None
        if context != self.context:
            reason = f"context {self.context}→{context}"
            self.context = context
            self.estimator = self._new_estimator(prior_demand or self.estimator.estimate())
            self._estimator_since = tick
        constraint_key = (
            (constraints or {}).get("state"),
            tuple(sorted((constraints or {}).get("boosts", {}).items())),
        )
        if reason is None and constraint_key != self._last_constraint_key and constraints is not None:
            boosts = ",".join(f"{svc}x{m:g}" for svc, m in constraint_key[1]) or "none"
            reason = f"healing {constraint_key[0]} (boosts {boosts})"
        self._last_constraint_key = constraint_key
        if reason is None and tick % self.interval == 0:
            reason = "control interval"
        if reason is None:
            return None

        # Until the estimator has a full control interval of samples (traffic
        # ramp-up, fresh context) the design-time prior is the better estimate.
        warmed = tick - self._estimator_since >= self.interval
        demands = (self.estimator.estimate() if warmed else None) or dict(
            prior_demand or self.estimator.prior
        )
        state = self._state(snapshot, constraints)
        obs = self.observation(context, demands, state)
        allocation, priorities = self.plan(context, demands, constraints, state)
        changed = any(
            abs(allocation.get(s, 0) - self.allocation.get(s, 0)) >= CHANGE_THRESHOLD_MBPS
            for s in set(allocation) | set(self.allocation)
        )
        self._record(tick, reason, demands, priorities, applied=changed, allocation=allocation)
        self.transitions.decision(tick, obs, action_from_multipliers(self.priority_engine.last_multipliers),
                                  context, allocation, len(self.history) - 1, applied=changed)
        if not changed:
            return None
        enforcement = None
        if self.qos is not None:
            ceilings = ceilings_for(allocation, constraints) if self.spec["healing"] else {}
            enforcement = self.qos.apply_allocation(allocation, ceilings=ceilings) if ceilings \
                else self.qos.apply_allocation(allocation)
            self.history[-1]["enforcement"] = {
                "verified": (enforcement or {}).get("verified"),
                "failures": (enforcement or {}).get("failures", []),
                "mismatches": (enforcement or {}).get("mismatches", []),
            }
            if enforcement and enforcement.get("verified") is False:
                # Keep the last known-good allocation as current state; the next
                # interval recomputes and retries instead of assuming success.
                self.enforcement_failures += 1
                return None
        self.allocation = allocation
        return allocation

    def _record(self, tick, reason, demands, priorities, applied=True, allocation=None):
        self.history.append({
            "tick": tick,
            "reason": reason,
            "context": self.context,
            "demand_estimate": {k: round(v, 2) for k, v in demands.items()},
            "priorities": {k: round(v, 3) for k, v in priorities.items()},
            "allocation": allocation or self.allocation,
            "applied": applied,
        })
