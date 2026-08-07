"""
SLA Model

Evaluates QoS satisfaction using weighted analytical scoring.

Author: RSNSD
"""

from __future__ import annotations

from RSNSD.domain.flow import FlowRecord


class SLAModel:
    """
    Computes SLA satisfaction and QoS score.

    QoS score is a weighted combination of
    normalized QoS metrics.

    SLA is considered satisfied only if every
    hard requirement is met.
    """

    LATENCY_WEIGHT = 0.30
    THROUGHPUT_WEIGHT = 0.30
    PACKET_LOSS_WEIGHT = 0.20
    JITTER_WEIGHT = 0.10
    AVAILABILITY_WEIGHT = 0.10

    def compute(
        self,
        flow: FlowRecord,
        latency_ms: float,
        throughput_mbps: float,
        packet_loss_pct: float,
        jitter_ms: float,
        availability_pct: float,
    ) -> tuple[bool, float]:

        # ==================================================
        # Hard SLA Checks
        # ==================================================

        latency_ok = (
            latency_ms
            <= flow.latency_requirement_ms
        )

        throughput_ok = (
            throughput_mbps
            >= flow.throughput_requirement_mbps
        )

        packet_loss_ok = (
            packet_loss_pct
            <= flow.packet_loss_requirement_pct
        )

        jitter_ok = (
            jitter_ms
            <= flow.jitter_requirement_ms
        )

        availability_ok = (
            availability_pct >= 99.0
        )

        satisfied = all(
            (
                latency_ok,
                throughput_ok,
                packet_loss_ok,
                jitter_ok,
                availability_ok,
            )
        )

        # ==================================================
        # Normalized Scores
        # ==================================================

        latency_score = min(
            1.0,
            flow.latency_requirement_ms
            / max(latency_ms, 0.01),
        )

        throughput_score = min(
            1.0,
            throughput_mbps
            / max(
                flow.throughput_requirement_mbps,
                0.01,
            ),
        )

        packet_loss_score = min(
            1.0,
            flow.packet_loss_requirement_pct
            / max(
                packet_loss_pct,
                0.01,
            ),
        )

        jitter_score = min(
            1.0,
            flow.jitter_requirement_ms
            / max(
                jitter_ms,
                0.01,
            ),
        )

        availability_score = min(
            1.0,
            availability_pct / 100.0,
        )

        # ==================================================
        # Weighted QoS Score
        # ==================================================

        qos_score = (

            latency_score
            * self.LATENCY_WEIGHT

            +

            throughput_score
            * self.THROUGHPUT_WEIGHT

            +

            packet_loss_score
            * self.PACKET_LOSS_WEIGHT

            +

            jitter_score
            * self.JITTER_WEIGHT

            +

            availability_score
            * self.AVAILABILITY_WEIGHT

        ) * 100.0

        return (
            satisfied,
            round(qos_score, 2),
        )