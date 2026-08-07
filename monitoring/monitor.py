"""
Continuous telemetry monitoring and SLA violation detection.
"""

from __future__ import annotations

from typing import Any

from core.config import load_applications


class Monitor:
    """Polls telemetry and detects SLA violations."""

    def __init__(self, sla_latency_ms: float = 100.0, sla_loss_pct: float = 5.0):
        self.sla_latency_ms = sla_latency_ms
        self.sla_loss_pct = sla_loss_pct
        self.applications = {a["application_id"]: a for a in load_applications()}
        self.violations: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []

    def check_snapshot(self, telemetry: dict[str, Any], flows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """Check a telemetry snapshot for SLA violations."""
        new_violations = []

        for flow in (flows or []):
            app_id = flow.get("application_id", "")
            app = self.applications.get(app_id, {})
            latency_req = app.get("latency_requirement_ms", self.sla_latency_ms)
            latency = flow.get("end_to_end_latency_ms", 0)
            loss = flow.get("packet_loss_rate", 0)

            if latency > latency_req:
                violation = {
                    "type": "latency",
                    "application_id": app_id,
                    "service_class": flow.get("service_class", "unknown"),
                    "measured_ms": latency,
                    "threshold_ms": latency_req,
                    "tick": telemetry.get("tick", 0),
                }
                new_violations.append(violation)

            if loss > self.sla_loss_pct:
                violation = {
                    "type": "packet_loss",
                    "application_id": app_id,
                    "service_class": flow.get("service_class", "unknown"),
                    "measured_pct": loss,
                    "threshold_pct": self.sla_loss_pct,
                    "tick": telemetry.get("tick", 0),
                }
                new_violations.append(violation)

        if telemetry.get("tc_drops", 0) > 100:
            new_violations.append({
                "type": "queue_overflow",
                "tc_drops": telemetry["tc_drops"],
                "tick": telemetry.get("tick", 0),
            })

        self.violations.extend(new_violations)
        self.history.append({
            "tick": telemetry.get("tick", 0),
            "violation_count": len(new_violations),
            "telemetry": telemetry,
        })
        return new_violations

    def get_violations(self) -> list[dict[str, Any]]:
        return list(self.violations)

    def is_healthy(self) -> bool:
        recent = self.history[-5:] if self.history else []
        return all(h["violation_count"] == 0 for h in recent)

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_violations": len(self.violations),
            "healthy": self.is_healthy(),
            "snapshots_checked": len(self.history),
            "violation_types": self._count_by_type(),
        }

    def _count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for v in self.violations:
            vtype = v.get("type", "unknown")
            counts[vtype] = counts.get(vtype, 0) + 1
        return counts
