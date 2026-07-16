"""
Machinery Telemetry

Represents connected agricultural machinery continuously
reporting operational status, diagnostics and maintenance
information to farm management systems.

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


MACHINERY_TELEMETRY = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Farm Machinery Telemetry",

    application_id="agriculture.machinery_telemetry",

    service_class=ServiceClass.AGRICULTURE,

    description=(
        "Real-time telemetry and diagnostics for connected "
        "agricultural machinery supporting predictive "
        "maintenance and fleet management."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.TCP,

    transport_mode="bidirectional",

    default_port=8883,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=520,

        std=80,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=60,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=28800,

        std=3600,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1.5,

        std=0.3,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=30,

    jitter_requirement_ms=10,

    packet_loss_requirement_pct=0.1,

    throughput_requirement_mbps=1.0,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.HIGH,

    slice_type=SliceType.URLLC,

    mobility=MobilityProfile.VEHICULAR,

    device_type=DeviceType.VEHICLE,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "monitored_parameters": [

            "engine_rpm",

            "fuel_level",

            "engine_temperature",

            "hydraulic_pressure",

            "battery_voltage",

            "gps_location",

            "maintenance_status",

        ],

        "supports_remote_diagnostics": True,

        "supports_predictive_maintenance": True,

        "fleet_management": True,

    },

)