"""
E-Governance

Represents digital government services including citizen
portals, subsidy applications, land records, certificates
and public administration services.

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


E_GOVERNANCE = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="E-Governance",

    application_id="general.e_governance",

    service_class=ServiceClass.GENERAL,

    description=(

        "Digital government platform providing access to "
        "citizen services, certificates, subsidies, land "
        "records and public administration."

    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.TCP,

    transport_mode="transactional",

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

        mean=900,

        std=300,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1.2,

        std=0.3,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=100,

    jitter_requirement_ms=25,

    packet_loss_requirement_pct=0.5,

    throughput_requirement_mbps=1.0,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.HIGH,

    slice_type=SliceType.EMBB,

    mobility=MobilityProfile.PEDESTRIAN,

    device_type=DeviceType.SMARTPHONE,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "supports_document_upload": True,

        "supports_digital_signature": True,

        "supports_identity_verification": True,

        "supports_online_payments": True,

        "service_category": "Citizen Services",

    },

)