"""
Demand estimation (architecture.md §4.2): from measurements, not reservations.

Offered load per service is observed where it is still unshaped:
  * uplink   – rx bytes on the UEs' switch access ports (before the bottleneck)
  * downlink – HTB class sent + dropped volume on the edge downlink (offered to
               the bottleneck); without QoS, delivered tx on the access ports

Elastic (TCP) traffic adapts to whatever it is given, so its true demand is not
observable from throughput alone. When a slice runs at ≥ 90 % of its
allocation the estimate is raised by ``headroom`` to probe for more demand.

Estimates are smoothed (EWMA) and forecast one control interval ahead with
Holt's linear trend method.
"""

from __future__ import annotations

from typing import Any

from collections import deque

from slicing.directions import DIRECTIONS, DOWNLINK, UPLINK, elastic_directions, split_demand

SERVICES = ("healthcare", "education", "agriculture", "general")


class HoltForecaster:
    """Double exponential smoothing (level + trend)."""

    def __init__(self, alpha: float = 0.5, beta: float = 0.3):
        self.alpha, self.beta = alpha, beta
        self.level: float | None = None
        self.trend = 0.0

    def update(self, value: float) -> float:
        if self.level is None:
            self.level, self._first = value, True
            return value
        if self._first:  # standard initialisation: trend from the first two points
            self.trend, self.level, self._first = value - self.level, value, False
            return value
        prev = self.level
        self.level = self.alpha * value + (1 - self.alpha) * (self.level + self.trend)
        self.trend = self.beta * (self.level - prev) + (1 - self.beta) * self.trend
        return self.level

    def forecast(self, steps: int = 1) -> float:
        return max(0.0, (self.level or 0.0) + steps * self.trend)


class MeasuredDemandEstimator:
    """Measured, smoothed and forecast per-service demand (Mbps)."""

    def __init__(
        self,
        prior: dict[str, float] | None = None,
        headroom: float = 1.25,
        saturation: float = 0.9,
        horizon_ticks: int = 1,
    ):
        self.prior = dict(prior or {})
        self.headroom = headroom
        self.saturation = saturation
        self.horizon = horizon_ticks
        self.forecasters = {s: HoltForecaster() for s in SERVICES}
        # Per-direction forecasts for direction-aware schedulers (slicing/directions.py).
        self.dir_forecasters = {d: {s: HoltForecaster() for s in SERVICES} for d in DIRECTIONS}
        self.dir_recent = {d: {s: deque(maxlen=10) for s in SERVICES} for d in DIRECTIONS}
        self.elastic = elastic_directions()
        self._prev_class_bytes: dict[str, float] = {}
        self._prev_up_class_bytes: dict[str, float] = {}
        self.history: list[dict[str, float]] = []

    def observe(self, snapshot: dict[str, Any], allocation: dict[str, float],
                directional_allocation: dict[str, dict[str, float]] | None = None) -> dict[str, float]:
        """Fold one telemetry snapshot in; returns the raw measured offered load.

        Snapshots whose counters are unavailable are skipped (the forecast keeps
        its last state) rather than read as zero demand.
        """
        health = snapshot.get("telemetry_health") or {}
        if health.get("services_without_counters"):
            self.skipped = getattr(self, "skipped", 0) + 1
            return {}
        interval = max(snapshot.get("interval_s", 1.0), 1e-3)
        uplink = snapshot.get("service_throughput_mbps", {})
        downlink = self._downlink_offered(snapshot, interval) or snapshot.get("service_downlink_mbps", {})
        measured = {}
        # Direction-aware estimates use the bottleneck's per-class counters for the uplink
        # too, so demand is counted in the class a flow is actually queued in (SliceNet
        # decisions included); host access-port counters are the fallback.
        uplink_by_class = self._class_offered(snapshot, "tc_class_stats", interval, self._prev_up_class_bytes)
        for direction, offered_dir, key in ((UPLINK, uplink_by_class or uplink, "tc_class_stats"),
                                            (DOWNLINK, downlink, "tc_downlink_class_stats")):
            dir_alloc = (directional_allocation or {}).get(direction, {})
            stats = snapshot.get(key) or {}
            for service in SERVICES:
                value = offered_dir.get(service, 0.0)
                alloc = dir_alloc.get(service, 0.0)
                # Direction-aware allocations include burst headroom, so a constant-rate
                # stream runs at ~90 % of its allocation. Probe up only on evidence that
                # the slice is actually saturated: a standing queue or drops.
                cls = stats.get(service) or {}
                queued = max(cls.get("backlog_bytes", 0), cls.get("leaf_backlog_bytes", 0)) > 3000
                elastic = direction in self.elastic.get(service, set())
                if elastic and alloc > 0 and value >= self.saturation * alloc and queued:
                    value = max(value, alloc * self.headroom)
                self.dir_forecasters[direction][service].update(value)
                self.dir_recent[direction][service].append(value)
        for service in SERVICES:
            offered = uplink.get(service, 0.0) + downlink.get(service, 0.0)
            alloc = allocation.get(service, 0.0)
            if alloc > 0 and offered >= self.saturation * alloc:
                offered = max(offered, alloc * self.headroom)   # elastic probe-up
            self.forecasters[service].update(offered)
            measured[service] = round(offered, 3)
        self.history.append(measured)
        return measured

    def _downlink_offered(self, snapshot: dict[str, Any], interval: float) -> dict[str, float]:
        return self._class_offered(snapshot, "tc_downlink_class_stats", interval, self._prev_class_bytes)

    @staticmethod
    def _class_offered(snapshot: dict[str, Any], key: str, interval: float, prev_store: dict) -> dict[str, float]:
        """Offered load per class at the bottleneck: Δ(sent + dropped bytes) / interval."""
        stats = snapshot.get(key) or {}
        offered = {}
        for service, s in stats.items():
            if service not in SERVICES:
                continue
            sent = s.get("sent_bytes", 0)
            pkts = max(s.get("sent_packets", 0), 1)
            volume = sent + s.get("dropped", 0) * sent / pkts   # dropped bytes ≈ mean size
            prev = prev_store.get(service)
            prev_store[service] = volume
            if prev is not None:
                offered[service] = max(volume - prev, 0) * 8 / interval / 1e6
        return offered

    def estimate(self) -> dict[str, float]:
        """Forecast demand for the next control interval (prior until data arrives)."""
        if not self.history:
            return dict(self.prior)
        return {s: round(self.forecasters[s].forecast(self.horizon), 3) for s in SERVICES}

    def estimate_directional(self, trend: bool = False, horizon_ticks: int = 2) -> dict[str, dict[str, float]]:
        """Per-direction demand: the mean of the last control interval.

        With ``trend`` (predictive schedulers), a consistent rise over the window
        (least-squares slope > 0 with R² ≥ 0.6) is extrapolated ``horizon_ticks``
        past the latest sample, capped at 1.5 × the window's peak: the allocation
        then leads a ramp instead of trailing it by half a window.
        """
        if not self.history:
            return split_demand(self.prior)
        # Demand = mean offered rate over the last control interval (5 samples).
        # Per-second samples of VBR traffic fluctuate around the mean; following
        # them (or their trend) chases bursts, which are the allocator's headroom
        # to absorb, not demand. Elastic probe-up values enter the mean as measured.
        out = {}
        for d in DIRECTIONS:
            out[d] = {}
            for s in SERVICES:
                recent = list(self.dir_recent[d][s])[-self.WINDOW:]
                value = sum(recent) / len(recent) if recent else 0.0
                if trend and len(recent) >= 4:
                    value = max(value, _ramp_forecast(recent, horizon_ticks))
                out[d][s] = round(value, 3)
        return out

    WINDOW = 5


def _ramp_forecast(samples: list[float], horizon: int) -> float:
    n = len(samples)
    xs = list(range(n))
    mx, my = (n - 1) / 2, sum(samples) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, samples))
    syy = sum((y - my) ** 2 for y in samples)
    if sxx == 0 or syy == 0:
        return my
    slope = sxy / sxx
    r2 = sxy * sxy / (sxx * syy)
    if slope <= 0 or r2 < 0.6:
        return my
    predicted = my + slope * ((n - 1) - mx + horizon)
    return min(predicted, 1.5 * max(samples))


class OracleDemandEstimator:
    """Uses the scenario registry demand directly (upper bound / ablation)."""

    def __init__(self, prior: dict[str, float]):
        self.prior = dict(prior)
        self.history: list[dict[str, float]] = []

    def observe(self, snapshot, allocation, directional_allocation=None) -> dict[str, float]:
        return dict(self.prior)

    def estimate(self) -> dict[str, float]:
        return dict(self.prior)

    def estimate_directional(self, trend: bool = False, horizon_ticks: int = 2) -> dict[str, dict[str, float]]:
        return split_demand(self.prior)
