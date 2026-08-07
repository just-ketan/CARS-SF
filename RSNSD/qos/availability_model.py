"""
Availability Model

Computes service availability based on
network congestion and QoS degradation.

Author: RSNSD
"""

from __future__ import annotations

from random import uniform

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord


class AvailabilityModel:
    """
    Analytical availability model.

    Availability starts at 100% and is reduced by
    cumulative QoS degradation.
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
        # Ideal Availability
        # ==================================================

        availability = 100.0

        # ==================================================
        # Packet Loss Penalty
        # ==================================================

        availability -= packet_loss_pct * 2.0

        # ==================================================
        # Latency Penalty
        # ==================================================

        if latency_ms > flow.latency_requirement_ms:

            ratio = (
                latency_ms /
                flow.latency_requirement_ms
            )

            availability -= (
                (ratio - 1.0) ** 2
            ) * 8.0

        # ==================================================
        # Jitter Penalty
        # ==================================================

        if jitter_ms > flow.jitter_requirement_ms:

            ratio = (
                jitter_ms /
                flow.jitter_requirement_ms
            )

            availability -= (
                (ratio - 1.0) ** 2
            ) * 6.0

        # ==================================================
        # Network Congestion
        # ==================================================

        if context.network_load_pct > 75:

            congestion = (
                (
                    context.network_load_pct
                    - 75
                ) / 25
            ) ** 2

            availability -= congestion * 6.0

        # ==================================================
        # Cell Congestion
        # ==================================================

        if context.cell_load_pct > 75:

            congestion = (
                (
                    context.cell_load_pct
                    - 75
                ) / 25
            ) ** 2

            availability -= congestion * 4.0

        # ==================================================
        # Poor Radio Quality
        # ==================================================

        availability -= max(
            0,
            10 - context.cqi,
        ) * 0.30

        availability -= max(
            0,
            15 - context.sinr_db,
        ) * 0.10

        # ==================================================
        # Mobility
        # ==================================================

        mobility = context.mobility_state.lower()

        if mobility in (
            "vehicular",
            "vehicle",
        ):

            availability -= 0.50

        elif mobility == "aerial":

            availability -= 0.30

        # ==================================================
        # Handover
        # ==================================================

        if context.handover_in_progress:

            availability -= uniform(
                1.5,
                3.5,
            )

        # ==================================================
        # Small Measurement Noise
        # ==================================================

        availability += uniform(
            -0.20,
            0.20,
        )

        # ==================================================
        # Clamp
        # ==================================================

        availability = max(
            80.0,
            min(
                availability,
                100.0,
            ),
        )

        return round(
            availability,
            2,
        )