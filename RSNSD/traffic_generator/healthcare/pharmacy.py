"""
Pharmacy Services Application Profile

Electronic prescription management, medicine inventory,
online pharmacy services and healthcare transaction systems.

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


PHARMACY_SERVICE = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Pharmacy Services",

    application_id="healthcare.pharmacy",

    service_class=ServiceClass.HEALTHCARE,

    description=(
        "Electronic prescription processing, medicine "
        "inventory management and pharmacy transactions."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.TCP,

    transport_mode="bidirectional",

    default_port=5006,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=768,
        std=48,
    ),

    inter_arrival_distribution=Distribution(
        distribution=DistributionType.CONSTANT,    
        value=0.25,
    ),

    session_duration_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=300,
        std=60,
    ),

    bitrate_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=2,
        std=0.3,
    ),

    # ======================================================
    # QoS Requirements
    # ======================================================

    latency_requirement_ms=200,

    jitter_requirement_ms=50,

    packet_loss_requirement_pct=1.0,

    throughput_requirement_mbps=2,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.LOW,

    slice_type=SliceType.EMBB,

    mobility=MobilityProfile.STATIC,

    device_type=DeviceType.LAPTOP,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "electronic_prescription": True,

        "inventory_sync": True,

        "payment_gateway": True,

        "barcode_scanner": True,

        "patient_database": True,

    },

)