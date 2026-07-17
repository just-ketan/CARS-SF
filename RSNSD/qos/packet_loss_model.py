"""
Packet Loss Model

Computes packet loss based on radio quality, congestion,
mobility and achieved throughput.

Author: RSNSD
"""

from random import uniform

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord


class PacketLossModel:
    """
    Analytical packet loss model.

    Packet loss increases under congestion,
    weak radio conditions and handovers.
    """

    def compute(
        self,
        flow: FlowRecord,
        context: ContextRecord,
        throughput_mbps: float,
    ) -> float:

        # ==================================================
        # Base packet loss
        # ==================================================

        loss = 0.02

        # ==================================================
        # Poor CQI
        # ==================================================

        if context.cqi < 10:

            loss += (10 - context.cqi) * 0.15

        # ==================================================
        # Poor SINR
        # ==================================================

        if context.sinr_db < 20:

            loss += (20 - context.sinr_db) * 0.08

        # ==================================================
        # Network Congestion
        # ==================================================

        if context.network_load_pct > 70:

            loss += (
                context.network_load_pct - 70
            ) * 0.04

        # ==================================================
        # Cell Congestion
        # ==================================================

        if context.cell_load_pct > 70:

            loss += (
                context.cell_load_pct - 70
            ) * 0.03

        # ==================================================
        # Slice Resource Saturation
        # ==================================================

        if context.slice_resource_utilization_pct > 80:

            loss += (
                context.slice_resource_utilization_pct - 80
            ) * 0.04

        # ==================================================
        # Throughput Deficit
        # ==================================================

        if throughput_mbps < flow.throughput_requirement_mbps:

            deficit = (

                flow.throughput_requirement_mbps

                - throughput_mbps

            )

            loss += deficit * 0.30

        # ==================================================
        # Handover
        # ==================================================

        if context.handover_in_progress:

            loss += uniform(0.5, 2.0)

        # ==================================================
        # Small Random Noise
        # ==================================================

        loss += uniform(0.0, 0.1)

        return round(max(0.0, loss), 3)