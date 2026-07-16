"""
Emergency Voice Application Profile

Mission-critical voice communication between emergency
responders, ambulances, rural clinics and hospitals.

Author: RSNSD
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


EMERGENCY_VOICE = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Emergency Voice",

    application_id="healthcare.emergency_voice",

    service_class=ServiceClass.HEALTHCARE,

    description=(
        "Mission-critical emergency voice communication "
        "between ambulances, hospitals and emergency "
        "response teams."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.UDP,

    transport_mode="bidirectional",

    default_port=5007,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=256,
        std=20,
    ),

    inter_arrival_distribution=Distribution(
        distribution=DistributionType.CONSTANT,
        value=0.02,
    ),

    session_duration_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=600,
        std=120,
    ),

    bitrate_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=0.128,
        std=0.01,
    ),

    # ======================================================
    # QoS Requirements
    # ======================================================

    latency_requirement_ms=10,

    jitter_requirement_ms=2,

    packet_loss_requirement_pct=0.1,

    throughput_requirement_mbps=0.128,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.CRITICAL,

    slice_type=SliceType.URLLC,

    mobility=MobilityProfile.VEHICULAR,

    device_type=DeviceType.SMARTPHONE,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "codec": "AMR-WB",

        "sample_rate_hz": 16000,

        "push_to_talk": True,

        "voice_encryption": True,

        "conference_support": True,

    },

)