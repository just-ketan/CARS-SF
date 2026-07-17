"""
Latency Model

Computes end-to-end latency using analytical relationships
between radio quality, congestion and mobility.

Author: RSNSD
"""

from random import uniform

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord


class LatencyModel:
    """
    Analytical latency model.

    The objective is not PHY-level simulation but to produce
    realistic latency values exhibiting correlations with
    congestion, signal quality and mobility.
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
        # Network congestion
        # ==================================================

        latency += context.network_load_pct * 0.25

        latency += context.cell_load_pct * 0.15

        # ==================================================
        # Radio quality
        # ==================================================

        latency += max(0, 15 - context.cqi) * 1.5

        latency += max(0, 20 - context.sinr_db) * 0.8

        # ==================================================
        # Slice priority
        # ==================================================

        if context.network_slice_id == "URLLC":

            latency *= 0.60

        elif context.network_slice_id == "eMBB":

            latency *= 0.90

        else:

            latency *= 1.15

        # ==================================================
        # Mobility
        # ==================================================

        if context.mobility_state == "vehicular":

            latency += 8

        elif context.mobility_state == "aerial":

            latency += 5

        # ==================================================
        # Handover
        # ==================================================

        if context.handover_in_progress:

            latency += uniform(15, 40)

        # ==================================================
        # Random variation
        # ==================================================

        latency += uniform(-2.5, 2.5)

        return round(max(1.0, latency), 2)