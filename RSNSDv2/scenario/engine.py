from RSNSDv2.registries.scenario_registry import ScenarioRegistry

class ScenarioOrchestrator:
    """
    Phase 3: Scenario Engine
    Continuously evolve network state to simulate realistic temporal changes.
    """
    def __init__(self, context_manager):
        self.context_manager = context_manager
        self.tick_count = 0
        self.registry = ScenarioRegistry()
        self.current_scenario = self.registry.get_scenario("Normal")

    def tick(self):
        self.tick_count += 1
        
        # Evolve scenario over time based on ticks
        # Normal for first 10, then School Hours, then Disaster
        if self.tick_count == 10:
            self.current_scenario = self.registry.get_scenario("School Hours")
        elif self.tick_count == 30:
            self.current_scenario = self.registry.get_scenario("Backhaul Failure")
            self.context_manager.power_grid = "Failing"
        elif self.tick_count == 45:
            self.current_scenario = self.registry.get_scenario("Normal")
            self.context_manager.power_grid = "Stable"
            
        return self.current_scenario

