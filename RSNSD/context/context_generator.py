"""
Scenario-Aware Context Generator

Generates realistic ContextRecord instances from a given
rural operating scenario.

Author: RSNSD
"""

from __future__ import annotations

import random

from RSNSD.domain.context import ContextRecord


class ContextGenerator:

    def __init__(
        self,
        seed: int | None = None,
    ):

        self.random = random.Random(seed)

    def generate(
        self,
        profile,
        scenario,
    ) -> ContextRecord:

        # ==================================================
        # Active Users
        # ==================================================

        active_users = self.random.randint(
            *scenario.active_users_range
        )

        max_users = max(
            scenario.active_users_range[1],
            1,
        )

        # ==================================================
        # Network Load
        # ==================================================

        network_load = (
            active_users / max_users
        ) * 100

        network_load += self.random.uniform(-5, 5)

        network_load = max(
            5.0,
            min(network_load, 100.0),
        )

        # ==================================================
        # Cell Load
        # ==================================================

        cell_load = (
            network_load
            + self.random.uniform(-8, 8)
        )

        cell_load = max(
            0.0,
            min(cell_load, 100.0),
        )

        # ==================================================
        # Radio Resource Blocks
        # ==================================================

        resource_blocks = int(
            5 + network_load * 0.45
        )

        resource_blocks += self.random.randint(-3, 3)

        resource_blocks = max(
            scenario.resource_blocks_range[0],
            min(
                resource_blocks,
                scenario.resource_blocks_range[1],
            ),
        )

        # ==================================================
        # Signal Strength
        # ==================================================

        signal_strength = self.random.uniform(
            *scenario.signal_strength_range
        )

        signal_strength -= network_load * 0.15

        signal_strength = max(
            scenario.signal_strength_range[0],
            min(
                signal_strength,
                scenario.signal_strength_range[1],
            ),
        )

        # ==================================================
        # SINR
        # ==================================================

        sinr = 30.0

        sinr += (signal_strength + 90) * 0.5

        sinr -= network_load * 0.12

        sinr += self.random.uniform(-1.0, 1.0)

        sinr = max(
            scenario.sinr_range[0],
            min(
                sinr,
                scenario.sinr_range[1],
            ),
        )

        # ==================================================
        # RSRP
        # ==================================================

        rsrp = signal_strength + self.random.uniform(
            -2.0,
            2.0,
        )

        rsrp = max(
            scenario.rsrp_range[0],
            min(
                rsrp,
                scenario.rsrp_range[1],
            ),
        )

        # ==================================================
        # RSRQ
        # ==================================================

        rsrq = -3.0 - (network_load / 12.0)

        rsrq += self.random.uniform(
            -1.0,
            1.0,
        )

        rsrq = max(
            scenario.rsrq_range[0],
            min(
                rsrq,
                scenario.rsrq_range[1],
            ),
        )

        # ==================================================
        # CQI
        # ==================================================

        cqi = round(
            max(
                1,
                min(
                    15,
                    sinr / 2,
                ),
            )
        )

        cqi = max(
            scenario.cqi_range[0],
            min(
                cqi,
                scenario.cqi_range[1],
            ),
        )

        # ==================================================
        # Slice Resource Utilization
        # ==================================================

        slice_utilization = (
            network_load * 0.75
        )

        slice_utilization += self.random.uniform(
            -5,
            5,
        )

        slice_utilization = max(
            scenario.slice_utilization_range[0],
            min(
                slice_utilization,
                scenario.slice_utilization_range[1],
            ),
        )

        # ==================================================
        # Handover Probability
        # ==================================================

        handover_probability = (
            scenario.handover_probability
        )

        mobility = profile.mobility.lower()

        if mobility in (
            "vehicular",
            "vehicle",
        ):

            handover_probability *= 3.0

        elif mobility in (
            "walking",
            "pedestrian",
        ):

            handover_probability *= 1.5

        handover_probability = min(
            handover_probability,
            1.0,
        )

        handover = (
            self.random.random()
            < handover_probability
        )

        # ==================================================
        # Build Context Record
        # ==================================================

        return ContextRecord(

            network_load_pct=round(
                network_load,
                2,
            ),

            cell_load_pct=round(
                cell_load,
                2,
            ),

            active_users=active_users,

            device_type=profile.device_type,

            mobility_state=profile.mobility,

            network_slice_id=profile.slice_type,

            time_of_day=scenario.daytime,

            signal_strength_dbm=round(
                signal_strength,
                2,
            ),

            sinr_db=round(
                sinr,
                2,
            ),

            rsrp_dbm=round(
                rsrp,
                2,
            ),

            rsrq_db=round(
                rsrq,
                2,
            ),

            cqi=cqi,

            slice_resource_utilization_pct=round(
                slice_utilization,
                2,
            ),

            radio_resource_blocks_used=resource_blocks,

            handover_in_progress=handover,

        )