"""
Video Conferencing

Represents real-time interactive video conferencing used for
remote work, meetings, teleconsultation and online collaboration.

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


VIDEO_CONFERENCING = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Video Conferencing",

    application_id="general.video_conferencing",

    service_class=ServiceClass.GENERAL,

    description=(

        "Real-time video conferencing supporting meetings, "
        "remote collaboration and multimedia communication."

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

        mean=1100,

        std=150,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=180,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=2400,

        std=900,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=4.5,

        std=1.0,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=50,

    jitter_requirement_ms=15,

    packet_loss_requirement_pct=0.5,

    throughput_requirement_mbps=3.5,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.HIGH,

    slice_type=SliceType.EMBB,

    mobility=MobilityProfile.PEDESTRIAN,

    device_type=DeviceType.LAPTOP,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "video_resolution": "1080p",

        "codec": "H.264",

        "fps": 30,

        "screen_sharing": True,

        "participant_limit": 100,

    },

)