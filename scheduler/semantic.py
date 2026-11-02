"""
Semantic state for the residual policy: what a situation *means*, not which one it is.

State v2 (scheduler/residual.py) names the scenario with a one-hot vector, so a policy
has no way to relate a scenario it never trained on to the ones it did. The semantic
state replaces that identifier with descriptors the policy can generalise over. Only
the observation changes: PPO, its loss and the reward are untouched.

    criticality (4)     context priority of each class / the context's highest priority
    policy (1)          1 = priority degradation (emergency), 0 = proportional (everyday)
    failure (1)         the scenario declares a network failure
    on_backup (1)       self-healing has moved traffic to the backup path
    demand (4)          classified offered load in the class's dominant direction / C
    allocation (4)      current rate in that direction / C
    loss margin (4)     measured loss / SLA, clipped at 5, scaled to [0, 1]
    delay margin (4)    queue delay / SLA delay, clipped at 2, scaled to [0, 1]
    persistent (4)      the class is in a persistent QoS violation
    utilisation (2)     uplink and downlink utilisation of the rural link
    confidence (1)      SliceNet's mean decision confidence (1 with address rules)

Whether this beats state v2 is decided by experiments/semantic_study.py.
"""

from __future__ import annotations

import numpy as np

from slicing.directions import DIRECTIONS, dominant_direction

SERVICES = ("healthcare", "education", "agriculture", "general")
SEMANTIC_OBS_DIM = 30


def build_semantic_observation(
    priorities: dict[str, float],
    degradation: str,
    failure_scenario: bool,
    on_backup: bool,
    directional_demand: dict[str, dict[str, float]],
    directional_allocation: dict[str, dict[str, float]],
    slice_qos: dict[str, dict[str, float]] | None,
    persistent: set[str],
    capacity: float,
    sla_loss: dict[str, float],
    sla_delay: dict[str, float],
    confidence: float = 1.0,
) -> np.ndarray:
    top = max(priorities.get(s, 1.0) for s in SERVICES) or 1.0
    criticality = [priorities.get(s, 1.0) / top for s in SERVICES]
    demand, alloc, loss, delay = [], [], [], []
    for s in SERVICES:
        d = dominant_direction(s)
        demand.append(min(directional_demand.get(d, {}).get(s, 0.0) / capacity, 2.0))
        alloc.append(directional_allocation.get(d, {}).get(s, 0.0) / capacity)
        q = (slice_qos or {}).get(s) or {}
        loss.append(min(float(q.get("loss_pct", 0.0)) / sla_loss[s], 5.0) / 5.0)
        delay.append(min(float(q.get("queue_delay_ms", 0.0)) / sla_delay[s], 2.0) / 2.0)
    utilisation = [min(sum(directional_demand.get(d, {}).values()) / capacity, 2.0) for d in DIRECTIONS]
    return np.array(
        criticality + [1.0 if degradation == "priority" else 0.0, float(failure_scenario), float(on_backup)]
        + demand + alloc + loss + delay + [float(s in persistent) for s in SERVICES] + utilisation
        + [float(np.clip(confidence, 0.0, 1.0))],
        dtype=np.float32,
    )
