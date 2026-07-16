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
    ) -> ContextRecord:

        network_load = self.random.uniform(
            scenario.network_load_min,
            scenario.network_load_max,
        )

        cell_load = self.random.uniform(
            scenario.network_load_min,
            scenario.network_load_max,
        )

        active_users = self.random.randint(
            scenario.active_users_min,
            scenario.active_users_max,
        )

        cqi = self.random.randint(
            scenario.cqi_min,
            scenario.cqi_max,
        )

        rsrp = self.random.uniform(
            scenario.rsrp_min,
            scenario.rsrp_max,
        )

        rsrq = self.random.uniform(-15, -5)

        sinr = self.random.uniform(8, 30)

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

            time_of_day="day",

            signal_strength_dbm=rsrp,

            sinr_db=sinr,

            rsrp_dbm=rsrp,

            rsrq_db=rsrq,

            cqi=cqi,

            network_slice_id=profile.slice_type.value,

            slice_resource_utilization_pct=self.random.uniform(
                scenario.slice_utilization_min,
                scenario.slice_utilization_max,
            ),

            radio_resource_blocks_used=self.random.randint(
                20,
                260,
            ),

            handover_in_progress=self.random.random() < 0.05,
        )