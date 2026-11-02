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
from slicing.directions import DIRECTIONS, elastic_directions, flatten, split_demand
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
    if name == "cem_residual_online":
        from scheduler.agent import OnlineResidualCEM
        return OnlineResidualCEM()
    if name == "cem_residual_online_frozen":
        from scheduler.agent import OnlineResidualCEM
        return OnlineResidualCEM(learning=False)
    if name in ("closed_loop", "closed_loop_frozen"):
        from scheduler.agent import ClosedLoopResidualPolicy
        policy = ClosedLoopResidualPolicy(learning=name == "closed_loop")
        return policy if policy.available else None
    if name == "ppo_residual":
        from scheduler.agent import ResidualPPOPolicy
        policy = ResidualPPOPolicy()
        return policy if policy.available else None
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
        self.context_blind = bool(self.spec.get("context_blind"))
        self.context_aware = context_aware and bool(self.spec.get("context_aware", True)) and not self.context_blind
        self.allocator = make_allocator(self.spec["allocator"])
        self.policy = make_policy(self.spec["policy"])
        self.policy_fallback = self.spec["policy"] != "none" and self.policy is None
        # A residual policy (module D) corrects the QoS-aware allocation instead of the
        # priority matrix; the priority engine then stays rule-based.
        self.residual_policy = self.policy if getattr(self.policy, "kind", None) == "residual" else None
        self.priority_engine = PriorityEngine(policy=None if self.residual_policy else self.policy)
        self._pending_obs = None
        self.last_residual_action: list[float] | None = None
        self.floors = getattr(self.allocator, "floors", {})
        self.context: str | None = None
        self.estimator = None
        self.allocation: dict[str, float] = {}
        self.history: list[dict[str, Any]] = []
        self._last_constraint_key = ("normal", ())
        self.enforcement_failures = 0
        self._estimator_since = 0
        # Direction-aware planning (slicing/directions.py) and the loss-driven headroom loop.
        self.directional = bool(self.spec.get("directional"))
        self.qos_loop = bool(self.spec.get("qos_loop")) and hasattr(self.allocator, "headroom")
        self.directional_allocation: dict[str, dict[str, float]] | None = None
        self._planned_directional: dict[str, dict[str, float]] | None = None
        self._planned_info: dict[str, Any] = {}
        self._loss_window: dict[str, list[float]] = {}
        self._quiet_intervals: dict[str, int] = {}
        # Module C: react to SLA risk on the next tick; predict demand ramps, queue growth
        # and clock-driven context changes.
        self.reactive = bool(self.spec.get("reactive"))
        self.predictive = bool(self.spec.get("predictive"))
        self._last_decision_tick = 0
        self._queue_delay_history: dict[str, list[float]] = {}
        self._preprovisioned_for: str | None = None
        self.reactions: list[dict[str, Any]] = []
        self._qos_window: dict[str, list[tuple[float, float]]] = {}
        from core.config import load_scenarios
        self._degradation = {sc["id"]: sc.get("degradation", "priority") for sc in load_scenarios()}
        self._planned_protected: dict[str, dict[str, float]] = {}
        self._learned_decision: dict | None = None
        self.hybrid_stats = {"accepted": 0, "rejected": 0}
        self.safety_rejections = 0
        # QoS monitoring on measurements; persistent violations trigger RL adaptation.
        from monitoring.qos_monitor import QoSViolationMonitor
        self.qos_monitor = QoSViolationMonitor(elastic={s for s, d in elastic_directions().items() if d})
        self.qos_status: dict[str, dict[str, Any]] = {}
        self.triggered = bool(self.spec.get("triggered"))
        self.rl_active = False
        self.adaptations: list[dict[str, Any]] = []
        self._open_adaptation: dict[str, Any] | None = None
        self.classifier_confidence = 1.0
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
        directional_demands: dict[str, dict[str, float]] | None = None,
    ) -> tuple[dict[str, float], dict[str, float]]:
        # Ablation: without context awareness the "normal" priority matrix is used throughout.
        priority_context = context if self.context_aware else "normal"
        priorities = self.priority_engine.priorities(priority_context, {**(state or {}), "demands": demands})
        for service, multiplier in (constraints or {}).get("boosts", {}).items():
            if service in priorities:
                priorities[service] *= multiplier
        if self.directional:
            # Each direction of the full-duplex link is its own capacity C.
            directional_demands = directional_demands or split_demand(demands)
            planned, info, protected = {}, {}, {}
            elastic = elastic_directions()
            if hasattr(self.allocator, "policy"):
                self.allocator.policy = self._degradation.get(priority_context, "priority")
            if self.context_blind:
                # A context-blind controller has no context prior either: the guard anchor is the
                # design demand it started with (supplied by the caller as the normal context's).
                design = split_demand(self.estimator.prior) if self.estimator is not None else {}
            design = split_demand(self.estimator.prior) if self.estimator is not None else {}
            for direction in DIRECTIONS:
                link_demand = {s: d / self.efficiency for s, d in directional_demands[direction].items()}
                if hasattr(self.allocator, "reference"):
                    self.allocator.reference = {s: v / self.efficiency for s, v in design.get(direction, {}).items()
                                                if direction in elastic.get(s, set())}
                alloc = self.allocator.allocate(self.capacity, priorities, link_demand)
                info[direction] = {"feasible": getattr(self.allocator, "feasible", None),
                                   "regime": getattr(self.allocator, "regime", None),
                                   "policy": getattr(self.allocator, "policy", None),
                                   "degraded": list(getattr(self.allocator, "degraded", []))}
                protected[direction] = dict(getattr(self.allocator, "protected", {}))
                if constraints and self.spec["healing"] and self.spec["class_mode"] == "service":
                    alloc = apply_constraints(alloc, link_demand, self.capacity, constraints, self.floors)
                    # Self-healing may legitimately cap a slice below its guard (backup capacity).
                    protected[direction] = {s: min(v, alloc.get(s, v)) for s, v in protected[direction].items()}
                planned[direction] = alloc
            self._learned_decision = None
            if self.residual_policy is not None and self._pending_obs is not None:
                from scheduler.residual import apply_residual
                if self.triggered and not self.rl_active:
                    # QoS is met: the rules stay in charge and the policy is not consulted.
                    self.last_residual_action = [0.0] * 4
                else:
                    self.last_residual_action = self.residual_policy.residual(context, self._pending_obs)
                    proposal = apply_residual(planned, self.last_residual_action, self.capacity, self.floors,
                                              protected)
                    if self.spec.get("safe_hybrid"):
                        from slicing.safety import accept_learned
                        degraded = {s for i in info.values() for s in i["degraded"]}
                        violating = set(getattr(self.allocator, "at_risk", set())) | self.qos_monitor.persistent()
                        ok, reasons = accept_learned(proposal, planned, self.capacity, protected, violating, degraded,
                                                     priorities=priorities if self.triggered else None)
                        self._learned_decision = {"accepted": ok, "reasons": reasons}
                        self.hybrid_stats["accepted" if ok else "rejected"] += 1
                        planned = proposal if ok else planned
                    else:
                        planned = proposal
            self._planned_directional, self._planned_info, self._planned_protected = planned, info, protected
            return flatten(planned), priorities
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
        directional_demands = self.estimator.estimate_directional()
        obs = self.observation(context, prior_demand, state, directional_demands)
        self._pending_obs = obs
        self.allocation, priorities = self.plan(context, prior_demand, state=state,
                                                directional_demands=directional_demands)
        self.directional_allocation = self._planned_directional
        self._record(0, "initial", prior_demand, priorities)
        self.transitions.decision(0, obs, self._action(), context, self.allocation, len(self.history) - 1, applied=True,
                                  learner_action=not self.triggered)
        return self.allocation

    # ------------------------------------------------------------ RL interface

    def _action(self) -> list[float]:
        if self.residual_policy is not None:
            return [round(float(a), 4) for a in (self.last_residual_action or [0.0, 0.0, 0.0, 0.0])]
        return action_from_multipliers(self.priority_engine.last_multipliers)

    def _window_qos(self) -> dict[str, dict[str, float]]:
        """Mean per-slice loss and queueing delay since the last decision."""
        return {s: {"loss_pct": sum(l for l, _ in v) / len(v), "queue_delay_ms": sum(q for _, q in v) / len(v)}
                for s, v in self._qos_window.items() if v}

    def observation(self, context: str, demands: dict[str, float], state: dict[str, Any],
                    directional_demands: dict[str, dict[str, float]] | None = None):
        """The RL state in the simulator's layout, built from live controller state:
        state v2 (scheduler/residual.py) for residual policies, else env_seq's layout."""
        if self.residual_policy is not None:
            from scheduler.residual import build_observation
            from scheduler.reward import sla_delay_targets, sla_loss_targets
            if getattr(self.residual_policy, "state_version", "v2") == "semantic":
                from core.config import load_scenarios
                from scheduler.semantic import build_semantic_observation
                scenario = next((s for s in load_scenarios() if s["id"] == context), {})
                return build_semantic_observation(
                    scenario.get("priority_weights", {}), self._degradation.get(context, "priority"),
                    bool(scenario.get("failure")), state.get("on_backup", False),
                    directional_demands or split_demand(demands), self.directional_allocation or {},
                    state.get("window_qos"), self.qos_monitor.persistent(), self.capacity,
                    sla_loss_targets(), sla_delay_targets(), self.classifier_confidence)
            return build_observation(context, directional_demands or split_demand(demands),
                                     self.directional_allocation or {}, state.get("window_qos"),
                                     state.get("on_backup", False), self.capacity,
                                     sla_loss_targets(), sla_delay_targets())
        if self._obs_env is None:
            from scheduler.env_seq import SequentialSlicingEnv
            self._obs_env = SequentialSlicingEnv(capacity=self.capacity)
        return self._obs_env.observation_from_live(
            context, demands, state.get("allocation") or {}, state.get("backlog_bytes"), state.get("on_backup", False),
        )

    def observe_reward(self, reward: float):
        self.transitions.reward(reward)

    def finish(self, tick: int, snapshot: dict[str, Any], context: str, constraints=None):
        state = {**self._state(snapshot, constraints), "window_qos": self._window_qos()}
        demands = self.estimator.estimate() or dict(self.estimator.prior)
        self.transitions.finish(tick, self.observation(context, demands, state,
                                                       self.estimator.estimate_directional()))
        self.qos_monitor.finish(tick)
        if hasattr(self.policy, "save"):
            self.policy.save()

    def _state(self, snapshot: dict[str, Any], constraints) -> dict[str, Any]:
        return {
            "allocation": self.allocation,
            "backlog_bytes": snapshot.get("queue_bytes", {}),
            "on_backup": (constraints or {}).get("state") in ("on_backup", "degraded"),
            "slice_qos": snapshot.get("slice_qos", {}),
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
        self.estimator.observe(snapshot, self.allocation, self.directional_allocation)
        self._observe_qos(snapshot)
        offered = prior_demand if self.demand_mode == "oracle" else (self.estimator.estimate() or prior_demand)
        self.qos_status = self.qos_monitor.observe(tick, snapshot, context, offered)
        self._score_adaptation(tick)
        if not self.spec["adaptive"]:
            return None
        risk = self._sla_risk(snapshot) if self.reactive else None
        persistent = self.qos_monitor.persistent()
        if self.triggered:
            was_active, self.rl_active = self.rl_active, bool(persistent)
            # A hand-over is a decision in its own right: the reaction hold-off does not apply.
            if self.rl_active and not was_active:
                risk, self._last_decision_tick = "persistent violation: " + ",".join(sorted(persistent)), -self.interval
            elif was_active and not self.rl_active:
                risk, self._last_decision_tick = "qos restored: rules resume", -self.interval
        upcoming = context_state.get("upcoming") if self.predictive else None

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
        if reason is None and risk and tick - self._last_decision_tick >= self.REACT_HOLD_TICKS:
            reason = f"sla risk: {risk}"
        plan_context = context
        # A forecast change of context, or of offered load (only the labelled oracle can see
        # load changes coming), is pre-provisioned once, PREPROVISION_TICKS ahead.
        key = (upcoming or {}).get("context"), (upcoming or {}).get("load_scale")
        if reason is None and upcoming and (upcoming["context"] != context or upcoming.get("load_scale") is not None) \
                and upcoming["in_ticks"] <= self.PREPROVISION_TICKS and self._preprovisioned_for != key:
            what = upcoming["context"] + (f" ×{upcoming['load_scale']}" if upcoming.get("load_scale") else "")
            reason = f"pre-provision {what} in {upcoming['in_ticks']} ticks"
            self._preprovisioned_for = key
            plan_context = upcoming["context"]
        if reason is None and tick % self.interval == 0:
            reason = "control interval"
        if reason is None:
            return None
        self._last_decision_tick = tick
        if reason.startswith(("sla risk", "pre-provision")):
            self.reactions.append({"tick": tick, "reason": reason})

        # Until the estimator has a full control interval of samples (traffic
        # ramp-up, fresh context) the design-time prior is the better estimate.
        warmed = tick - self._estimator_since >= self.interval
        demands = (self.estimator.estimate() if warmed else None) or dict(
            prior_demand or self.estimator.prior
        )
        directional_demands = (self.estimator.estimate_directional(trend=self.predictive) if warmed else None) \
            or split_demand(demands)
        if reason.startswith("pre-provision"):
            # Pre-provisioning: reserve for the upcoming context's (or load's) demand as well.
            upcoming_split = split_demand(context_state.get("upcoming_demand") or {})
            directional_demands = {
                d: {s: max(directional_demands[d].get(s, 0.0), upcoming_split.get(d, {}).get(s, 0.0))
                    for s in directional_demands[d]} for d in DIRECTIONS
            }
        headroom_changes = self._adapt_headroom()
        state = {**self._state(snapshot, constraints), "window_qos": self._window_qos()}
        obs = self.observation(context, demands, state, directional_demands)
        self._pending_obs = obs
        self._qos_window = {}
        allocation, priorities = self.plan(plan_context, demands, constraints, state, directional_demands)
        if self.directional and self.directional_allocation:
            changed = any(
                abs(self._planned_directional[d].get(s, 0) - self.directional_allocation[d].get(s, 0))
                >= CHANGE_THRESHOLD_MBPS for d in DIRECTIONS for s in self._planned_directional[d]
            )
        else:
            changed = any(
                abs(allocation.get(s, 0) - self.allocation.get(s, 0)) >= CHANGE_THRESHOLD_MBPS
                for s in set(allocation) | set(self.allocation)
            )
        if headroom_changes:
            reason += f" + headroom {headroom_changes}"
        self._record(tick, reason, demands, priorities, applied=changed, allocation=allocation)
        consulted = self.residual_policy is None or not self.triggered or self.rl_active
        accepted = consulted and (self._learned_decision or {}).get("accepted", True)
        if self.triggered and consulted:
            self.history[-1]["rl_adaptation"] = {"accepted": bool(accepted), "action": self.last_residual_action}
            if self._open_adaptation is None:
                self._open_adaptation_record(tick, bool(accepted))
        self.transitions.decision(tick, obs, self._action(), context, allocation, len(self.history) - 1,
                                  applied=changed, learner_action=bool(accepted))
        if not changed:
            return None
        violations = self._safety_violations(allocation)
        if violations:
            # Never actuate a plan that breaks an invariant: keep the last good allocation.
            self.history[-1]["safety"] = {"accepted": False, "violations": violations}
            self.safety_rejections += 1
            return None
        enforcement = None
        if self.qos is not None:
            ceilings = ceilings_for(allocation, constraints) if self.spec["healing"] else {}
            kwargs = {"ceilings": ceilings} if ceilings else {}
            if self.directional:
                kwargs["directional"] = self._planned_directional
            enforcement = self.qos.apply_allocation(allocation, **kwargs)
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
        if self.directional:
            self.directional_allocation = self._planned_directional
        return allocation

    # -------------------------------------------------- did the adaptation help?

    def violation_score(self) -> int:
        return sum(1 for v in self.qos_status.values() if v["status"] != "ok")

    def _open_adaptation_record(self, tick: int, accepted: bool):
        self._open_adaptation = {
            "tick": tick, "context": self.context, "action": self.last_residual_action, "accepted": accepted,
            "violating": sorted(self.qos_monitor.persistent()), "score_before": self.violation_score(),
            "samples": [],
        }

    ADAPTATION_WINDOW_TICKS = 5

    def _score_adaptation(self, tick: int):
        """Subsequent measurements decide whether an RL adjustment restored QoS."""
        record = self._open_adaptation
        if record is None:
            return
        record["samples"].append(self.violation_score())
        if tick - record["tick"] >= self.ADAPTATION_WINDOW_TICKS:
            after = sum(record["samples"]) / len(record["samples"])
            record.update({"score_after": round(after, 3), "improved": after < record["score_before"],
                           "restored": all(s not in self.qos_monitor.persistent() for s in record["violating"])})
            del record["samples"]
            self.adaptations.append(record)
            self._open_adaptation = None

    def _safety_violations(self, allocation: dict[str, float]) -> list[str]:
        from slicing.safety import validate
        if self.directional and self._planned_directional:
            return validate(self._planned_directional, self.capacity, self._planned_protected)
        return validate({"both": allocation}, self.capacity, None)

    # ------------------------------------------------------- reactive / predictive

    REACT_HOLD_TICKS, PREPROVISION_TICKS = 2, 2
    QUEUE_RISK_FRACTION = 0.5          # of the slice's one-way SLA delay

    def _sla_risk(self, snapshot: dict[str, Any]) -> str | None:
        """A slice breaching (or, when predictive, about to breach) its SLA this tick."""
        from scheduler.reward import sla_delay_targets, sla_loss_targets

        loss_t, delay_t = sla_loss_targets(), sla_delay_targets()
        # Slices the allocator has explicitly degraded (demand > capacity) cannot be
        # helped by re-planning; their breaches are expected and already recorded.
        degraded = {s for info in self._planned_info.values() for s in info.get("degraded", [])}
        for service, qos in (snapshot.get("slice_qos") or {}).items():
            if service in degraded:
                continue
            loss, queue = float(qos.get("loss_pct", 0.0)), float(qos.get("queue_delay_ms", 0.0))
            history = self._queue_delay_history.setdefault(service, [])
            history.append(queue)
            del history[:-3]
            if loss > loss_t.get(service, float("inf")):
                return f"{service} loss {loss:.2f}%"
            if elastic_directions().get(service):
                # TCP fills its own queue by design (CoDel bounds it); re-planning does not
                # change that, and demand probing already covers an under-allocated TCP slice.
                continue
            limit = self.QUEUE_RISK_FRACTION * delay_t.get(service, float("inf"))
            if queue > limit:
                return f"{service} queue {queue:.1f} ms"
            if self.predictive and len(history) == 3 and history[0] < history[1] < history[2] \
                    and history[2] > 0.4 * limit and history[2] + 2 * (history[2] - history[0]) / 2 > limit:
                return f"{service} queue rising {history[0]:.1f}→{history[2]:.1f} ms"
        return None

    # ------------------------------------------------------- QoS headroom loop

    LOSS_HIGH, LOSS_LOW_FRACTION, QUIET_INTERVALS = 1.0, 0.25, 3
    HEADROOM_UP, HEADROOM_DOWN = 1.15, 0.97

    def _observe_qos(self, snapshot: dict[str, Any]):
        for service, qos in (snapshot.get("slice_qos") or {}).items():
            self._loss_window.setdefault(service, []).append(float(qos.get("loss_pct", 0.0)))
            self._qos_window.setdefault(service, []).append(
                (float(qos.get("loss_pct", 0.0)), float(qos.get("queue_delay_ms", 0.0))))

    def _adapt_headroom(self) -> dict[str, float]:
        """Per slice: raise burst headroom while its loss over the last interval exceeds
        its SLA loss target; relax it after QUIET_INTERVALS intervals well below target."""
        if not self.qos_loop:
            self._loss_window = {}
            return {}
        from scheduler.reward import sla_loss_targets

        targets, changes = sla_loss_targets(), {}
        allocator = self.allocator
        for service, losses in self._loss_window.items():
            if not losses or service not in allocator.headroom:
                continue
            mean_loss, current = sum(losses) / len(losses), allocator.headroom[service]
            if mean_loss > targets[service] * self.LOSS_HIGH:
                new = min(allocator.MAX_HEADROOM, current * self.HEADROOM_UP)
                self._quiet_intervals[service] = 0
                allocator.at_risk.add(service)
            elif mean_loss < targets[service] * self.LOSS_LOW_FRACTION:
                allocator.at_risk.discard(service)
                self._quiet_intervals[service] = self._quiet_intervals.get(service, 0) + 1
                new = max(allocator.BASE_HEADROOM, current * self.HEADROOM_DOWN) \
                    if self._quiet_intervals[service] >= self.QUIET_INTERVALS else current
            else:
                self._quiet_intervals[service], new = 0, current
            if abs(new - current) > 1e-9:
                allocator.headroom[service] = new
                changes[service] = round(new, 3)
        self._loss_window = {}
        return changes

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
        if self.directional and self._planned_directional:
            self.history[-1]["directional_allocation"] = self._planned_directional
            self.history[-1]["feasibility"] = self._planned_info
            self.history[-1]["protected"] = self._planned_protected
        if self._learned_decision is not None:
            self.history[-1]["learned_proposal"] = self._learned_decision
        if self.qos_loop:
            self.history[-1]["headroom"] = {k: round(v, 3) for k, v in self.allocator.headroom.items()}
