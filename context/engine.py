"""
Context Engine: infers the operating context (architecture.md §4.1).

Inputs: simulated clock (time of day, weekday, month → season), active alerts
(disaster, medical, infrastructure) and administrative policy overrides.
Output: one of the scenario-registry context ids.

Precedence (highest first):
  1. administrative override
  2. alerts (medical_emergency > disaster > fiber_cut)
  3. school hours on school days
  4. harvest season during daylight
  5. normal
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from core.config import load_yaml

ALERT_CONTEXTS = {
    "medical_emergency": "medical_emergency",
    "flood": "disaster",
    "fire": "disaster",
    "earthquake": "disaster",
    "disaster": "disaster",
    "fiber_cut": "fiber_cut",
}
ALERT_PRECEDENCE = ["medical_emergency", "disaster", "fiber_cut"]


class ContextInferenceEngine:
    """Rule-based context inference over a (simulated) clock and event feed."""

    def __init__(
        self,
        timeline: str | None = None,
        fixed_context: str | None = None,
        start: datetime | None = None,
        minutes_per_tick: float = 10.0,
    ):
        registry = load_yaml("timelines.yaml")
        self.calendar = registry.get("calendar", {})
        spec = registry.get("timelines", {}).get(timeline, {}) if timeline else {}
        if timeline and not spec:
            raise ValueError(f"unknown timeline: {timeline}")
        self.timeline = timeline
        self.fixed_context = fixed_context
        self.start = start or (
            datetime.fromisoformat(spec["start"]) if spec.get("start") else datetime(2026, 6, 15, 12)
        )
        self.minutes_per_tick = spec.get("minutes_per_tick", minutes_per_tick)
        self.events = sorted(spec.get("events", []), key=lambda e: e["tick"])
        self.active_alerts: set[str] = set()
        self.admin_override: str | None = None
        self.history: list[dict[str, Any]] = []

    def clock(self, tick: int) -> datetime:
        return self.start + timedelta(minutes=self.minutes_per_tick * tick)

    def raise_alert(self, alert: str):
        self.active_alerts.add(alert)

    def clear_alert(self, alert: str):
        self.active_alerts.discard(alert)

    def set_admin_override(self, context: str | None):
        self.admin_override = context

    def _apply_events(self, tick: int):
        for event in self.events:
            if event["tick"] != tick:
                continue
            if "alert" in event:
                self.raise_alert(event["alert"])
            if "clear" in event:
                self.clear_alert(event["clear"])
            if "admin" in event:
                self.set_admin_override(event["admin"])

    def infer(self, now: datetime) -> tuple[str, str]:
        """(context_id, reason) for the current inputs."""
        if self.admin_override:
            return self.admin_override, "admin override"
        alert_contexts = {ALERT_CONTEXTS.get(a, "disaster") for a in self.active_alerts}
        for context in ALERT_PRECEDENCE:
            if context in alert_contexts:
                return context, f"alert: {', '.join(sorted(self.active_alerts))}"
        if self.fixed_context:
            return self.fixed_context, "fixed scenario"

        school_start, school_end = self.calendar.get("school_hours", [8, 15])
        if now.weekday() in self.calendar.get("school_days", [0, 1, 2, 3, 4]) and (
            school_start <= now.hour < school_end
        ):
            return "school", "school hours"
        harvest_start, harvest_end = self.calendar.get("harvest_hours", [6, 18])
        if now.month in self.calendar.get("harvest_months", []) and (
            harvest_start <= now.hour < harvest_end
        ):
            return "harvest", "harvest season"
        return "normal", "default"

    def step(self, tick: int) -> dict[str, Any]:
        self._apply_events(tick)
        now = self.clock(tick)
        context, reason = self.infer(now)
        changed = not self.history or self.history[-1]["context"] != context
        snapshot = {
            "tick": tick,
            "clock": now.isoformat(timespec="minutes"),
            "context": context,
            "reason": reason,
            "alerts": sorted(self.active_alerts),
            "changed": changed,
        }
        self.history.append(snapshot)
        return snapshot

    def get_history(self) -> list[dict[str, Any]]:
        return list(self.history)


class ContextManager:
    """Tracks per-tick scenario state snapshots during experiments."""

    def __init__(self):
        self.history: list[dict[str, Any]] = []

    def update_from_scenario(self, scenario_state: dict[str, Any]):
        self.history.append({
            "scenario_id": scenario_state.get("scenario_id", "normal"),
            "network_load_pct": scenario_state.get("network_load_pct", 50),
            "backhaul_degraded": scenario_state.get("backhaul_degraded", False),
            "tick": scenario_state.get("tick", 0),
        })

    def get_snapshot(self) -> dict[str, Any]:
        if self.history:
            return self.history[-1]
        return {"scenario_id": "normal", "network_load_pct": 40, "tick": 0}

    def get_history(self) -> list[dict[str, Any]]:
        return list(self.history)
