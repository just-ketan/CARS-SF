"""
Learning Management System

Represents Learning Management Systems (LMS) such as Moodle,
Canvas or Google Classroom used for assignments, quizzes,
course materials and announcements.

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


LEARNING_MANAGEMENT = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Learning Management System",

    application_id="education.learning_management",

    service_class=ServiceClass.EDUCATION,

    description=(
        "Interactive web-based learning platform supporting "
        "course content, assignments, quizzes and grading."
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

        std=150,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=80,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1800,

        std=600,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=2.5,

        std=0.8,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=120,

    jitter_requirement_ms=30,

    packet_loss_requirement_pct=1.0,

    throughput_requirement_mbps=2.0,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.MEDIUM,

    slice_type=SliceType.EMBB,

    mobility=MobilityProfile.STATIC,

    device_type=DeviceType.LAPTOP,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "supports_assignments": True,

        "supports_quizzes": True,

        "supports_announcements": True,

    },

)