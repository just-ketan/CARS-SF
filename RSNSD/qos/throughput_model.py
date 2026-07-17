"""
Throughput Model

Computes achievable throughput based on application demand,
radio quality, congestion and latency.

Author: RSNSD
"""

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord


class ThroughputModel:
    """
    Analytical throughput model.

    Throughput starts from the application's requested
    bitrate and is reduced by congestion, poor radio
    conditions and excessive latency.
    """

    def compute(
        self,
        flow: FlowRecord,
        context: ContextRecord,
        latency_ms: float,
    ) -> float:

        # ==================================================
        # Requested throughput
        # ==================================================

        throughput = flow.throughput_requirement_mbps

        # ==================================================
        # Radio Quality (CQI)
        # ==================================================

        throughput *= context.cqi / 15.0

        # ==================================================
        # Signal Quality (SINR)
        # ==================================================

        throughput *= min(context.sinr_db / 20.0, 1.0)

        # ==================================================
        # Network Congestion
        # ==================================================

        throughput *= max(0.20, 1 - context.network_load_pct / 100)

        throughput *= max(0.30, 1 - context.cell_load_pct / 100)

        # ==================================================
        # Slice Resource Utilization
        # ==================================================

        throughput *= max(
            0.30,
            1 - context.slice_resource_utilization_pct / 100,
        )

        # ==================================================
        # Radio Resource Blocks
        # ==================================================

        throughput *= min(
            context.radio_resource_blocks_used / 50,
            1.0,
        )

        # ==================================================
        # Latency Penalty
        # ==================================================

        if latency_ms > flow.latency_requirement_ms:

            throughput *= (
                flow.latency_requirement_ms /
                latency_ms
            )

        # ==================================================
        # Upper Bound
        # ==================================================

        throughput = min(
            throughput,
            flow.bitrate_mbps,
        )

        return round(max(0.05, throughput), 3)