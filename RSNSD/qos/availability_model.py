"""
Availability Model

Computes service availability based on current network
conditions and QoS degradation.

Author: RSNSD
"""

from random import uniform

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord


class AvailabilityModel:
    """
    Analytical availability model.

    Availability is expressed as a percentage and decreases
    under congestion, packet loss and handovers.
    """

    def compute(
        self,
        flow: FlowRecord,
        context: ContextRecord,
        latency_ms: float,
        packet_loss_pct: float,
        jitter_ms: float,
    ) -> float:

        # ==================================================
        # Start from ideal availability
        # ==================================================

        availability = 100.0

        # ==================================================
        # Packet Loss
        # ==================================================

        availability -= packet_loss_pct * 2.5

        # ==================================================
        # Excess Latency
        # ==================================================

        if latency_ms > flow.latency_requirement_ms:

            excess = latency_ms - flow.latency_requirement_ms

            availability -= excess * 0.05

        # ==================================================
        # Excess Jitter
        # ==================================================

        if jitter_ms > flow.jitter_requirement_ms:

            excess = jitter_ms - flow.jitter_requirement_ms

            availability -= excess * 0.08

        # ==================================================
        # Network Congestion
        # ==================================================

        if context.network_load_pct > 80:

            availability -= (

                context.network_load_pct - 80

            ) * 0.20

        # ==================================================
        # Cell Congestion
        # ==================================================

        if context.cell_load_pct > 80:

            availability -= (

                context.cell_load_pct - 80

            ) * 0.15

        # ==================================================
        # Handover
        # ==================================================

        if context.handover_in_progress:

            availability -= uniform(1.0, 3.0)

        # ==================================================
        # Small Noise
        # ==================================================

        availability += uniform(-0.3, 0.3)

        return round(

            min(

                100.0,

                max(80.0, availability),

            ),

            2,

        )