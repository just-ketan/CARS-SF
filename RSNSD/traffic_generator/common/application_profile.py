"""
Application Profile

Defines the complete behavioural specification of an application.
Every traffic generator samples from an ApplicationProfile to
produce realistic network traffic.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from RSNSD.domain.enums import (
    DeviceType,
    MobilityProfile,
    PriorityLevel,
    ServiceClass,
    SliceType,
    TransportProtocol,
)
from .distributions import Distribution


@dataclass(slots=True)
class ApplicationProfile:
    """
    Complete description of one application's traffic behaviour.
    """

    # ==========================================================
    # Identity
    # ==========================================================

    name: str

    application_id: str

    service_class: ServiceClass

    description: str

    # ==========================================================
    # Network Behaviour
    # ==========================================================

    protocol: TransportProtocol

    transport_mode: str

    default_port: int

    # ==========================================================
    # Traffic Characteristics
    # ==========================================================

    packet_size_distribution: Distribution

    inter_arrival_distribution: Distribution

    session_duration_distribution: Distribution

    bitrate_distribution: Distribution

    # ==========================================================
    # QoS Targets
    # ==========================================================

    latency_requirement_ms: float

    jitter_requirement_ms: float

    packet_loss_requirement_pct: float

    throughput_requirement_mbps: float

    # ==========================================================
    # Service Context
    # ==========================================================

    priority: PriorityLevel

    slice_type: SliceType

    mobility: MobilityProfile

    device_type: DeviceType

    # ==========================================================
    # Optional Metadata
    # ==========================================================

    metadata: Optional[Dict] = field(default_factory=dict)