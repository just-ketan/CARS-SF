"""
Attendance System

Represents RFID, NFC, QR-code and biometric attendance
systems used in educational institutions.

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


ATTENDANCE_SYSTEM = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Attendance System",

    application_id="education.attendance_system",

    service_class=ServiceClass.EDUCATION,

    description=(
        "Automated attendance system using RFID, NFC, QR "
        "codes or biometric authentication."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.TCP,

    transport_mode="transactional",

    default_port=443,

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

        rate=8,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=15,

        std=5,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=0.05,

        std=0.01,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=150,

    jitter_requirement_ms=40,

    packet_loss_requirement_pct=1.0,

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

        "authentication": "RFID/NFC/Biometric",

        "transaction_type": "Attendance",

        "cloud_sync": True,

    },

)