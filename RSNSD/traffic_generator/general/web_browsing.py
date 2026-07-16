"""
Web Browsing

Represents conventional web browsing including news,
government portals, online shopping and information access.

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


WEB_BROWSING = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Web Browsing",

    application_id="general.web_browsing",

    service_class=ServiceClass.GENERAL,

    description=(
        "General internet browsing including websites, "
        "government services, online shopping and news."
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

        mean=900,

        std=180,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=70,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1200,

        std=400,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=2.0,

        std=0.5,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=150,

    jitter_requirement_ms=40,

    packet_loss_requirement_pct=1.0,

    throughput_requirement_mbps=2.0,

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

        "supports_https": True,

        "content_type": "Mixed",

        "cacheable": True,

    },

)