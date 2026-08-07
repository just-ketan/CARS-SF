"""
Packet Loss Model

Computes packet loss based on radio quality,
network congestion, scheduling conditions,
and achieved throughput.

Author: RSNSD
"""

from __future__ import annotations

from random import uniform

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord


class PacketLossModel:
    """
    Analytical packet loss model.

    Packet loss depends on

        Radio Quality
            ↓
        Congestion
            ↓
        Throughput Deficit
            ↓
        Handover
    """

    def compute(
        self,
        flow: FlowRecord,
        context: ContextRecord,
        throughput_mbps: float,
    ) -> float:

        # ==================================================
        # Base Packet Loss
        # ==================================================

        loss = 0.02

        # ==================================================
        # CQI Penalty
        # ==================================================

        if context.cqi < 10:

            cqi_penalty = (
                (10 - context.cqi) / 10
            ) ** 2

            loss += cqi_penalty * 3.0

        # ==================================================
        # SINR Penalty
        # ==================================================

        if context.sinr_db < 20:

            sinr_penalty = (
                (20 - context.sinr_db) / 20
            ) ** 2

            loss += sinr_penalty * 4.0

        # ==================================================
        # Network Congestion
        # ==================================================

        if context.network_load_pct > 60:

            congestion = (
                (context.network_load_pct - 60) / 40
            ) ** 2

            loss += congestion * 5.0

        # ==================================================
        # Cell Congestion
        # ==================================================

        if context.cell_load_pct > 60:

            congestion = (
                (context.cell_load_pct - 60) / 40
            ) ** 2

            loss += congestion * 3.5

        # ==================================================
        # Slice Resource Saturation
        # ==================================================

        if context.slice_resource_utilization_pct > 75:

            saturation = (
                (
                    context.slice_resource_utilization_pct
                    - 75
                ) / 25
            ) ** 2

            loss += saturation * 4.0

        # ==================================================
        # Throughput Deficit
        # ==================================================

        required = max(
            flow.throughput_requirement_mbps,
            0.01,
        )

        ratio = throughput_mbps / required

        if ratio < 1.0:

            deficit = (
                1.0 - ratio
            ) ** 2

            loss += deficit * 10.0

        # ==================================================
        # Mobility
        # ==================================================

        mobility = context.mobility_state.lower()

        if mobility in (
            "vehicular",
            "vehicle",
        ):

            loss += 0.30

        elif mobility == "aerial":

            loss += 0.15

        # ==================================================
        # Handover
        # ==================================================

        if context.handover_in_progress:

            loss += uniform(
                1.0,
                3.0,
            )

        # ==================================================
        # Small Noise
        # ==================================================

        loss += uniform(
            0.0,
            0.08,
        )

        # ==================================================
        # Clamp
        # ==================================================

        loss = max(
            0.0,
            min(
                loss,
                30.0,
            ),
        )

        return round(
            loss,
            3,
        )