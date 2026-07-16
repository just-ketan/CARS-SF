"""
Autonomous Tractor

Represents autonomous agricultural machinery requiring
ultra-low latency communication for navigation, control,
and safety-critical farming operations.

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


AUTONOMOUS_TRACTOR = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Autonomous Tractor",

    application_id="agriculture.autonomous_tractor",

    service_class=ServiceClass.AGRICULTURE,

    description=(
        "Autonomous farming vehicle performing precision "
        "operations using real-time navigation, obstacle "
        "avoidance and remote supervision."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.UDP,

    transport_mode="bidirectional",

    default_port=5000,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=700,

        std=100,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=300,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=14400,

        std=1800,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=4.0,

        std=0.8,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=10,

    jitter_requirement_ms=3,

    packet_loss_requirement_pct=0.01,

    throughput_requirement_mbps=3.0,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.CRITICAL,

    slice_type=SliceType.URLLC,

    mobility=MobilityProfile.VEHICULAR,

    device_type=DeviceType.VEHICLE,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "automation_level": "Fully Autonomous",

        "gps_enabled": True,

        "rtk_supported": True,

        "supports_obstacle_detection": True,

        "implements_auto_steering": True,

    },

)