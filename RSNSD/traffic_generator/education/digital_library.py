"""
Online Examination

Represents secure real-time online examinations requiring
low latency, high reliability and continuous synchronization.

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


ONLINE_EXAM = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Online Examination",

    application_id="education.online_exam",

    service_class=ServiceClass.EDUCATION,

    description=(
        "Secure online examination platform with continuous "
        "answer synchronization and proctoring."
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

        mean=700,

        std=120,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=120,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=7200,

        std=900,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1.2,

        std=0.3,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=30,

    jitter_requirement_ms=10,

    packet_loss_requirement_pct=0.1,

    throughput_requirement_mbps=1.0,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.CRITICAL,

    slice_type=SliceType.URLLC,

    mobility=MobilityProfile.STATIC,

    device_type=DeviceType.LAPTOP,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "exam_type": "MCQ + Subjective",

        "proctoring": True,

        "camera_required": True,

    },

)