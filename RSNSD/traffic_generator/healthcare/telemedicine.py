"""
Telemedicine Traffic Profile

Interactive real-time video consultation over a 5G network.

This profile represents delay-sensitive healthcare traffic
requiring URLLC characteristics.
"""

from RSNSD.domain.enums import (
    DeviceType,
    MobilityProfile,
    PriorityLevel,
    ServiceClass,
    SliceType,
    TransportProtocol,
)

from RSNSD.traffic_generator.common.application_profile import (
    ApplicationProfile,
)

from RSNSD.traffic_generator.common.distributions import (
    Distribution,
    DistributionType,
)


TELEMEDICINE = ApplicationProfile(

    # ==========================================================
    # Identity
    # ==========================================================

    name="Telemedicine Consultation",

    application_id="healthcare.telemedicine",

    service_class=ServiceClass.HEALTHCARE,

    description="Real-time doctor-patient video consultation.",

    # ==========================================================
    # Network Behaviour
    # ==========================================================

    protocol=TransportProtocol.UDP,

    transport_mode="unicast",

    default_port=5004,

    # ==========================================================
    # Traffic Characteristics
    # ==========================================================

    packet_size_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=1200,
        std=100,
    ),

    inter_arrival_distribution=Distribution(
        distribution=DistributionType.EXPONENTIAL,
        rate=50,
    ),

    session_duration_distribution=Distribution(
        distribution=DistributionType.UNIFORM,
        minimum=300,
        maximum=1800,
    ),

    bitrate_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=6.0,
        std=1.0,
    ),

    # ==========================================================
    # QoS Requirements
    # ==========================================================

    latency_requirement_ms=20,

    jitter_requirement_ms=5,

    packet_loss_requirement_pct=0.5,

    throughput_requirement_mbps=5.0,

    # ==========================================================
    # Context
    # ==========================================================

    priority=PriorityLevel.CRITICAL,

    slice_type=SliceType.URLLC,

    mobility=MobilityProfile.PEDESTRIAN,

    device_type=DeviceType.SMARTPHONE,

    metadata={
        "codec": "H.265",
        "video_resolution": "1080p",
        "fps": 30,
    }

)