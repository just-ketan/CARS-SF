"""
Teacher Portal

Represents faculty portals used for managing courses,
grades, attendance, assignments and communication.

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


TEACHER_PORTAL = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Teacher Portal",

    application_id="education.teacher_portal",

    service_class=ServiceClass.EDUCATION,

    description=(
        "Faculty portal supporting attendance management, "
        "grading, assignment uploads and academic records."
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

        mean=850,

        std=120,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=40,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=2400,

        std=600,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1.5,

        std=0.4,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=120,

    jitter_requirement_ms=30,

    packet_loss_requirement_pct=1.0,

    throughput_requirement_mbps=1.5,

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

        "supports_grading": True,

        "supports_attendance": True,

        "supports_assignments": True,

        "supports_course_management": True,

    },

)