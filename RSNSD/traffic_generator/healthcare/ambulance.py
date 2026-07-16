"""
Ambulance Telemetry Application Profile

Real-time telemetry from connected ambulances carrying
critical patients towards healthcare facilities.

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


AMBULANCE_TELEMETRY = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Ambulance Telemetry",

    application_id="healthcare.ambulance",

    service_class=ServiceClass.HEALTHCARE,

    description=(
        "Continuous transmission of patient vitals, GPS "
        "location, vehicle telemetry, and emergency data "
        "between ambulance and hospital."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.TCP,

    transport_mode="bidirectional",

    default_port=5003,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=768,
        std=64,
    ),

    inter_arrival_distribution=Distribution(
        distribution=DistributionType.CONSTANT,
        value=0.01,
    ),

    session_duration_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=1800,
        std=300,
    ),

    bitrate_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=8,
        std=1,
    ),

    # ======================================================
    # QoS Requirements
    # ======================================================

    latency_requirement_ms=15,

    jitter_requirement_ms=3,

    packet_loss_requirement_pct=0.05,

    throughput_requirement_mbps=6,

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

        "gps_enabled": True,

        "ecg_stream": True,

        "camera_stream": True,

        "vehicle_speed_updates": True,

        "vital_signs": True,

    },

)