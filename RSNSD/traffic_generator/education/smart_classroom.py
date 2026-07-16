"""
Smart Classroom

Represents IoT-enabled smart classroom infrastructure
including environmental sensors, smart lighting,
projectors, occupancy monitoring and automation.

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


SMART_CLASSROOM = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Smart Classroom",

    application_id="education.smart_classroom",

    service_class=ServiceClass.EDUCATION,

    description=(
        "IoT-enabled classroom automation including smart "
        "lighting, occupancy monitoring, environmental "
        "sensors and intelligent classroom devices."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.UDP,

    transport_mode="periodic",

    default_port=1883,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=220,

        std=40,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=15,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=28800,

        std=1800,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=0.25,

        std=0.05,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=200,

    jitter_requirement_ms=80,

    packet_loss_requirement_pct=2.0,

    throughput_requirement_mbps=0.2,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.MEDIUM,

    slice_type=SliceType.MMTC,

    mobility=MobilityProfile.STATIC,

    device_type=DeviceType.SENSOR,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "sensor_types": [
            "temperature",
            "humidity",
            "occupancy",
            "light",
        ],

        "communication": "MQTT",

        "battery_powered": True,

    },

)