"""
Per-slice KPIs and resilience metrics from measured data.

``slice_kpis``       flow-window records → latency p50/p95/p99, jitter, loss,
                     SLA-satisfied share, delivered throughput, demand satisfaction
``jain_fairness``    Jain's index over per-slice (weighted) demand satisfaction
``outage_metrics``   matched packets + failure time → per-service delivery gap
                     (service downtime) and packets lost during failover
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

SERVICES = ("healthcare", "education", "agriculture", "general")


def slice_kpis(df: pd.DataFrame, demands: dict[str, float] | None = None, window_s: float = 5.0) -> dict[str, Any]:
    if df.empty or "service_class" not in df.columns:
        return {}
    rate_df = df
    if "window_index" in df.columns and df["window_index"].nunique() > 1:
        # Traffic stops mid-window when the control loop ends, so the final
        # window is partial; counting it would understate delivered rates by
        # up to 1/N depending on how many stray tail packets fall into it.
        rate_df = df[df["window_index"] < df["window_index"].max()]
    windows = max(rate_df["window_index"].nunique(), 1) if "window_index" in rate_df.columns else 1
    kpis: dict[str, Any] = {}
    for service, group in df.groupby("service_class"):
        rate_group = rate_df[rate_df["service_class"] == service]
        lat = group["end_to_end_latency_ms"].dropna()
        p95 = group["p95_latency_ms"].dropna() if "p95_latency_ms" in group else lat
        delivered = rate_group["throughput_mbps"].sum() / windows
        demand = (demands or {}).get(service)
        kpis[service] = {
            "records": int(len(group)),
            "latency_p50_ms": _q(lat, 50),
            "latency_p95_ms": _q(p95, 95),
            "latency_p99_ms": _q(p95, 99),
            "jitter_ms": round(float(group["jitter_ms"].mean()), 3),
            "loss_pct": round(float(group["packet_loss_rate"].mean()), 3),
            "sla_satisfied_share": round(float(group["sla_satisfied"].astype(bool).mean()), 4),
            "delivered_mbps": round(float(delivered), 3),
            "demand_mbps": demand,
            "demand_satisfaction": round(min(1.0, delivered / demand), 4) if demand else None,
        }
    return kpis


def _q(series: pd.Series, q: float):
    return round(float(np.percentile(series, q)), 3) if len(series) else None


def jain_fairness(values: list[float]) -> float | None:
    values = [v for v in values if v is not None]
    if not values or sum(values) == 0:
        return None
    arr = np.array(values, dtype=float)
    return round(float(arr.sum() ** 2 / (len(arr) * (arr ** 2).sum())), 4)


def weighted_utility(kpis: dict[str, Any], weights: dict[str, float]) -> float | None:
    """Priority-weighted mean demand satisfaction (the 'social utility' of an allocation)."""
    pairs = [
        (weights.get(s, 1.0), k["demand_satisfaction"])
        for s, k in kpis.items() if k.get("demand_satisfaction") is not None
    ]
    if not pairs:
        return None
    total = sum(w for w, _ in pairs)
    return round(sum(w * v for w, v in pairs) / total, 4)


def outage_metrics(
    packets: pd.DataFrame,
    failure_ts: float,
    services_by_ip: dict[str, str],
    core_ips: set[str],
    horizon_s: float = 20.0,
) -> dict[str, Any]:
    """Longest delivery gap and lost packets after a failure, per core-bound service."""
    if packets.empty:
        return {}
    data = packets.copy()
    data["service"] = data["flow"].map(lambda f: services_by_ip.get(f[0]))
    data["peer"] = data["flow"].map(lambda f: f[1])
    core = data[data["peer"].isin(core_ips) & data["service"].notna()]
    out: dict[str, Any] = {}
    for service, group in core.groupby("service"):
        window = group[(group["tx_ts"] >= failure_ts - 1.0) & (group["tx_ts"] <= failure_ts + horizon_s)]
        delivered = np.sort(window["rx_ts"].dropna().to_numpy())
        if len(delivered) < 2:
            out[service] = {"outage_s": horizon_s, "lost_packets": int(window["rx_ts"].isna().sum())}
            continue
        # Longest delivery gap in the failure window (packets already in flight
        # at the failure would otherwise make the outage look instantaneous).
        horizon_end = min(failure_ts + horizon_s, float(group["tx_ts"].max()))
        edges = np.concatenate([[failure_ts], delivered[delivered > failure_ts], [horizon_end]])
        gaps = np.diff(edges)
        k = int(np.argmax(gaps))
        gap_start, gap_end = edges[k], edges[k + 1]
        sent_in_gap = window[(window["tx_ts"] >= gap_start - 1.0) & (window["tx_ts"] <= gap_end)]
        out[service] = {
            "outage_s": round(float(gap_end - gap_start), 3),
            "lost_packets": int(sent_in_gap["rx_ts"].isna().sum()),
        }
    return out
