"""
Priority Engine (architecture.md §4.3): produces the priority matrix.

The base matrix comes from the operating context (scenario registry). A
*policy* may adjust it — the rule-based policy leaves it unchanged, a learned
policy (Learning Engine) multiplies each service weight. Swapping the policy is
how the framework moves from rule-based priorities to AI-generated ones without
touching any other module.
"""

from __future__ import annotations

from typing import Any, Callable

from slicing.context_engine import ContextEngine

Policy = Callable[[str, dict[str, Any]], dict[str, float]]


class PriorityEngine:
    def __init__(self, policy: Policy | None = None, context_engine: ContextEngine | None = None):
        self.context_engine = context_engine or ContextEngine()
        self.policy = policy
        self.weights: dict[str, float] = {}
        self.last_multipliers: dict[str, float] = {}

    def set_weights(self, weights):
        self.weights = dict(weights)

    def priorities(self, context_id: str, state: dict[str, Any] | None = None) -> dict[str, float]:
        """Priority matrix for a context, adjusted by the policy if one is set."""
        base = self.context_engine.get_context(context_id)
        if self.policy is None:
            multipliers = {}
        else:
            multipliers = self.policy(context_id, state or {})
        # The policy's action, kept so the live loop can log it as an RL transition.
        self.last_multipliers = {s: float(multipliers.get(s, 1.0)) for s in base}
        self.weights = {s: base[s] * self.last_multipliers[s] for s in base}
        return dict(self.weights)

    def allocate_bandwidth(self, total_bandwidth):
        """Pure weighted-proportional split (no demand awareness) — a baseline."""
        tot_weight = sum(self.weights.values())
        allocation = {}
        for srvc, wt in self.weights.items():
            allocation[srvc] = round(total_bandwidth * wt / tot_weight, 2)
        return allocation
