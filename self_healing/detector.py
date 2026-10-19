"""
Failure detection from telemetry signatures (architecture.md §4.7).

Reactive detection works on each telemetry snapshot plus timestamped link
events from the 50 ms link watcher. ``PredictiveDetector`` fits short-horizon
trends to per-service RTT and forecasts SLA violations before they happen.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

import numpy as np

from topology.rural_topology import BACKHAUL_INTF

EDGE_SERVICES = ("healthcare", "agriculture")   # probe targets in the edge cloud
CORE_SERVICES = ("education", "general")        # probe targets behind the backhaul


class FailureDetector:
    """Detects network failures from per-tick telemetry snapshots."""

    QUEUE_DROP_THRESHOLD = 50          # packets dropped at the bottleneck per tick
    LINK_SATURATION_PCT = 95
    LATENCY_SPIKE_THRESHOLD_MS = 200
    BACKHAUL_ACTIVE_MBPS = 1.0         # below this the backhaul is considered idle

    def __init__(self):
        self.detected_failures: list[dict[str, Any]] = []
        self._prev_snapshot: dict[str, Any] | None = None
        self._backhaul_failed = False

    def analyze(self, telemetry: dict[str, Any]) -> list[dict[str, Any]]:
        failures = []
        tick = telemetry.get("tick", 0)

        if telemetry.get("tc_drops", 0) > self.QUEUE_DROP_THRESHOLD:
            failures.append({
                "type": "congestion",
                "severity": "high",
                "tc_drops": telemetry["tc_drops"],
                "tick": tick,
            })

        if telemetry.get("link_utilization_pct", 0) > self.LINK_SATURATION_PCT:
            failures.append({
                "type": "link_saturation",
                "severity": "medium",
                "utilization_pct": telemetry["link_utilization_pct"],
                "tick": tick,
            })

        failures.extend(self._link_state_failures(telemetry, tick))

        rtts = telemetry.get("service_rtt_ms") or {}
        if rtts and all(rtt is None for rtt in rtts.values()):
            failures.append({
                "type": "connectivity_loss",
                "severity": "critical",
                "tick": tick,
            })
        elif rtts and all(rtts.get(s) is None for s in CORE_SERVICES) and any(
            rtts.get(s) is not None for s in EDGE_SERVICES
        ):
            failures.append({
                "type": "core_unreachable",
                "severity": "critical",
                "tick": tick,
                "timestamp": telemetry.get("timestamp"),
            })
        for service, rtt in rtts.items():
            if rtt is not None and rtt > self.LATENCY_SPIKE_THRESHOLD_MS:
                failures.append({
                    "type": "latency_spike",
                    "severity": "high",
                    "service_class": service,
                    "rtt_ms": rtt,
                    "tick": tick,
                })

        self.detected_failures.extend(failures)
        self._prev_snapshot = dict(telemetry)
        return failures

    def analyze_link_events(self, events: list[dict[str, Any]], tick: int) -> list[dict[str, Any]]:
        """Fast path: link-watcher events between ticks (does not touch snapshot state)."""
        failures = self._from_link_events(events, tick)
        self.detected_failures.extend(failures)
        return failures

    def _from_link_events(self, events: list[dict[str, Any]], tick: int) -> list[dict[str, Any]]:
        failures = []
        for event in events:
            if event["intf"] != BACKHAUL_INTF:
                continue
            if not event["up"] and not self._backhaul_failed:
                self._backhaul_failed = True
                failures.append({
                    "type": "fiber_cut", "severity": "critical", "tick": tick,
                    "timestamp": event["timestamp"], "source": "link_watcher",
                })
            elif event["up"] and self._backhaul_failed:
                self._backhaul_failed = False
                failures.append({
                    "type": "primary_restored", "severity": "info", "tick": tick,
                    "timestamp": event["timestamp"], "source": "link_watcher",
                })
        return failures

    def _link_state_failures(self, telemetry: dict[str, Any], tick: int) -> list[dict[str, Any]]:
        failures = self._from_link_events(telemetry.get("link_events", []), tick)
        if not failures and not self._backhaul_failed and self._is_backhaul_cut(telemetry):
            self._backhaul_failed = True
            failures.append({
                "type": "fiber_cut", "severity": "critical", "tick": tick,
                "timestamp": telemetry.get("timestamp"),
                "backhaul_up": telemetry.get("backhaul_up"),
                "backhaul_throughput_mbps": telemetry.get("backhaul_throughput_mbps"),
                "source": "snapshot",
            })
        elif not failures and self._backhaul_failed and telemetry.get("backhaul_up") is True:
            self._backhaul_failed = False
            failures.append({
                "type": "primary_restored", "severity": "info", "tick": tick,
                "timestamp": telemetry.get("timestamp"), "source": "snapshot",
            })
        return failures

    def _is_backhaul_cut(self, telemetry: dict[str, Any]) -> bool:
        # Direct signal: primary backhaul lost carrier and no backup is carrying
        # traffic. When link state is reported it is authoritative, because a
        # throughput collapse alone cannot be told apart from sources going quiet.
        if "backhaul_up" in telemetry:
            return telemetry["backhaul_up"] is False and not telemetry.get("backup_backhaul_up")

        if self._prev_snapshot is None:
            return False

        # Fallback signal: backhaul throughput collapses by >90% in one tick
        # (only on healthy telemetry: missing counters are not a collapse).
        if (telemetry.get("telemetry_health") or {}).get("missing_interfaces"):
            return False
        prev_tput = self._prev_snapshot.get("backhaul_throughput_mbps")
        curr_tput = telemetry.get("backhaul_throughput_mbps")
        if prev_tput is not None and curr_tput is not None:
            return prev_tput > self.BACKHAUL_ACTIVE_MBPS and curr_tput < prev_tput * 0.1

        # Legacy snapshots carrying per-tick byte counts only.
        prev_bytes = self._prev_snapshot.get("ovs_bytes", 0)
        curr_bytes = telemetry.get("ovs_bytes", 0)
        return prev_bytes > 1000 and curr_bytes < prev_bytes * 0.1

    def get_failures(self) -> list[dict[str, Any]]:
        return list(self.detected_failures)


class PredictiveDetector:
    """Forecasts SLA violations from RTT trends (linear fit over a sliding window).

    A *backhaul degradation* is predicted when every core-bound service's RTT
    trend crosses its threshold within ``horizon_ticks`` while edge-bound
    services stay flat: the shared factor is the backhaul, not the slices.
    """

    def __init__(
        self,
        thresholds_ms: dict[str, float],
        window: int = 6,
        horizon_ticks: int = 5,
        min_slope_ms: float = 2.0,
    ):
        self.thresholds = thresholds_ms
        self.window = window
        self.horizon = horizon_ticks
        self.min_slope = min_slope_ms
        self.samples: dict[str, deque] = defaultdict(lambda: deque(maxlen=window))
        self.predictions: list[dict[str, Any]] = []

    def _trend(self, service: str) -> tuple[float, float] | None:
        points = [(t, v) for t, v in self.samples[service] if v is not None]
        if len(points) < max(4, self.window // 2):
            return None
        t, v = np.array(points, dtype=float).T
        slope, intercept = np.polyfit(t, v, 1)
        return float(slope), float(intercept)

    CONGESTION_UTILISATION_PCT = 90
    CONGESTION_BACKLOG_BYTES = 30_000    # ≈ 2.4 ms of queue at 100 Mbps

    def local_congestion(self, telemetry: dict[str, Any]) -> bool:
        """Evidence that rising RTT comes from the local bottleneck, not the backhaul.

        Congestion grows a queue (and drops packets) at the rural uplink;
        backhaul degradation adds delay beyond it with the local queues empty.
        """
        if telemetry.get("tc_drops", 0) > 0:
            return True
        if telemetry.get("link_utilization_pct", 0) >= self.CONGESTION_UTILISATION_PCT:
            return True
        backlog = telemetry.get("queue_bytes") or {}
        core = [backlog.get(s, 0) for s in CORE_SERVICES] or [backlog.get("aggregate", 0)]
        return max(core + [backlog.get("aggregate", 0)]) > self.CONGESTION_BACKLOG_BYTES

    def observe(self, telemetry: dict[str, Any]) -> list[dict[str, Any]]:
        tick = telemetry.get("tick", 0)
        congested = self.local_congestion(telemetry)
        self.recent_congestion = getattr(self, "recent_congestion", [])[-(self.window - 1):] + [congested]
        for service, rtt in (telemetry.get("service_rtt_ms") or {}).items():
            self.samples[service].append((tick, rtt))

        forecasts = {}
        for service in list(self.samples):
            trend = self._trend(service)
            if trend is None:
                continue
            slope, intercept = trend
            forecasts[service] = (slope, slope * (tick + self.horizon) + intercept)

        predictions = []
        core = [forecasts.get(s) for s in CORE_SERVICES]
        edge = [forecasts.get(s) for s in EDGE_SERVICES]
        # A shared backhaul affects every core-bound slice alike: act when the
        # common rising trend will breach the *strictest* core-bound threshold.
        strictest = min(self.thresholds.get(s, 150) for s in CORE_SERVICES)
        if all(core) and all(slope >= self.min_slope for slope, _ in core) and (
            max(value for _, value in core) >= strictest
        ) and all(e is None or e[0] < self.min_slope for e in edge) and not any(self.recent_congestion):
            predictions.append({
                "type": "predicted_backhaul_degradation",
                "severity": "warning",
                "tick": tick,
                "timestamp": telemetry.get("timestamp"),
                "forecast_rtt_ms": {s: round(f[1], 1) for s, f in zip(CORE_SERVICES, core)},
            })
        self.predictions.extend(predictions)
        return predictions
