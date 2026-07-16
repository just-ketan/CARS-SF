"""
Remote Surgery Application Profile

Represents robotic telesurgery traffic requiring extremely
low latency and ultra-high reliability.

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


REMOTE_SURGERY = ApplicationProfile(

    # --------------------------------------------------
    # Identity
    # --------------------------------------------------

    name="Remote Surgery",

    application_id="healthcare.remote_surgery",

    service_class=ServiceClass.HEALTHCARE,

    description=(
        "Robotic telesurgery with haptic feedback and "
        "multiple synchronized HD video streams."
    ),

    # --------------------------------------------------
    # Network Behaviour
    # --------------------------------------------------

    protocol=TransportProtocol.TCP,

    transport_mode="bidirectional",

    default_port=5001,

    # --------------------------------------------------
    # Traffic Characteristics
    # --------------------------------------------------

    packet_size_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=1400,
        std=40,
    ),

    inter_arrival_distribution=Distribution(
        distribution=DistributionType.CONSTANT,
        value=0.001,
    ),

    session_duration_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=7200,
        std=300,
    ),

    bitrate_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=80,
        std=5,
    ),

    # --------------------------------------------------
    # QoS
    # --------------------------------------------------

    latency_requirement_ms=5,

    jitter_requirement_ms=1,

    packet_loss_requirement_pct=0.01,

    throughput_requirement_mbps=75,

    # --------------------------------------------------
    # Service Context
    # --------------------------------------------------

    priority=PriorityLevel.CRITICAL,

    slice_type=SliceType.URLLC,

    mobility=MobilityProfile.STATIC,

    device_type=DeviceType.GATEWAY,

    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------

    metadata={

        "video_resolution": "4K",

        "video_streams": 3,

        "haptic_feedback": True,

        "codec": "H.265",

        "fps": 60,

    },

)