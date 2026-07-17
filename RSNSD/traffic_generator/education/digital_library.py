"""
Digital Library

Represents digital library platforms providing access to
e-books, journals, lecture notes, recorded classes and
educational multimedia resources.

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


DIGITAL_LIBRARY = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Digital Library",

    application_id="education.digital_library",

    service_class=ServiceClass.EDUCATION,

    description=(
        "Educational digital library providing access to "
        "books, journals, lecture recordings, research "
        "papers and multimedia learning resources."
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

        std=200,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=80,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=2400,

        std=600,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=8.0,

        std=2.0,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=120,

    jitter_requirement_ms=30,

    packet_loss_requirement_pct=1.0,

    throughput_requirement_mbps=6.0,

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

        "supports_video_lectures": True,

        "supports_document_download": True,

        "supports_research_papers": True,

        "supports_offline_access": True,

        "content_type": "Educational Resources",

    },

)