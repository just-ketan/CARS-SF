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
        self._prev_class_bytes: dict[str, float] = {}
        self.history: list[dict[str, float]] = []

    def observe(self, snapshot: dict[str, Any], allocation: dict[str, float]) -> dict[str, float]:
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
        stats = snapshot.get("tc_downlink_class_stats") or {}
        offered = {}
        for service, s in stats.items():
            sent = s.get("sent_bytes", 0)
            pkts = max(s.get("sent_packets", 0), 1)
            volume = sent + s.get("dropped", 0) * sent / pkts   # dropped bytes ≈ mean size
            prev = self._prev_class_bytes.get(service)
            self._prev_class_bytes[service] = volume
            if prev is not None:
                offered[service] = max(volume - prev, 0) * 8 / interval / 1e6
        return offered

    def estimate(self) -> dict[str, float]:
        """Forecast demand for the next control interval (prior until data arrives)."""
        if not self.history:
            return dict(self.prior)
        return {s: round(self.forecasters[s].forecast(self.horizon), 3) for s in SERVICES}


class OracleDemandEstimator:
    """Uses the scenario registry demand directly (upper bound / ablation)."""

    def __init__(self, prior: dict[str, float]):
        self.prior = dict(prior)
        self.history: list[dict[str, float]] = []

    def observe(self, snapshot, allocation) -> dict[str, float]:
        return dict(self.prior)

    def estimate(self) -> dict[str, float]:
        return dict(self.prior)
