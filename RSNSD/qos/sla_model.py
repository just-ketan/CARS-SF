"""
SLA Model

Evaluates whether a traffic flow satisfies the application's
QoS requirements.

Author: RSNSD
"""

from RSNSD.domain.flow import FlowRecord


class SLAModel:
    """
    Computes QoS satisfaction.

    A flow satisfies the SLA only if every QoS requirement
    defined by the application profile is met.
    """

    def compute(
        self,
        flow: FlowRecord,
        latency_ms: float,
        throughput_mbps: float,
        packet_loss_pct: float,
        jitter_ms: float,
        availability_pct: float,
    ) -> tuple[bool, float]:

        checks = []

        # ==================================================
        # Latency
        # ==================================================

        checks.append(

            latency_ms <= flow.latency_requirement_ms

        )

        # ==================================================
        # Throughput
        # ==================================================

        checks.append(

            throughput_mbps >= flow.throughput_requirement_mbps

        )

        # ==================================================
        # Packet Loss
        # ==================================================

        checks.append(

            packet_loss_pct <= flow.packet_loss_requirement_pct

        )

        # ==================================================
        # Jitter
        # ==================================================

        checks.append(

            jitter_ms <= flow.jitter_requirement_ms

        )

        # ==================================================
        # Availability
        # ==================================================

        checks.append(

            availability_pct >= 99.0

        )

        # ==================================================
        # SLA Decision
        # ==================================================

        satisfied = all(checks)

        # ==================================================
        # QoS Satisfaction Score
        # ==================================================

        score = (

            sum(checks)

            / len(checks)

        ) * 100.0

        return (

            satisfied,

            round(score, 2),

        )