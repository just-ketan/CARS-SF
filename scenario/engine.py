"""Scenario state machine driven by registry definitions."""

from __future__ import annotations

from typing import Any

from core.config import load_scenarios


class ScenarioOrchestrator:
    """Manages scenario transitions during an experiment."""

    def __init__(self, scenario_id: str = "normal"):
        self.scenarios = {s["id"]: s for s in load_scenarios()}
        self.scenario_id = scenario_id
        self.tick = 0

    def tick_advance(self) -> dict[str, Any]:
        scenario = self.scenarios.get(self.scenario_id, self.scenarios["normal"])
        self.tick += 1
        return {
            "scenario_id": self.scenario_id,
            "name": scenario["name"],
            "tick": self.tick,
            "priority_weights": scenario.get("priority_weights", {}),
            "demand_mbps": scenario.get("demand_mbps", {}),
            "network_load_pct": scenario.get("network_load_pct", 50),
            "backhaul_degraded": scenario.get("backhaul_degraded", False),
        }

    def set_scenario(self, scenario_id: str):
        if scenario_id in self.scenarios:
            self.scenario_id = scenario_id
            self.tick = 0

    def get_scenario(self) -> dict[str, Any]:
        return self.scenarios.get(self.scenario_id, self.scenarios["normal"])
