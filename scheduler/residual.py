"""
Residual RL interface (state v2 and the residual action), shared by the
direction-aware simulator (``scheduler/env_dir.py``) and the live controller.

State v2 (K + 17 floats, K = number of registry contexts):
    0..K-1      context one-hot (registry order)
    K..K+3      demand in the slice's dominant direction / C
    K+4..K+7    current allocation in the dominant direction / C
    K+8..K+11   measured loss / SLA loss target, clipped to [0, 5], scaled to [0, 1]
    K+12..K+15  queueing delay / SLA one-way delay, clipped to [0, 2], scaled to [0, 1]
    K+16        on backup / degraded (self-healing)

Residual action a ∈ [−1, 1]^4: the QoS-aware heuristic's allocation is the
baseline; the policy scales each slice's rate in its dominant direction by
(1 + 0.3·a_s). Each direction is then renormalised to capacity: freed capacity
goes to slices that asked for more, a shortfall is taken from the others in
proportion to their rate above their floor. Floors and Σ ≤ C always hold, so a
learned policy can only redistribute, never break a guarantee. a = 0 reproduces
the heuristic exactly.

"Floor" here is the allocator's *protected* minimum per direction (floor or
anti-starvation guard, whichever is larger): evaluation v3 showed a residual
allowed to cut a slice down to its plain floor starving best-effort TCP.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from slicing.directions import DIRECTIONS, dominant_direction

SERVICES = ("healthcare", "education", "agriculture", "general")
RESIDUAL_SCALE = 0.3
def contexts() -> list[str]:
    from core.config import load_scenarios
    return [s["id"] for s in load_scenarios()]


OBS_DIM = len(contexts()) + 17     # one-hot over the registry's contexts + 16 per-slice values + on_backup


def build_observation(
    context: str,
    directional_demand: dict[str, dict[str, float]],
    directional_allocation: dict[str, dict[str, float]],
    slice_qos: dict[str, dict[str, float]] | None,
    on_backup: bool,
    capacity: float,
    sla_loss: dict[str, float],
    sla_delay: dict[str, float],
    context_list: list[str] | None = None,
) -> np.ndarray:
    context_list = context_list or contexts()
    one_hot = np.zeros(len(context_list))
    if context in context_list:
        one_hot[context_list.index(context)] = 1.0
    demand, alloc, loss, delay = [], [], [], []
    for s in SERVICES:
        d = dominant_direction(s)
        demand.append(min(directional_demand.get(d, {}).get(s, 0.0) / capacity, 2.0))
        alloc.append(directional_allocation.get(d, {}).get(s, 0.0) / capacity)
        q = (slice_qos or {}).get(s) or {}
        loss.append(min(float(q.get("loss_pct", 0.0)) / sla_loss[s], 5.0) / 5.0)
        delay.append(min(float(q.get("queue_delay_ms", 0.0)) / sla_delay[s], 2.0) / 2.0)
    return np.concatenate([one_hot, demand, alloc, loss, delay, [1.0 if on_backup else 0.0]]).astype(np.float32)


def apply_residual(
    directional_allocation: dict[str, dict[str, float]],
    action: Any,
    capacity: float,
    floors: dict[str, float],
    protected: dict[str, dict[str, float]] | None = None,
) -> dict[str, dict[str, float]]:
    action = np.clip(np.asarray(action, dtype=float), -1.0, 1.0)
    out = {d: dict(v) for d, v in directional_allocation.items()}
    for direction in DIRECTIONS:
        rates = out[direction]
        minimum = {s: max(floors.get(s, 0.0), (protected or {}).get(direction, {}).get(s, 0.0)) for s in rates}
        floor = {s: min(minimum[s], rates.get(s, 0.0)) for s in rates}
        wanted = {}
        for i, s in enumerate(SERVICES):
            if s in rates and dominant_direction(s) == direction:
                wanted[s] = max(floor[s], rates[s] * (1 + RESIDUAL_SCALE * action[i]))
            elif s in rates:
                wanted[s] = rates[s]
        excess = sum(wanted.values()) - capacity
        if excess > 0:
            # Take the shortfall from slices that did not ask for more, above their floors.
            donors = {s: wanted[s] - floor[s] for s in wanted
                      if wanted[s] <= rates[s] + 1e-9 and wanted[s] > floor[s]}
            if sum(donors.values()) < excess:
                donors = {s: wanted[s] - floor[s] for s in wanted if wanted[s] > floor[s]}
            pool = sum(donors.values())
            if pool > 0:
                for s, room in donors.items():
                    wanted[s] -= min(room, excess * room / pool)
        elif excess < 0:
            # Freed capacity goes to slices that asked for more (by their request), else proportionally.
            takers = {s: wanted[s] - rates[s] for s in wanted if wanted[s] > rates[s]}
            pool = sum(takers.values()) or sum(wanted.values())
            for s in wanted:
                share = takers.get(s, 0.0) if takers else wanted[s]
                wanted[s] += -excess * share / pool
        out[direction] = {s: round(float(max(floor[s], v)), 2) for s, v in wanted.items()}
    return out
