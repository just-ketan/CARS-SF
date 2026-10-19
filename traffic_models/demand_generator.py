class DemandGenerator:

    def get_demands(self, context):

        registry_demands = _registry_demands().get(context)
        if registry_demands:
            return dict(registry_demands)

        if context == "school":

            return {
                "healthcare": 5,
                "education": 80,
                "agriculture": 10,
                "general": 50
            }

        elif context == "harvest":

            return {
                "healthcare": 5,
                "education": 20,
                "agriculture": 80,
                "general": 50
            }

        elif context == "disaster":

            return {
                "healthcare": 90,
                "education": 5,
                "agriculture": 5,
                "general": 20
            }

        return {
            "healthcare": 20,
            "education": 20,
            "agriculture": 20,
            "general": 20
        }

    def get_demands_for_scenario(self, scenario: dict) -> dict[str, float]:
        return scenario.get("demand_mbps", self.get_demands(scenario.get("id", "normal")))


def _registry_demands():
    """Scenario registry is the source of truth; the table above is a fallback."""
    try:
        from core.config import load_scenarios
        return {s["id"]: s["demand_mbps"] for s in load_scenarios() if "demand_mbps" in s}
    except Exception:
        return {}
