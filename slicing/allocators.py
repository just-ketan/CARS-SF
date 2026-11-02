"""
Allocation strategies (architecture.md §4.4) behind one interface.

  demand_aware   proposed: per-slice floors, priority-weighted share capped at
                 demand, surplus redistributed to unsatisfied slices
  qos_aware      QoS-targeted (one direction at a time): each slice gets demand ×
                 headroom; when that is infeasible, slices are served in an explicit
                 priority order and the ones left short are reported as degraded
  proportional   priority-weighted split, ignores demand (Priority Engine only)
  static_equal   equal fixed shares, ignores context and demand
  tgpp           technology-centric 3GPP slices (URLLC/eMBB/mMTC) with fixed shares
  none           no slicing: one shared FIFO-like queue
"""

from __future__ import annotations

from core.config import load_yaml
from slicing.allocation_engine import AllocationEngine

SERVICES = ("healthcare", "education", "agriculture", "general")


def _slices() -> dict:
    return load_yaml("slices.yaml")


class DemandAwareAllocator:
    name = "demand_aware"
    classes = SERVICES

    def __init__(self, floors: dict[str, float] | None = None):
        self.engine = AllocationEngine()
        self.floors = floors if floors is not None else {
            s: cfg.get("min_mbps", 0) for s, cfg in _slices()["service_slices"].items()
        }

    def allocate(self, capacity: float, priorities: dict, demands: dict) -> dict[str, float]:
        guaranteed = {
            s: min(self.floors.get(s, 0.0), demands.get(s, 0.0), capacity / len(SERVICES))
            for s in SERVICES
        }
        remaining = capacity - sum(guaranteed.values())
        residual_demand = {s: max(demands.get(s, 0.0) - guaranteed[s], 0.0) for s in SERVICES}
        extra = self.engine.allocate(remaining, {s: priorities[s] for s in SERVICES}, residual_demand)
        return {s: round(guaranteed[s] + extra.get(s, 0.0), 2) for s in SERVICES}


class DemandAwareNoSurplusAllocator(DemandAwareAllocator):
    """Ablation: floors + priority share capped at demand, idle share NOT redistributed."""

    name = "demand_aware_no_surplus"

    def allocate(self, capacity: float, priorities: dict, demands: dict) -> dict[str, float]:
        guaranteed = {
            s: min(self.floors.get(s, 0.0), demands.get(s, 0.0), capacity / len(SERVICES))
            for s in SERVICES
        }
        remaining = capacity - sum(guaranteed.values())
        total = sum(priorities[s] for s in SERVICES)
        return {
            s: round(guaranteed[s] + min(remaining * priorities[s] / total,
                                         max(demands.get(s, 0.0) - guaranteed[s], 0.0)), 2)
            for s in SERVICES
        }


class QoSAwareAllocator:
    """Allocate for each slice's QoS target in one direction of the link.

    Regimes (per direction, recorded in ``regime`` and ``audit``):
      sla_feasible   Σ demand × headroom ≤ C: every slice gets its full SLA target
      mean_feasible  Σ demand ≤ C < Σ demand × headroom: mean demands met, burst headroom rationed
      overload       Σ demand > C: starvation guard, then rationing
    Rationing follows the context's declared degradation policy: ``priority`` (critical
    slices first) or ``proportional`` (equal fraction of every shortfall).

    1. Every slice gets its floor (a small reverse floor in its light direction).
    2. Demands first: if Σ max(floor, demand) ≤ C, every slice gets its demand.
       Otherwise (overloaded direction):
         a. anti-starvation guard: every slice first gets max(floor, 20 % of its
            demand), twice the reward's starvation threshold (scaled down above the
            floors if even the guards do not fit). For elastic (TCP) slices the demand
            used here is at least the context's design demand: their measured demand
            falls when they are starved and cannot anchor the guard;
         b. the rest is served in descending priority, each slice up to its
            burst-protected target demand × headroom.
       Slices granted less than their demand are listed in ``degraded``. The
       degradation order is explicit and auditable, but no slice is starved.
    3. Headroom from the spare capacity, first to slices currently failing
       their SLA (``at_risk``), then in priority order: up to
       demand × (headroom − 1) per slice to absorb VBR bursts above the mean.
       Headroom never displaces another slice's demand. The controller raises a
       slice's headroom while its measured loss exceeds its SLA and relaxes it
       when the loss is well below (``SliceController._adapt_headroom``).
    4. Any capacity still left is shared by priority among the slices that use
       this direction (HTB lends idle capacity anyway; this makes the guarantee
       explicit where it can matter).
    """

    name = "qos_aware"
    classes = SERVICES
    BASE_HEADROOM, MAX_HEADROOM = 1.1, 1.6
    REVERSE_FLOOR = 0.5          # Mb/s for a slice's light direction (ACKs, requests)
    STARVATION_GUARD = 0.2       # share of demand every slice keeps when a direction is overloaded

    def __init__(self, floors: dict[str, float] | None = None):
        self.floors = floors if floors is not None else {
            s: cfg.get("min_mbps", 0) for s, cfg in _slices()["service_slices"].items()
        }
        self.headroom = {s: self.BASE_HEADROOM for s in SERVICES}
        self.at_risk: set[str] = set()      # slices currently failing their SLA (set by the controller)
        # Design demand of elastic (TCP) slices in the direction being planned (set by the
        # controller). A starved TCP slice sends less, so its measured demand collapses;
        # the starvation guard must not collapse with it.
        self.reference: dict[str, float] = {}
        # Per slice, the part of its last grant a residual policy may not take away:
        # max(floor, starvation guard), capped at the grant (see scheduler/residual.py).
        self.protected: dict[str, float] = {}
        self.degraded: list[str] = []
        self.feasible = True
        # Context-dependent degradation policy (registries/scenarios.yaml `degradation`), set by
        # the controller per plan: "priority" (emergencies) or "proportional" (everyday).
        self.policy = "priority"
        self.regime = "sla_feasible"
        self.audit: dict = {}

    POLICIES = ("priority", "proportional")

    def allocate(self, capacity: float, priorities: dict, demands: dict) -> dict[str, float]:
        """One direction. Sets ``regime`` (sla_feasible | mean_feasible | overload),
        ``degraded``, ``protected`` and ``audit`` (what each slice was owed and got)."""
        floors = {
            s: min(self.floors.get(s, 0.0), capacity / len(SERVICES))
            if demands.get(s, 0.0) >= self.REVERSE_FLOOR else self.REVERSE_FLOOR
            for s in SERVICES
        }
        policy = self.policy if self.policy in self.POLICIES else "priority"
        base = {s: max(floors[s], demands.get(s, 0.0)) for s in SERVICES}
        target = {s: max(base[s], demands.get(s, 0.0) * self.headroom.get(s, self.BASE_HEADROOM)) for s in SERVICES}
        order = sorted(SERVICES, key=lambda s: (-priorities.get(s, 1.0), SERVICES.index(s)))
        guard_now = {s: max(floors[s], self.STARVATION_GUARD * max(demands.get(s, 0.0), self.reference.get(s, 0.0)))
                     for s in SERVICES}

        if sum(target.values()) <= capacity:
            # SLA-feasible: every slice gets its demand plus its burst headroom.
            self.regime, self.feasible, self.degraded = "sla_feasible", True, []
            grant = dict(target)
        elif sum(base.values()) <= capacity:
            # Capacity boundary: every mean demand fits, but not every burst requirement.
            # Mean throughput is never cut; only burst headroom is rationed, by the policy.
            self.regime, self.feasible, self.degraded = "mean_feasible", True, []
            grant = dict(base)
            spare = capacity - sum(grant.values())
            if policy == "proportional":
                self._share_proportionally(grant, target, spare)
            else:
                at_risk_first = [s for s in order if s in self.at_risk] + [s for s in order if s not in self.at_risk]
                self._serve_in_order(grant, target, spare, at_risk_first)
        else:
            # Overload: the starvation guard first, then the remaining capacity by the policy.
            # Evaluation v1–v2 showed strict priority on bare demand starving best-effort TCP
            # and a guard on a collapsing TCP estimate; the guard is anchored on design demand.
            self.regime, self.feasible = "overload", False
            guard = dict(guard_now)
            if sum(guard.values()) > capacity:
                above = {s: guard[s] - floors[s] for s in SERVICES}
                room = max(capacity - sum(floors.values()), 0.0)
                scale = room / sum(above.values()) if sum(above.values()) > 0 else 0.0
                guard = {s: floors[s] + above[s] * scale for s in SERVICES}
            grant = dict(guard)
            remaining = capacity - sum(grant.values())
            if policy == "proportional":
                self._share_proportionally(grant, base, remaining)
            else:
                self._serve_in_order(grant, target, remaining, order)
            self.degraded = [s for s in order if grant[s] + 1e-6 < demands.get(s, 0.0)]

        spare = capacity - sum(grant.values())
        if spare > 1e-6:
            # Leftover capacity (every slice already has its target) goes to the slices that use
            # this direction in proportion to their demand. It is context-independent on purpose:
            # once every SLA target is met, a context change must not cause a reconfiguration.
            active = [s for s in SERVICES if demands.get(s, 0.0) >= self.REVERSE_FLOOR] or list(SERVICES)
            total = sum(max(demands.get(s, 0.0), 1e-9) for s in active)
            for s in active:
                grant[s] += spare * max(demands.get(s, 0.0), 1e-9) / total
        self.protected = {s: round(min(grant[s], guard_now[s]), 2) for s in SERVICES}
        self.audit = {"regime": self.regime, "policy": policy,
                      "owed": {s: round(target[s], 2) for s in SERVICES},
                      "granted": {s: round(grant[s], 2) for s in SERVICES},
                      "degraded": list(self.degraded)}
        return {s: round(grant[s], 2) for s in SERVICES}

    @staticmethod
    def _serve_in_order(grant: dict, target: dict, budget: float, order: list[str]):
        for s in order:
            extra = min(max(budget, 0.0), max(target[s] - grant[s], 0.0))
            grant[s] += extra
            budget -= extra

    @staticmethod
    def _share_proportionally(grant: dict, target: dict, budget: float):
        """Every slice receives the same fraction of its remaining shortfall."""
        want = {s: max(target[s] - grant[s], 0.0) for s in grant}
        total = sum(want.values())
        if total <= 0 or budget <= 0:
            return
        fraction = min(1.0, budget / total)
        for s in grant:
            grant[s] += want[s] * fraction


class ProportionalAllocator:
    name = "proportional"
    classes = SERVICES

    def allocate(self, capacity: float, priorities: dict, demands: dict) -> dict[str, float]:
        total = sum(priorities[s] for s in SERVICES)
        return {s: round(capacity * priorities[s] / total, 2) for s in SERVICES}


class StaticEqualAllocator:
    name = "static_equal"
    classes = SERVICES
    static = True

    def allocate(self, capacity: float, priorities: dict, demands: dict) -> dict[str, float]:
        return {s: round(capacity / len(SERVICES), 2) for s in SERVICES}


class TgppAllocator:
    name = "tgpp"
    static = True

    def __init__(self):
        self.slices = _slices()["tgpp_slices"]
        self.classes = tuple(self.slices)

    def allocate(self, capacity: float, priorities: dict, demands: dict) -> dict[str, float]:
        return {name: round(capacity * cfg["share"], 2) for name, cfg in self.slices.items()}


class NoSlicingAllocator:
    name = "none"
    classes = ()
    static = True

    def allocate(self, capacity: float, priorities: dict, demands: dict) -> dict[str, float]:
        return {}


ALLOCATORS = {
    cls.name: cls
    for cls in (DemandAwareAllocator, DemandAwareNoSurplusAllocator, QoSAwareAllocator, ProportionalAllocator, StaticEqualAllocator, TgppAllocator, NoSlicingAllocator)
}


def make_allocator(name: str):
    if name not in ALLOCATORS:
        raise ValueError(f"unknown allocator {name}; choose from {sorted(ALLOCATORS)}")
    return ALLOCATORS[name]()
