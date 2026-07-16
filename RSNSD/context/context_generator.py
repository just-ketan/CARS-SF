"""
Scenario-Aware Context Generator

Generates realistic ContextRecord instances from a given
rural operating scenario.

Author: RSNSD
"""

import random

from RSNSD.domain.context import ContextRecord


class ContextGenerator:

    def __init__(self, seed: int | None = None):

        self.random = random.Random(seed)

    def generate(
        self,
        profile,
        scenario,
    ):

        return ContextRecord(

            network_load_pct=self.random.uniform(
                *scenario.network_load_range
            ),

            cell_load_pct=self.random.uniform(
                *scenario.cell_load_range
            ),

            active_users=self.random.randint(
                *scenario.active_users_range
            ),

            device_type=profile.device_type,

            mobility_state=profile.mobility,

            network_slice_id=profile.slice_type,

            time_of_day=scenario.daytime,

            signal_strength_dbm=self.random.uniform(
                *scenario.signal_strength_range
            ),

            sinr_db=self.random.uniform(
                *scenario.sinr_range
            ),

            rsrp_dbm=self.random.uniform(
                *scenario.rsrp_range
            ),

            rsrq_db=self.random.uniform(
                *scenario.rsrq_range
            ),

            cqi=self.random.randint(
                *scenario.cqi_range
            ),

            slice_resource_utilization_pct=self.random.uniform(
                *scenario.slice_utilization_range
            ),

            radio_resource_blocks_used=self.random.randint(
                *scenario.resource_blocks_range
            ),

            handover_in_progress=(
                self.random.random()
                < scenario.handover_probability
            ),

        )