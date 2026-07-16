"""
Precision Agriculture Analytics

Represents AI-powered precision agriculture platforms that
aggregate sensor data, drone imagery and machinery telemetry
to generate actionable insights for farmers.

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


PRECISION_AGRICULTURE = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Precision Agriculture Analytics",

    application_id="agriculture.precision_agriculture",

    service_class=ServiceClass.AGRICULTURE,

    description=(
        "AI-driven precision agriculture platform performing "
        "crop analytics, yield prediction, disease detection "
        "and farm management using multi-source data."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.TCP,

    transport_mode="bidirectional",

    default_port=443,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1400,

        std=120,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=100,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=3600,

        std=600,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=10.0,

        std=2.0,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=150,

    jitter_requirement_ms=40,

    packet_loss_requirement_pct=1.0,

    throughput_requirement_mbps=8.0,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.MEDIUM,

    slice_type=SliceType.EMBB,

    mobility=MobilityProfile.STATIC,

    device_type=DeviceType.GATEWAY,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "analytics_modules": [

            "yield_prediction",

            "crop_health_analysis",

            "disease_detection",

            "fertilizer_recommendation",

            "irrigation_optimization",

            "weather_forecasting",

        ],

        "supports_ai_models": True,

        "supports_satellite_data": True,

        "supports_drone_imagery": True,

    },

)