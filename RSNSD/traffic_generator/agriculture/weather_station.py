"""
Weather Station

Represents automated agricultural weather stations that
continuously monitor environmental conditions to support
precision farming operations.

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


WEATHER_STATION = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Weather Station",

    application_id="agriculture.weather_station",

    service_class=ServiceClass.AGRICULTURE,

    description=(
        "Automated weather station providing real-time "
        "environmental measurements for precision farming."
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

        std=35,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=6,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=86400,

        std=3600,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=0.08,

        std=0.02,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=500,

    jitter_requirement_ms=150,

    packet_loss_requirement_pct=3.0,

    throughput_requirement_mbps=0.05,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.LOW,

    slice_type=SliceType.MMTC,

    mobility=MobilityProfile.STATIC,

    device_type=DeviceType.SENSOR,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "measurements": [

            "temperature",

            "humidity",

            "wind_speed",

            "wind_direction",

            "rainfall",

            "solar_radiation",

            "air_pressure",

        ],

        "sampling_interval_minutes": 10,

        "power_source": "Solar Battery",

    },

)