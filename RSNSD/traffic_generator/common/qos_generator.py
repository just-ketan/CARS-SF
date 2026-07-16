"""
QoS Generator

Computes observed QoS metrics from the generated application
flow and network context.
"""

import random

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord
from RSNSD.domain.qos import QoSRecord


class QoSGenerator:

    def __init__(self, seed: int | None = None):

        self.random = random.Random(seed)

    def generate(
        self,
        flow: FlowRecord,
        context: ContextRecord,
    ) -> QoSRecord:

        # --------------------------------------------------
        # Congestion
        # --------------------------------------------------

        congestion_factor = context.network_load_pct / 100.0

        # --------------------------------------------------
        # Radio quality
        # --------------------------------------------------

        radio_penalty = max(
            0,
            (15 - context.cqi) * 0.8,
        )

        # --------------------------------------------------
        # Latency
        # --------------------------------------------------

        latency = (
            flow.latency_requirement_ms
            + congestion_factor * 25
            + radio_penalty
            + self.random.uniform(-1.5, 1.5)
        )

        # --------------------------------------------------
        # Jitter
        # --------------------------------------------------

        jitter = (
            flow.jitter_requirement_ms
            + congestion_factor * 8
            + self.random.uniform(0, 2)
        )

        # --------------------------------------------------
        # Packet Loss
        # --------------------------------------------------

        packet_loss = min(
            100,
            flow.packet_loss_requirement_pct
            + congestion_factor * 4
            + max(0, 10 - context.cqi) * 0.3
            + self.random.uniform(0, 0.3),
        )

        # --------------------------------------------------
        # Throughput
        # --------------------------------------------------

        throughput = (
            flow.bitrate_mbps
            * (1 - congestion_factor * 0.45)
            * (context.cqi / 15)
        )

        throughput = max(0.1, throughput)

        # --------------------------------------------------
        # Allocated Bandwidth
        # --------------------------------------------------

        bandwidth = throughput * 1.15

        # --------------------------------------------------
        # Availability
        # --------------------------------------------------

        availability = max(
            90,
            100
            - packet_loss
            - congestion_factor * 2,
        )

        # --------------------------------------------------
        # SLA
        # --------------------------------------------------

        sla = (

            latency <= flow.latency_requirement_ms

            and

            jitter <= flow.jitter_requirement_ms

            and

            packet_loss <= flow.packet_loss_requirement_pct

        )

        return QoSRecord(

            latency_ms=round(latency, 2),

            jitter_ms=round(jitter, 2),

            packet_loss_pct=round(packet_loss, 3),

            throughput_mbps=round(throughput, 3),

            bandwidth_allocated_mbps=round(bandwidth, 3),

            availability_pct=round(availability, 2),

            sla_satisfied=sla,
        )