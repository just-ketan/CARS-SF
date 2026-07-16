"""
Live Classroom

Represents real-time online classroom sessions with
interactive audio/video communication.

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


LIVE_CLASSROOM = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Live Classroom",

    application_id="education.live_classroom",

    service_class=ServiceClass.EDUCATION,

    description=(
        "Real-time online classroom with HD audio/video "
        "streaming between teacher and students."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.UDP,

    transport_mode="bidirectional",

    default_port=443,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1200,

        std=180,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=180,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=3600,

        std=600,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=5.0,

        std=1.0,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=80,

    jitter_requirement_ms=20,

    packet_loss_requirement_pct=1.0,

    throughput_requirement_mbps=4.0,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.HIGH,

    slice_type=SliceType.EMBB,

    mobility=MobilityProfile.STATIC,

    device_type=DeviceType.LAPTOP,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "video_resolution": "1080p",

        "codec": "H.264",

        "fps": 30,

    },

)