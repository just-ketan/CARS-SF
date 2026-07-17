"""
Jitter Model

Computes network jitter based on latency, congestion,
packet loss and mobility.

Author: RSNSD
"""

from random import uniform

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord


class JitterModel:
    """
    Analytical jitter model.

    Jitter represents latency variation and is strongly
    correlated with congestion and unstable radio links.
    """

    CONGESTION_THRESHOLD = 70

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

        jitter = max(1.0, latency_ms * 0.10)

        # ==================================================
        # Packet Loss Contribution
        # ==================================================

        jitter += packet_loss_pct * 1.5

        # ==================================================
        # Network Congestion
        # ==================================================

        if context.network_load_pct > self.CONGESTION_THRESHOLD:

            jitter += (

                context.network_load_pct

                - self.CONGESTION_THRESHOLD

            ) * 0.15

        # ==================================================
        # Cell Congestion
        # ==================================================

        if context.cell_load_pct > self.CONGESTION_THRESHOLD:

            jitter += (

                context.cell_load_pct

                - self.CONGESTION_THRESHOLD

            ) * 0.10

        # ==================================================
        # Mobility
        # ==================================================

        if context.mobility_state == "vehicular":

            jitter += 2

        elif context.mobility_state == "aerial":

            jitter += 1.5

        # ==================================================
        # Handover
        # ==================================================

        if context.handover_in_progress:

            jitter += uniform(5, 12)

        # ==================================================
        # Small Random Noise
        # ==================================================

        jitter += uniform(-1.0, 1.0)

        return round(max(0.5, jitter), 2)