"""
Smart Irrigation

Represents intelligent irrigation systems that monitor soil
conditions and automatically control irrigation equipment.

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


SMART_IRRIGATION = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Smart Irrigation",

    application_id="agriculture.smart_irrigation",

    service_class=ServiceClass.AGRICULTURE,

    description=(
        "Automated irrigation system using environmental "
        "sensors and remotely controlled irrigation valves."
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

        mean=180,

        std=30,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=12,

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

    latency_requirement_ms=300,

    jitter_requirement_ms=100,

    packet_loss_requirement_pct=2.0,

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

        "communication_protocol": "MQTT",

        "sensor_types": [

            "soil_moisture",

            "water_flow",

            "valve_status",

        ],

        "power_source": "Solar Battery",

        "automatic_control": True,

    },

)