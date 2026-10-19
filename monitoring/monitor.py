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


class SliceMonitor:
    """Online per-slice SLA monitoring against ``registries/slices.yaml``.

    Per tick and slice: one-way latency (probe RTT / 2), loss (HTB drops per
    packet offered to the slice's classes, both directions) and demand
    satisfaction (delivered / offered-by-design throughput).
    """

    def __init__(self):
        from core.config import load_yaml

        self.slices = load_yaml("slices.yaml")["service_slices"]
        self.records: list[dict[str, Any]] = []
        self._prev_class: dict[str, tuple[int, int]] = {}

    def _loss_pct(self, snapshot: dict[str, Any], service: str) -> float | None:
        sent = drops = 0
        found = False
        for key in ("tc_class_stats", "tc_downlink_class_stats"):
            stats = (snapshot.get(key) or {}).get(service)
            if stats:
                found = True
                sent += stats["sent_packets"]
                drops += stats["dropped"]
        if not found:
            return None
        prev_sent, prev_drops = self._prev_class.get(service, (sent, drops))
        self._prev_class[service] = (sent, drops)
        d_sent, d_drops = sent - prev_sent, drops - prev_drops
        attempted = d_sent + d_drops
        return round(d_drops / attempted * 100, 3) if attempted > 0 else 0.0

    def check(self, snapshot: dict[str, Any], demands: dict[str, float]) -> list[dict[str, Any]]:
        rtts = snapshot.get("service_rtt_ms") or {}
        up = snapshot.get("service_throughput_mbps") or {}
        down = snapshot.get("service_downlink_mbps") or {}
        violations = []
        for service, cfg in self.slices.items():
            sla = cfg["sla"]
            rtt = rtts.get(service)
            latency = rtt / 2 if rtt is not None else None
            loss = self._loss_pct(snapshot, service)
            delivered = up.get(service, 0.0) + down.get(service, 0.0)
            demand = demands.get(service, 0.0)
            satisfaction = min(1.0, delivered / demand) if demand > 0 else 1.0
            record = {
                "tick": snapshot.get("tick", 0),
                "service_class": service,
                "latency_ms": latency,
                "loss_pct": loss,
                "satisfaction": round(satisfaction, 4),
                "latency_ok": latency is not None and latency <= sla["latency_ms"],
                "loss_ok": loss is None or loss <= sla["loss_pct"],
                "satisfaction_ok": satisfaction >= sla["min_satisfaction"],
            }
            record["sla_ok"] = record["latency_ok"] and record["loss_ok"] and record["satisfaction_ok"]
            self.records.append(record)
            if not record["sla_ok"]:
                violations.append(record)
        return violations

    def summary(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for service in self.slices:
            rows = [r for r in self.records if r["service_class"] == service]
            if not rows:
                continue
            lat = [r["latency_ms"] for r in rows if r["latency_ms"] is not None]
            out[service] = {
                "sla_compliance": round(sum(r["sla_ok"] for r in rows) / len(rows), 4),
                "latency_compliance": round(sum(r["latency_ok"] for r in rows) / len(rows), 4),
                "loss_compliance": round(sum(r["loss_ok"] for r in rows) / len(rows), 4),
                "mean_satisfaction": round(sum(r["satisfaction"] for r in rows) / len(rows), 4),
                "mean_probe_latency_ms": round(sum(lat) / len(lat), 2) if lat else None,
            }
        return out
