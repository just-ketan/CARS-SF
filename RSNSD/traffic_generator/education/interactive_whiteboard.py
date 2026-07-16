"""
Interactive Whiteboard

Represents collaborative digital whiteboards used during
live lectures for drawing, annotation and synchronized
content sharing between instructors and students.

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


INTERACTIVE_WHITEBOARD = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Interactive Whiteboard",

    application_id="education.interactive_whiteboard",

    service_class=ServiceClass.EDUCATION,

    description=(
        "Collaborative real-time digital whiteboard for "
        "annotations, drawing and synchronized classroom "
        "content sharing."
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

        mean=950,

        std=140,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=120,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=3600,

        std=900,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=3.0,

        std=0.8,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=60,

    jitter_requirement_ms=15,

    packet_loss_requirement_pct=0.5,

    throughput_requirement_mbps=2.5,

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

        "supports_annotation": True,

        "supports_multiuser": True,

        "supports_screen_sharing": True,

        "max_concurrent_users": 100,

    },

)