"""
Livestock Monitoring

Represents wearable IoT devices attached to livestock for
tracking health, location and activity in smart farming.

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


LIVESTOCK_MONITORING = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Livestock Monitoring",

    application_id="agriculture.livestock_monitoring",

    service_class=ServiceClass.AGRICULTURE,

    description=(
        "Wearable IoT devices for continuous livestock "
        "tracking, health monitoring and geolocation."
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

        mean=250,

        std=40,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=8,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=43200,

        std=3600,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=0.12,

        std=0.03,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=250,

    jitter_requirement_ms=80,

    packet_loss_requirement_pct=2.0,

    throughput_requirement_mbps=0.08,

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

        "animal_types": [

            "cattle",

            "buffalo",

            "sheep",

            "goat",

        ],

        "measurements": [

            "gps_location",

            "body_temperature",

            "heart_rate",

            "activity_level",

        ],

        "battery_life_days": 30,

        "gps_enabled": True,

    },

)