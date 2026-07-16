"""
Emergency Alert Service

Represents government emergency notification systems used
for disaster warnings, evacuation notices, severe weather
alerts and public safety broadcasts.

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


EMERGENCY_ALERT = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Emergency Alert Service",

    application_id="general.emergency_alert",

    service_class=ServiceClass.GENERAL,

    description=(

        "Government emergency notification service for "
        "broadcasting disaster warnings, evacuation notices "
        "and public safety alerts."

    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.UDP,

    transport_mode="broadcast",

    default_port=5001,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=350,

        std=40,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=2,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=30,

        std=10,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=0.2,

        std=0.05,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=15,

    jitter_requirement_ms=5,

    packet_loss_requirement_pct=0.01,

    throughput_requirement_mbps=0.1,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.CRITICAL,

    slice_type=SliceType.URLLC,

    mobility=MobilityProfile.PEDESTRIAN,

    device_type=DeviceType.SMARTPHONE,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "broadcast_type": "Public Safety",

        "supports_cell_broadcast": True,

        "supports_disaster_warning": True,

        "supports_geo_targeting": True,

        "acknowledgement_required": False,

    },

)