"""
Context Generator

Generates realistic network context for a traffic flow based on
the selected network scenario.
"""

import random

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.enums import SliceType

from .application_profile import ApplicationProfile
from .scenarios import Scenario


class ContextGenerator:

    def __init__(self, seed: int | None = None):

        self.random = random.Random(seed)

    def generate(
        self,
        profile: ApplicationProfile,
        scenario: Scenario,
        clock=None,
    ) -> ContextRecord:

        if clock:
            time_multiplier = clock.get_time_multiplier()
            # Add some randomness (±10%) to the multiplier
            time_multiplier *= self.random.uniform(0.9, 1.1)

            if clock.is_rush_hour:
                time_of_day_str = f"rush_hour ({clock.time_string})"
            elif clock.is_night:
                time_of_day_str = f"night ({clock.time_string})"
            else:
                time_of_day_str = f"day ({clock.time_string})"
                
            active_users = int(
                scenario.active_users_range[0] + 
                (scenario.active_users_range[1] - scenario.active_users_range[0]) * time_multiplier
            )
            
            network_load = scenario.network_load_range[0] + (scenario.network_load_range[1] - scenario.network_load_range[0]) * time_multiplier
            cell_load = network_load * self.random.uniform(0.9, 1.1)
        else:
            time_of_day_str = "day"
            
            network_load = self.random.uniform(*scenario.network_load_range)
            cell_load = self.random.uniform(*scenario.cell_load_range)
            active_users = self.random.randint(int(scenario.active_users_range[0]), int(scenario.active_users_range[1]))
            
        network_load = min(100.0, max(0.0, network_load))
        cell_load = min(100.0, max(0.0, cell_load))

        cqi = self.random.randint(int(scenario.cqi_range[0]), int(scenario.cqi_range[1]))

        rsrp = self.random.uniform(*scenario.rsrp_range)
        rsrq = self.random.uniform(*scenario.rsrq_range)
        sinr = self.random.uniform(*scenario.sinr_range)

        return ContextRecord(

            service_type=profile.service_class.value,
            application_name=profile.name,
            slice_type=profile.slice_type.value,
            service_priority=profile.priority.value,
            network_load_pct=network_load,
            cell_load_pct=cell_load,
            active_users=active_users,
            device_type=profile.device_type.value,
            mobility_state=profile.mobility.value,
            time_of_day=time_of_day_str,
            signal_strength_dbm=rsrp,
            sinr_db=sinr,
            rsrp_dbm=rsrp,
            rsrq_db=rsrq,
            cqi=cqi,
            network_slice_id=profile.slice_type.value,
            slice_resource_utilization_pct=self.random.uniform(*scenario.slice_utilization_range),
            radio_resource_blocks_used=self.random.randint(*scenario.resource_blocks_range),

            handover_in_progress=self.random.random() < 0.05,
        )