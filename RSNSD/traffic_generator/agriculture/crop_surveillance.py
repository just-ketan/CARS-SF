"""
Crop Surveillance Drone

Represents UAV-based crop monitoring using HD cameras,
multispectral sensors and AI-assisted crop inspection.

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


CROP_SURVEILLANCE = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Crop Surveillance Drone",

    application_id="agriculture.crop_surveillance",

    service_class=ServiceClass.AGRICULTURE,

    description=(
        "Autonomous drone performing crop monitoring using "
        "high-definition video and multispectral imaging."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.UDP,

    transport_mode="uplink_stream",

    default_port=5600,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1350,

        std=120,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=250,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=1800,

        std=300,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=18.0,

        std=4.0,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=80,

    jitter_requirement_ms=20,

    packet_loss_requirement_pct=1.0,

    throughput_requirement_mbps=15.0,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.HIGH,

    slice_type=SliceType.EMBB,

    mobility=MobilityProfile.AERIAL,

    device_type=DeviceType.DRONE,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "camera_resolution": "4K",

        "camera_type": "RGB + Multispectral",

        "fps": 30,

        "flight_altitude_m": 120,

        "supports_ai_detection": True,

    },

)