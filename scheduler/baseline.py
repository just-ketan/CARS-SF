"""
Rule-based baseline scheduler using existing slicing modules.
"""

from __future__ import annotations

from typing import Any

from slicing.allocation_engine import AllocationEngine
from slicing.context_engine import ContextEngine
from traffic_models.demand_generator import DemandGenerator


class RuleBasedScheduler:
    """Heuristic policy using ContextEngine + AllocationEngine."""

    def __init__(self, total_bandwidth: float = 100.0):
        self.total_bandwidth = total_bandwidth
        self.context_engine = ContextEngine()
        self.allocation_engine = AllocationEngine()
        self.demand_generator = DemandGenerator()

    def decide(self, context_id: str, demands: dict[str, float] | None = None) -> dict[str, float]:
        priorities = self.context_engine.get_context(context_id)
        if demands is None:
            demands = self.demand_generator.get_demands(context_id)
        return self.allocation_engine.allocate(
            self.total_bandwidth, priorities, demands
        )

    def compute_reward(
        self,
        allocation: dict[str, float],
        measured_qos: dict[str, dict[str, float]],
        priorities: dict[str, int],
    ) -> float:
        total_weight = sum(priorities.values())
        reward = 0.0
        sla_violations = 0

        for service, bw in allocation.items():
            qos = measured_qos.get(service, {})
            throughput = qos.get("throughput_mbps", 0)
            latency = qos.get("latency_ms", 0)
            satisfaction = min(1.0, throughput / max(bw, 0.01))
            if latency > 100:
                sla_violations += 1
            weight = priorities.get(service, 1) / total_weight
            reward += weight * satisfaction * 100

        reward -= sla_violations * 10
        return round(reward, 2)
