"""
The CARS-SF reward: one definition for the simulator (env_seq), the live
Mininet environment (env_mininet) and the per-tick feedback log.

    r = R_sat + R_sla + R_loss + R_starve + R_realloc + R_idle

  R_sat     = 100 · Σ_s w̃_s · min(1, delivered_s / demand_s)
              context weights w̃ (normalised); the slice's demand is met → 1.
  R_sla     = −10 per slice whose one-way delay exceeds its SLA target
              (a missing delay measurement counts as a violation: no data is not success).
  R_loss    = −0.5 · mean loss % across slices.
  R_starve  = −20 per slice with real demand (≥ 0.5 Mb/s) that receives < 10 % of it.
  R_realloc = −5 · Σ_s |a_s − a'_s| / C, the share of capacity moved by this decision
              (penalises oscillating policies; at most −10).
  R_idle    = −5 · idle share of capacity, only while some slice is unsatisfied
              (capacity left unused while demand goes unserved is waste).

Weights are deliberate: satisfaction dominates (0–100); an SLA breach costs as
much as 10 % of total satisfaction; starvation is worse than any single SLA
breach; reallocation and idling are second-order regularisers. The context
weights come from the scenario registry, never from the policy, so an agent
cannot inflate its own reward by re-weighting slices.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SERVICES = ("healthcare", "education", "agriculture", "general")

W_SLA, W_LOSS, W_STARVE, W_REALLOC, W_IDLE = 10.0, 0.5, 20.0, 5.0, 5.0
STARVE_DEMAND_MBPS, STARVE_SATISFACTION = 0.5, 0.1


@dataclass
class SliceOutcome:
    demand_mbps: float
    delivered_mbps: float
    delay_ms: float | None
    loss_pct: float
    allocation_mbps: float
    previous_allocation_mbps: float | None = None


def compute_reward(
    outcomes: dict[str, SliceOutcome],
    weights: dict[str, float],
    sla_delay_ms: dict[str, float],
    capacity_mbps: float,
) -> tuple[float, dict[str, Any]]:
    total_w = sum(weights.get(s, 0.0) for s in outcomes) or 1.0
    sat, violations, starved, losses, moved = {}, [], [], [], 0.0
    for s, o in outcomes.items():
        sat[s] = 1.0 if o.demand_mbps <= 1e-6 else min(1.0, max(o.delivered_mbps, 0.0) / o.demand_mbps)
        if o.delay_ms is None or o.delay_ms > sla_delay_ms.get(s, float("inf")):
            violations.append(s)
        if o.demand_mbps >= STARVE_DEMAND_MBPS and sat[s] < STARVE_SATISFACTION:
            starved.append(s)
        losses.append(max(o.loss_pct, 0.0))
        if o.previous_allocation_mbps is not None:
            moved += abs(o.allocation_mbps - o.previous_allocation_mbps)

    delivered = sum(max(o.delivered_mbps, 0.0) for o in outcomes.values())
    idle_share = max(capacity_mbps - delivered, 0.0) / capacity_mbps if capacity_mbps > 0 else 0.0
    unsatisfied = any(v < 0.999 for v in sat.values())

    terms = {
        "satisfaction": 100.0 * sum(weights.get(s, 0.0) * sat[s] for s in outcomes) / total_w,
        "sla": -W_SLA * len(violations),
        "loss": -W_LOSS * (sum(losses) / len(losses) if losses else 0.0),
        "starvation": -W_STARVE * len(starved),
        "reallocation": -W_REALLOC * (moved / capacity_mbps if capacity_mbps > 0 else 0.0),
        "idle": -W_IDLE * idle_share if unsatisfied else 0.0,
    }
    reward = float(sum(terms.values()))
    info = {
        "terms": {k: round(v, 4) for k, v in terms.items()},
        "satisfaction": {k: round(v, 4) for k, v in sat.items()},
        "sla_violations": violations,
        "starved": starved,
    }
    return reward, info


# --------------------------------------------------------------------------
# Live (Mininet) outcomes: the same SliceOutcome built from a telemetry snapshot
# --------------------------------------------------------------------------

def sla_delay_targets() -> dict[str, float]:
    from core.config import load_yaml

    slices = load_yaml("slices.yaml")["service_slices"]
    return {s: float(slices[s]["sla"]["latency_ms"]) for s in SERVICES}


def _class_counters(snapshot: dict[str, Any], service: str) -> tuple[int, int]:
    sent = dropped = 0
    for key in ("tc_class_stats", "tc_downlink_class_stats"):
        stats = (snapshot.get(key) or {}).get(service) or {}
        sent += int(stats.get("sent_packets", 0))
        dropped += int(stats.get("dropped", 0))
    return sent, dropped


def outcomes_from_snapshot(
    snapshot: dict[str, Any],
    previous_snapshot: dict[str, Any] | None,
    allocation: dict[str, float],
    previous_allocation: dict[str, float] | None,
    demand: dict[str, float],
) -> dict[str, SliceOutcome]:
    """Map one measured control interval onto the reward's per-slice outcomes.

    delivered  uplink + downlink goodput of the slice's hosts (interface counters),
               the same bidirectional convention as the offered demand and the KPIs
    delay      one-way delay estimated as probe RTT / 2; a missing probe is None,
               which the reward counts as an SLA violation
    loss       Δdropped / (Δsent + Δdropped) on the slice's HTB classes, both directions
    """
    up = snapshot.get("service_throughput_mbps") or {}
    down = snapshot.get("service_downlink_mbps") or {}
    rtt = snapshot.get("service_rtt_ms") or {}
    outcomes = {}
    for s in SERVICES:
        sent, dropped = _class_counters(snapshot, s)
        if previous_snapshot is not None:
            prev_sent, prev_dropped = _class_counters(previous_snapshot, s)
            sent, dropped = max(sent - prev_sent, 0), max(dropped - prev_dropped, 0)
        loss = 100.0 * dropped / (sent + dropped) if sent + dropped > 0 else 0.0
        outcomes[s] = SliceOutcome(
            demand_mbps=float(demand.get(s, 0.0)),
            delivered_mbps=float(up.get(s, 0.0)) + float(down.get(s, 0.0)),
            delay_ms=None if rtt.get(s) is None else float(rtt[s]) / 2,
            loss_pct=loss,
            allocation_mbps=float(allocation.get(s, 0.0)),
            previous_allocation_mbps=None if previous_allocation is None else float(previous_allocation.get(s, 0.0)),
        )
    return outcomes
