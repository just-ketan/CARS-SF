"""
Video Streaming

Represents OTT video streaming services such as YouTube,
Netflix and educational multimedia platforms.

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


VIDEO_STREAMING = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Video Streaming",

    application_id="general.video_streaming",

    service_class=ServiceClass.GENERAL,

    description=(
        "Adaptive bitrate video streaming for entertainment "
        "and educational multimedia content."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.TCP,

    transport_mode="download",

    default_port=443,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1400,

        std=100,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=220,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=2700,

        std=900,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=8.0,

        std=2.5,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=200,

    jitter_requirement_ms=40,

    packet_loss_requirement_pct=1.5,

    throughput_requirement_mbps=6.0,

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

        "video_resolution": "Adaptive",

        "supports_hdr": True,

        "adaptive_bitrate": True,

        "codec": "H.265",

        "fps": 30,

    },

)