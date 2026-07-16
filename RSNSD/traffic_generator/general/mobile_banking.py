"""
Mobile Banking

Represents secure financial transactions including mobile
banking, UPI payments, digital wallets and online financial
services.

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


MOBILE_BANKING = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Mobile Banking",

    application_id="general.mobile_banking",

    service_class=ServiceClass.GENERAL,

    description=(

        "Secure digital banking supporting fund transfers, "
        "UPI payments, account management and financial "
        "transactions."

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

        mean=450,

        std=80,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=20,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=300,

        std=120,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=0.5,

        std=0.1,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=40,

    jitter_requirement_ms=10,

    packet_loss_requirement_pct=0.05,

    throughput_requirement_mbps=0.3,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.CRITICAL,

    slice_type=SliceType.URLLC,

    mobility=MobilityProfile.PEDESTRIAN,

    device_type=DeviceType.SMARTPHONE,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "supports_upi": True,

        "supports_biometrics": True,

        "supports_two_factor_authentication": True,

        "encryption": "TLS 1.3",

        "transaction_type": "Financial",

    },

)