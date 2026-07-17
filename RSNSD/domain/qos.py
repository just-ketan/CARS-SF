"""
QoS Domain Model

Represents the Quality of Service experienced by a traffic
flow after transmission through the network.

Author: RSNSD
"""

from dataclasses import dataclass


@dataclass(slots=True)
class QoSRecord:
    """
    Quality of Service metrics computed by the QoS Engine.
    """

    end_to_end_latency_ms: float

    throughput_mbps: float

    goodput_mbps: float

    packet_loss_rate: float

    jitter_ms: float

    queueing_delay_ms: float

    retransmission_rate: float

    availability_pct: float

    qos_satisfaction_score: float

    sla_satisfied: bool