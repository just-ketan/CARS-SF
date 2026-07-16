"""
Social Media

Represents social networking platforms supporting content
sharing, messaging, image uploads, short videos and live
streaming.

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


SOCIAL_MEDIA = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Social Media",

    application_id="general.social_media",

    service_class=ServiceClass.GENERAL,

    description=(

        "Social networking applications supporting image "
        "sharing, short videos, messaging, live streaming "
        "and multimedia content."

    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.TCP,

    transport_mode="bidirectional",

    default_port=443,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1100,

        std=180,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=150,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1800,

        std=600,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=4.0,

        std=1.2,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=120,

    jitter_requirement_ms=30,

    packet_loss_requirement_pct=1.0,

    throughput_requirement_mbps=3.5,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.MEDIUM,

    slice_type=SliceType.EMBB,

    mobility=MobilityProfile.PEDESTRIAN,

    device_type=DeviceType.SMARTPHONE,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "supports_image_upload": True,

        "supports_video_upload": True,

        "supports_live_streaming": True,

        "supports_messaging": True,

        "supports_short_video": True,

    },

)