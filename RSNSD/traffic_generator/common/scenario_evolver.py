"""
Scenario Evolver

Handles dynamic progression and evolution of scenarios over time.
"""

from .scenarios import NORMAL_DAY as NORMAL, SCHOOL_HOURS, HARVEST, DISASTER, FESTIVAL, Scenario
from .clock import SimulationClock
from dataclasses import replace

class ScenarioEvolver:
    
    def __init__(self, base_scenario: Scenario):
        self.base_scenario = base_scenario

    def evolve(self, clock: SimulationClock) -> Scenario:
        """
        Returns a modified scenario based on the time of day and the specific progression.
        """
        name = self.base_scenario.name
        
        # Base multiplier logic
        if name == "School Hours":
            # School opening (escalation between 8 and 9)
            if 8 <= clock.hour < 9:
                progression = (clock.minute) / 60.0
                return self._scale_scenario(NORMAL, self.base_scenario, progression)
            # School closing
            elif 15 <= clock.hour < 16:
                progression = (clock.minute) / 60.0
                return self._scale_scenario(self.base_scenario, NORMAL, progression)
            elif clock.is_school_hours:
                return self.base_scenario
            else:
                return NORMAL
                
        elif name == "Harvest":
            # Harvest progression (escalates through the morning)
            if 6 <= clock.hour < 12:
                progression = ((clock.hour - 6) * 60 + clock.minute) / 360.0
                return self._scale_scenario(NORMAL, self.base_scenario, progression)
            elif 12 <= clock.hour < 18:
                return self.base_scenario
            elif 18 <= clock.hour < 20:
                progression = ((clock.hour - 18) * 60 + clock.minute) / 120.0
                return self._scale_scenario(self.base_scenario, NORMAL, progression)
            else:
                return NORMAL
                
        elif name == "Disaster":
            # Disaster escalation (rapid)
            if 10 <= clock.hour < 11:
                progression = (clock.minute) / 60.0
                return self._scale_scenario(NORMAL, self.base_scenario, progression)
            # Disaster peaks
            elif 11 <= clock.hour < 16:
                return self.base_scenario
            # Recovery phase (slow)
            elif 16 <= clock.hour < 24:
                progression = ((clock.hour - 16) * 60 + clock.minute) / (8 * 60.0)
                return self._scale_scenario(self.base_scenario, NORMAL, progression)
            else:
                return NORMAL
                
        elif name == "Festival":
            # Crowd evolution (gradual build up)
            if 14 <= clock.hour < 18:
                progression = ((clock.hour - 14) * 60 + clock.minute) / 240.0
                return self._scale_scenario(NORMAL, self.base_scenario, progression)
            elif 18 <= clock.hour < 22:
                return self.base_scenario
            elif 22 <= clock.hour < 24:
                progression = ((clock.hour - 22) * 60 + clock.minute) / 120.0
                return self._scale_scenario(self.base_scenario, NORMAL, progression)
            else:
                return NORMAL
                
        return self.base_scenario

    def _scale_scenario(self, s1: Scenario, s2: Scenario, factor: float) -> Scenario:
        """
        Linearly interpolate between two scenarios.
        """
        def lerp(v1, v2, f):
            return v1 + (v2 - v1) * f
            
        return replace(
            s1,
            network_load_range=(
                lerp(s1.network_load_range[0], s2.network_load_range[0], factor),
                lerp(s1.network_load_range[1], s2.network_load_range[1], factor)
            ),
            cell_load_range=(
                lerp(s1.cell_load_range[0], s2.cell_load_range[0], factor),
                lerp(s1.cell_load_range[1], s2.cell_load_range[1], factor)
            ),
            active_users_range=(
                int(lerp(s1.active_users_range[0], s2.active_users_range[0], factor)),
                int(lerp(s1.active_users_range[1], s2.active_users_range[1], factor))
            ),
            cqi_range=(
                int(lerp(s1.cqi_range[0], s2.cqi_range[0], factor)),
                int(lerp(s1.cqi_range[1], s2.cqi_range[1], factor))
            ),
            rsrp_range=(
                lerp(s1.rsrp_range[0], s2.rsrp_range[0], factor),
                lerp(s1.rsrp_range[1], s2.rsrp_range[1], factor)
            ),
            slice_utilization_range=(
                lerp(s1.slice_utilization_range[0], s2.slice_utilization_range[0], factor),
                lerp(s1.slice_utilization_range[1], s2.slice_utilization_range[1], factor)
            ),
            service_bias_multiplier=lerp(s1.service_bias_multiplier, s2.service_bias_multiplier, factor)
        )
