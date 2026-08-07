"""
Failure detection from telemetry signatures.
"""

from __future__ import annotations

from typing import Any


class FailureDetector:
    """Detects network failures from telemetry patterns."""

    QUEUE_DROP_THRESHOLD = 50
    LATENCY_SPIKE_THRESHOLD_MS = 200
    LOSS_SPIKE_THRESHOLD_PCT = 10

    def __init__(self):
        self.detected_failures: list[dict[str, Any]] = []
        self._prev_snapshot: dict[str, Any] | None = None

    def analyze(self, telemetry: dict[str, Any]) -> list[dict[str, Any]]:
        failures = []

        if telemetry.get("tc_drops", 0) > self.QUEUE_DROP_THRESHOLD:
            failures.append({
                "type": "congestion",
                "severity": "high",
                "tc_drops": telemetry["tc_drops"],
                "tick": telemetry.get("tick", 0),
            })

        if telemetry.get("link_utilization_pct", 0) > 95:
            failures.append({
                "type": "link_saturation",
                "severity": "medium",
                "utilization_pct": telemetry["link_utilization_pct"],
                "tick": telemetry.get("tick", 0),
            })

        if self._prev_snapshot:
            prev_bytes = self._prev_snapshot.get("ovs_bytes", 0)
            curr_bytes = telemetry.get("ovs_bytes", 0)
            if prev_bytes > 1000 and curr_bytes < prev_bytes * 0.1:
                failures.append({
                    "type": "fiber_cut",
                    "severity": "critical",
                    "prev_bytes": prev_bytes,
                    "curr_bytes": curr_bytes,
                    "tick": telemetry.get("tick", 0),
                })

        self.detected_failures.extend(failures)
        self._prev_snapshot = dict(telemetry)
        return failures

    def get_failures(self) -> list[dict[str, Any]]:
        return list(self.detected_failures)
