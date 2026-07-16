"""
Soil Monitoring

Represents distributed soil monitoring sensors used for
precision agriculture. These sensors periodically report
soil properties to assist irrigation and crop management.

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


SOIL_MONITORING = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Soil Monitoring",

    application_id="agriculture.soil_monitoring",

    service_class=ServiceClass.AGRICULTURE,

    description=(
        "Distributed soil monitoring network measuring soil "
        "moisture, pH, nutrients and temperature."
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

        mean=160,

        std=25,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=10,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=86400,

        std=3600,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=0.06,

        std=0.01,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=500,

    jitter_requirement_ms=150,

    packet_loss_requirement_pct=3.0,

    throughput_requirement_mbps=0.03,

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

            "soil_moisture",

            "soil_temperature",

            "soil_ph",

            "electrical_conductivity",

            "nitrogen",

            "phosphorus",

            "potassium",

        ],

        "sampling_interval_minutes": 15,

        "power_source": "Solar Battery",

    },

)