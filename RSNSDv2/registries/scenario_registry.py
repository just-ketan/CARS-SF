from dataclasses import dataclass

@dataclass
class ScenarioProfile:
    scenario_id: str
    name: str
    trigger_condition: str
    duration_s: int
    # Multipliers for application demands
    demand_multipliers: dict # e.g. {"Healthcare": 1.0, "Agriculture": 2.5}
    # Fault injections active during this scenario
    active_faults: list

class ScenarioRegistry:
    def __init__(self):
        self.scenarios = [
            ScenarioProfile(
                "SCN_001", "Normal", "Default", 0,
                {"Healthcare": 1.0, "Agriculture": 1.0, "Education": 1.0, "General": 1.0},
                []
            ),
            ScenarioProfile(
                "SCN_002", "School Hours", "Time 09:00-15:00", 3600,
                {"Healthcare": 1.0, "Agriculture": 1.0, "Education": 3.0, "General": 1.5},
                []
            ),
            ScenarioProfile(
                "SCN_003", "Harvest", "Time 16:00-18:00", 7200,
                {"Healthcare": 1.0, "Agriculture": 4.0, "Education": 1.0, "General": 1.0},
                []
            ),
            ScenarioProfile(
                "SCN_004", "Backhaul Failure", "Random Trigger", 120,
                {"Healthcare": 1.0, "Agriculture": 1.0, "Education": 1.0, "General": 1.0},
                [{"type": "link_degrade", "target": ("s2", "s3"), "bw_pct": 0.1, "delay_add": "200ms"}]
            ),
            ScenarioProfile(
                "SCN_005", "Festival", "Scheduled Event", 14400,
                {"Healthcare": 1.0, "Agriculture": 0.5, "Education": 0.5, "General": 5.0},
                []
            )
        ]

    def get_scenario(self, name: str):
        for scn in self.scenarios:
            if scn.name == name:
                return scn
        return self.scenarios[0]
