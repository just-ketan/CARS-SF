"""
Jitter Model

Computes network jitter based on congestion,
latency variation, packet loss and mobility.

Author: RSNSD
"""

from __future__ import annotations

from random import uniform

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord


class JitterModel:
    """
    Analytical jitter model.

    Jitter represents packet delay variation.

    It increases due to

        Queueing
            ↓
        Congestion
            ↓
        Packet Loss
            ↓
        Mobility
            ↓
        Handover
    """

    def compute(
        self,
        flow: FlowRecord,
        context: ContextRecord,
        latency_ms: float,
        packet_loss_pct: float,
    ) -> float:

        # ==================================================
        # Base Jitter
        # ==================================================

        jitter = max(
            0.5,
            latency_ms * 0.05,
        )

        # ==================================================
        # Queueing / Congestion
        # ==================================================

        network_load = context.network_load_pct

        if network_load < 60:

            jitter += network_load * 0.03

        elif network_load < 80:

            jitter += 2.0
            jitter += (
                network_load - 60
            ) * 0.12

        else:

            jitter += 4.4
            jitter += (
                network_load - 80
            ) * 0.35

        # ==================================================
        # Cell Congestion
        # ==================================================

        jitter += context.cell_load_pct * 0.03

        # ==================================================
        # Packet Loss
        # ==================================================

        jitter += packet_loss_pct * 0.80

        # ==================================================
        # Poor Radio Quality
        # ==================================================

        jitter += max(
            0,
            15 - context.cqi,
        ) * 0.35

        jitter += max(
            0,
            20 - context.sinr_db,
        ) * 0.15

        # ==================================================
        # Mobility
        # ==================================================

        mobility = context.mobility_state.lower()

        if mobility in (
            "vehicular",
            "vehicle",
        ):

            jitter += 2.5

        elif mobility in (
            "walking",
            "pedestrian",
        ):

            jitter += 0.8

        elif mobility == "aerial":

            jitter += 2.0

        # ==================================================
        # Handover
        # ==================================================

        if context.handover_in_progress:

            jitter += uniform(
                6,
                15,
            )

        # ==================================================
        # Random Noise
        # ==================================================

        jitter += uniform(
            -0.5,
            0.5,
        )

        return round(
            max(
                0.5,
                jitter,
            ),
            2,
        )