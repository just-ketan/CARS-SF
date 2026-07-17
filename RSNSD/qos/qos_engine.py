"""
QoS Engine

Coordinates all QoS analytical models to compute
correlated QoS metrics for each generated traffic flow.

Author: RSNSD
"""

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord

from .availability_model import AvailabilityModel
from .jitter_model import JitterModel
from .latency_model import LatencyModel
from .packet_loss_model import PacketLossModel
from .sla_model import SLAModel
from .throughput_model import ThroughputModel
from RSNSD.domain.qos import QoSRecord

class QoSEngine:
    """
    Central QoS computation engine.

    Each QoS metric is computed sequentially because later
    metrics depend on earlier ones.
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
    ) -> FlowRecord:

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
        # Build QoS Record
        # ==================================================

        goodput = max(
            0.0,
            throughput * (1 - packet_loss / 100),
        )

        queueing_delay = max(
            0.0,
            latency - flow.latency_requirement_ms,
        )

        retransmission_rate = packet_loss * 0.25

        return QoSRecord(
            end_to_end_latency_ms=latency,
            throughput_mbps=throughput,
            goodput_mbps=goodput,
            packet_loss_rate=packet_loss,
            jitter_ms=jitter,
            queueing_delay_ms=queueing_delay,
            retransmission_rate=retransmission_rate,
            availability_pct=availability,
            qos_satisfaction_score=qos_score,
            sla_satisfied=sla_satisfied,
        )