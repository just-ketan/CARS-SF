"""
Latency Model

Computes end-to-end latency using analytical relationships
between congestion, radio quality, mobility and scheduling.

Author: RSNSD
"""

from __future__ import annotations

from random import uniform

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord


class LatencyModel:
    """
    Analytical latency model.

    Latency consists of:

        Base Processing Delay
      + Queueing Delay
      + Radio Delay
      + Mobility Delay
      + Handover Delay
      + Random Noise

    Queueing delay increases non-linearly with congestion,
    producing more realistic behaviour.
    """

    def compute(
        self,
        flow: FlowRecord,
        context: ContextRecord,
    ) -> float:

        # ==================================================
        # Base latency
        # ==================================================

        latency = flow.latency_requirement_ms

        # ==================================================
        # Queueing Delay
        # ==================================================

        queue_delay = 0.0

        network_load = context.network_load_pct
        cell_load = context.cell_load_pct

        if network_load < 60:

            queue_delay += network_load * 0.10

        elif network_load < 80:

            queue_delay += 6
            queue_delay += (network_load - 60) * 0.60

        else:

            queue_delay += 18
            queue_delay += (network_load - 80) * 1.50

        queue_delay += cell_load * 0.10

        latency += queue_delay

        # ==================================================
        # Radio Quality Delay
        # ==================================================

        latency += max(
            0,
            15 - context.cqi,
        ) * 1.8

        latency += max(
            0,
            20 - context.sinr_db,
        ) * 0.9

        latency += max(
            0,
            -85 - context.signal_strength_dbm,
        ) * 0.15

        # ==================================================
        # Slice Scheduling
        # ==================================================

        slice_id = context.network_slice_id.upper()

        if slice_id == "URLLC":

            latency *= 0.55

        elif slice_id == "EMBB":

            latency *= 0.90

        else:

            latency *= 1.15

        # ==================================================
        # Mobility Delay
        # ==================================================

        mobility = context.mobility_state.lower()

        if mobility in (
            "vehicular",
            "vehicle",
        ):

            latency += 10

        elif mobility in (
            "walking",
            "pedestrian",
        ):

            latency += 3

        elif mobility == "aerial":

            latency += 6

        # ==================================================
        # Handover Delay
        # ==================================================

        if context.handover_in_progress:

            latency += uniform(
                20,
                45,
            )

        # ==================================================
        # Small Noise
        # ==================================================

        latency += uniform(
            -1.5,
            1.5,
        )

        # ==================================================
        # Final Latency
        # ==================================================

        return round(
            max(
                1.0,
                latency,
            ),
            2,
        )