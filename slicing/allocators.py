"""
Allocation strategies (architecture.md §4.4) behind one interface.

  demand_aware   proposed: per-slice floors, priority-weighted share capped at
                 demand, surplus redistributed to unsatisfied slices
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
    for cls in (DemandAwareAllocator, DemandAwareNoSurplusAllocator, ProportionalAllocator, StaticEqualAllocator, TgppAllocator, NoSlicingAllocator)
}


def make_allocator(name: str):
    if name not in ALLOCATORS:
        raise ValueError(f"unknown allocator {name}; choose from {sorted(ALLOCATORS)}")
    return ALLOCATORS[name]()
