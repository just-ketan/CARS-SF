"""
Flow Domain Model

Represents one generated network flow before it is exported
into the dataset.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FlowRecord:

    # ==========================================================
    # Identity
    # ==========================================================

    flow_id: str

    application_id: str

    service_class: str

    # ==========================================================
    # Generated Traffic
    # ==========================================================

    packet_size: float

    inter_arrival_time_ms: float

    session_duration_s: float

    bitrate_mbps: float

    # ==========================================================
    # QoS Targets
    # ==========================================================

    latency_requirement_ms: float

    jitter_requirement_ms: float

    packet_loss_requirement_pct: float

    throughput_requirement_mbps: float

    # ==========================================================
    # Metadata
    # ==========================================================

    metadata: dict[str, Any] = field(default_factory=dict)