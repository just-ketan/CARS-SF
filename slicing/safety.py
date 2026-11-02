"""
Safety validation of an allocation before it is actuated (the "Safety Validation"
stage between allocation policy and network actuation).

``validate`` checks the invariants every scheduler must respect, per direction:

  * every rate is finite and ≥ 0;
  * Σ rates ≤ C (+ rounding tolerance);
  * every slice keeps its protected minimum (floor or anti-starvation guard, from the
    allocator that produced the plan).

A plan that violates them is never actuated: the controller keeps the last good
allocation and records the violations.

``accept_learned`` is the acceptance gate of the safe RL hybrid. A learned proposal
is used only if it passes ``validate`` and, in addition,

  * no slice that is currently failing its SLA (``at_risk``) or explicitly degraded
    receives less than the heuristic plan gives it, and
  * it moves at most ``max_move_share`` of each direction's capacity away from the
    heuristic plan (bounded reconfiguration).

Otherwise the heuristic plan is used.
"""

from __future__ import annotations

import math

TOLERANCE_MBPS = 0.05
MAX_MOVE_SHARE = 0.2


def validate(directional: dict[str, dict[str, float]], capacity: float,
             protected: dict[str, dict[str, float]] | None = None) -> list[str]:
    violations = []
    for direction, rates in directional.items():
        for slice_name, rate in rates.items():
            if rate is None or not math.isfinite(rate) or rate < 0:
                violations.append(f"{direction}/{slice_name}: invalid rate {rate}")
        total = sum(r for r in rates.values() if r is not None and math.isfinite(r))
        if total > capacity + TOLERANCE_MBPS:
            violations.append(f"{direction}: Σ {total:.2f} > C {capacity:.2f}")
        for slice_name, minimum in ((protected or {}).get(direction) or {}).items():
            if rates.get(slice_name, 0.0) + TOLERANCE_MBPS < minimum:
                violations.append(f"{direction}/{slice_name}: {rates.get(slice_name, 0.0):.2f} < protected {minimum:.2f}")
    return violations


def accept_learned(proposal: dict[str, dict[str, float]], heuristic: dict[str, dict[str, float]],
                   capacity: float, protected: dict[str, dict[str, float]] | None,
                   at_risk: set[str], degraded: set[str],
                   max_move_share: float = MAX_MOVE_SHARE,
                   priorities: dict[str, float] | None = None) -> tuple[bool, list[str]]:
    """With ``priorities`` (restoring QoS under a persistent violation) a learned plan may
    rebalance between violating slices, but never away from a higher-priority one."""
    reasons = validate(proposal, capacity, protected)
    for direction, rates in proposal.items():
        base = heuristic.get(direction, {})
        for slice_name in at_risk | degraded:
            if rates.get(slice_name, 0.0) + TOLERANCE_MBPS >= base.get(slice_name, 0.0):
                continue
            if priorities is not None:
                gainers = [s for s in rates if rates[s] > base.get(s, 0.0) + TOLERANCE_MBPS]
                if gainers and all(priorities.get(s, 1.0) > priorities.get(slice_name, 1.0) for s in gainers):
                    continue
            reasons.append(f"{direction}/{slice_name}: learned plan takes capacity from a slice "
                           f"{'at SLA risk' if slice_name in at_risk else 'already degraded'}")
        moved = sum(abs(rates.get(s, 0.0) - base.get(s, 0.0)) for s in set(rates) | set(base)) / 2
        if moved > max_move_share * capacity + TOLERANCE_MBPS:
            reasons.append(f"{direction}: moves {moved:.1f} Mb/s > {max_move_share:.0%} of C")
    return not reasons, reasons
