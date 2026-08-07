"""
QoS Engine

Coordinates all QoS analytical models to compute
correlated QoS metrics for each generated traffic flow.

Author: RSNSD
"""

from __future__ import annotations

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord
from RSNSD.domain.qos import QoSRecord

from .availability_model import AvailabilityModel
from .jitter_model import JitterModel
from .latency_model import LatencyModel
from .packet_loss_model import PacketLossModel
from .sla_model import SLAModel
from .throughput_model import ThroughputModel


class QoSEngine:
    """
    Central QoS computation engine.

    QoS metrics are computed sequentially because later
    metrics depend on earlier analytical outputs.
    """

    def __init__(self):

        self.latency_model = LatencyModel()
        self.throughput_model = ThroughputModel()
        self.packet_loss_model = PacketLossModel()
        self.jitter_model = JitterModel()
        self.availability_model = AvailabilityModel()
        self.sla_model = SLAModel()

    def compute(
        self,
        flow: FlowRecord,
        context: ContextRecord,
    ) -> QoSRecord:

        # ==================================================
        # Latency
        # ==================================================

        latency = self.latency_model.compute(
            flow,
            context,
        )

        # ==================================================
        # Throughput
        # ==================================================

        throughput = self.throughput_model.compute(
            flow,
            context,
            latency,
        )

        # ==================================================
        # Packet Loss
        # ==================================================

        packet_loss = self.packet_loss_model.compute(
            flow,
            context,
            throughput,
        )

        # ==================================================
        # Jitter
        # ==================================================

        jitter = self.jitter_model.compute(
            flow,
            context,
            latency,
            packet_loss,
        )

        # ==================================================
        # Availability
        # ==================================================

        availability = self.availability_model.compute(
            flow,
            context,
            latency,
            packet_loss,
            jitter,
        )

        # ==================================================
        # SLA
        # ==================================================

        sla_satisfied, qos_score = self.sla_model.compute(
            flow,
            latency,
            throughput,
            packet_loss,
            jitter,
            availability,
        )

        # ==================================================
        # Queueing Delay
        # ==================================================

        queueing_delay = (
            context.network_load_pct * 0.25
            + context.cell_load_pct * 0.15
        )

        if context.network_load_pct > 80:

            queueing_delay += (
                context.network_load_pct - 80
            ) * 0.80

        queueing_delay = min(
            queueing_delay,
            latency,
        )

        # ==================================================
        # Retransmission Rate
        # ==================================================

        retransmission_rate = (

            packet_loss

            *

            (1 + latency / 100)

        )

        retransmission_rate = min(
            retransmission_rate,
            100.0,
        )

        # ==================================================
        # Goodput
        # ==================================================

        goodput = (

            throughput

            *

            (1 - packet_loss / 100)

            *

            (1 - retransmission_rate / 100)

        )

        goodput = max(
            0.0,
            goodput,
        )

        # ==================================================
        # QoS Record
        # ==================================================

        return QoSRecord(

            end_to_end_latency_ms=round(
                latency,
                2,
            ),

            throughput_mbps=round(
                throughput,
                3,
            ),

            goodput_mbps=round(
                goodput,
                3,
            ),

            packet_loss_rate=round(
                packet_loss,
                3,
            ),

            jitter_ms=round(
                jitter,
                2,
            ),

            queueing_delay_ms=round(
                queueing_delay,
                2,
            ),

            retransmission_rate=round(
                retransmission_rate,
                3,
            ),

            availability_pct=round(
                availability,
                3,
            ),

            qos_satisfaction_score=round(
                qos_score,
                3,
            ),

            sla_satisfied=sla_satisfied,

        )