"""
Health Monitoring Application Profile

Periodic health monitoring from wearable and home healthcare
IoT devices for chronic disease management and elderly care.

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


HEALTH_MONITORING = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Health Monitoring",

    application_id="healthcare.health_monitoring",

    service_class=ServiceClass.HEALTHCARE,

    description=(
        "Periodic transmission of physiological measurements "
        "from wearable healthcare devices."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.UDP,

    transport_mode="uplink",

    default_port=5004,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=256,
        std=24,
    ),

    inter_arrival_distribution=Distribution(
        distribution=DistributionType.CONSTANT,
        value=30.0,
    ),

    session_duration_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=86400,
        std=7200,
    ),

    bitrate_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=0.05,
        std=0.01,
    ),

    # ======================================================
    # QoS Requirements
    # ======================================================

    latency_requirement_ms=250,

    jitter_requirement_ms=50,

    packet_loss_requirement_pct=1.0,

    throughput_requirement_mbps=0.05,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.MEDIUM,

    slice_type=SliceType.MMTC,

    mobility=MobilityProfile.PEDESTRIAN,

    device_type=DeviceType.SENSOR,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "heart_rate": True,

        "blood_pressure": True,

        "blood_oxygen": True,

        "body_temperature": True,

        "fall_detection": True,

        "battery_powered": True,

    },

)