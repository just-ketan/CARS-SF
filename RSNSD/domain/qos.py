"""
QoS Domain Model

Represents the observed Quality of Service experienced by a
generated network flow.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class QoSRecord:

    latency_ms: float

    jitter_ms: float

    packet_loss_pct: float

    throughput_mbps: float

    bandwidth_allocated_mbps: float

    availability_pct: float

    sla_satisfied: bool