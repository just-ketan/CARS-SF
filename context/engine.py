"""Environmental context management."""

from __future__ import annotations

from typing import Any


class ContextManager:
    """Tracks environmental context snapshots during experiments."""

    def __init__(self):
        self.history: list[dict[str, Any]] = []
        self.weather = "Clear"
        self.power_grid = "Stable"

    def update_from_scenario(self, scenario_state: dict[str, Any]):
        load = scenario_state.get("network_load_pct", 50)
        if load > 90:
            self.weather = "Storm"
        elif load > 70:
            self.weather = "Rain"
        else:
            self.weather = "Clear"

        if scenario_state.get("backhaul_degraded"):
            self.power_grid = "Degraded"

        snapshot = {
            "weather": self.weather,
            "power_grid": self.power_grid,
            "scenario_id": scenario_state.get("scenario_id", "normal"),
            "network_load_pct": load,
            "tick": scenario_state.get("tick", 0),
        }
        self.history.append(snapshot)

    def get_snapshot(self) -> dict[str, Any]:
        if self.history:
            return self.history[-1]
        return {
            "weather": self.weather,
            "power_grid": self.power_grid,
            "scenario_id": "normal",
            "network_load_pct": 40,
            "tick": 0,
        }

    def get_history(self) -> list[dict[str, Any]]:
        return list(self.history)
