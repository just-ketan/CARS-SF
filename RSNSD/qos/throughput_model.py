"""
Throughput Model

Computes achievable throughput based on application demand,
radio quality, congestion and scheduling conditions.

Author: RSNSD
"""

from __future__ import annotations

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord


class ThroughputModel:
    """
    Analytical throughput model.

    Throughput depends on:

        Requested Throughput
            ↓
        Radio Quality
            ↓
        Scheduling Resources
            ↓
        Congestion
            ↓
        Latency Penalty
    """

    def compute(
        self,
        flow: FlowRecord,
        context: ContextRecord,
        latency_ms: float,
    ) -> float:

        # ==================================================
        # Requested Throughput
        # ==================================================

        throughput = flow.throughput_requirement_mbps

        # ==================================================
        # CQI Scaling
        # ==================================================

        cqi_factor = (
            context.cqi / 15.0
        ) ** 1.2

        throughput *= cqi_factor

        # ==================================================
        # SINR Scaling
        # ==================================================

        sinr_factor = min(
            1.0,
            max(
                0.10,
                context.sinr_db / 25.0,
            ),
        )

        throughput *= sinr_factor

        # ==================================================
        # Network Congestion
        # ==================================================

        network_factor = max(
            0.05,
            ((100 - context.network_load_pct) / 100) ** 2,
        )

        throughput *= network_factor

        # ==================================================
        # Cell Congestion
        # ==================================================

        cell_factor = max(
            0.10,
            ((100 - context.cell_load_pct) / 100) ** 1.8,
        )

        throughput *= cell_factor

        # ==================================================
        # Slice Resource Utilization
        # ==================================================

        slice_factor = max(
            0.10,
            (
                (100 - context.slice_resource_utilization_pct)
                / 100
            ) ** 1.5,
        )

        throughput *= slice_factor

        # ==================================================
        # Radio Resource Blocks
        # ==================================================

        rb_factor = (
            context.radio_resource_blocks_used / 50
        )

        rb_factor = max(
            0.20,
            min(
                rb_factor,
                1.0,
            ),
        )

        throughput *= rb_factor

        # ==================================================
        # Slice Priority Bonus
        # ==================================================

        slice_id = context.network_slice_id.upper()

        if slice_id == "URLLC":

            throughput *= 0.90

        elif slice_id == "EMBB":

            throughput *= 1.10

        elif slice_id == "MMTC":

            throughput *= 0.70

        # ==================================================
        # Latency Penalty
        # ==================================================

        if latency_ms > flow.latency_requirement_ms:

            ratio = (
                flow.latency_requirement_ms
                / latency_ms
            )

            throughput *= ratio ** 1.5

        # ==================================================
        # Physical Upper Bound
        # ==================================================

        throughput = min(
            throughput,
            flow.bitrate_mbps,
        )

        throughput = min(
            throughput,
            flow.throughput_requirement_mbps,
        )

        # ==================================================
        # Minimum Throughput
        # ==================================================

        throughput = max(
            throughput,
            0.05,
        )

        return round(
            throughput,
            3,
        )