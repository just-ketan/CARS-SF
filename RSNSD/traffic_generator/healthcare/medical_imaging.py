"""
Medical Imaging Application Profile

Transmission of high-resolution medical images such as CT,
MRI, X-ray, PET and ultrasound between healthcare facilities,
edge servers and cloud-based diagnostic systems.

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


MEDICAL_IMAGING = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Medical Imaging",

    application_id="healthcare.medical_imaging",

    service_class=ServiceClass.HEALTHCARE,

    description=(
        "Transfer of high-resolution medical images for "
        "remote diagnosis and AI-assisted radiology."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.TCP,

    transport_mode="uplink",

    default_port=5005,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=1450,
        std=20,
    ),

    inter_arrival_distribution=Distribution(
        distribution=DistributionType.CONSTANT,
        value=0.002,
    ),

    session_duration_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=900,
        std=120,
    ),

    bitrate_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=120,
        std=15,
    ),

    # ======================================================
    # QoS Requirements
    # ======================================================

    latency_requirement_ms=100,

    jitter_requirement_ms=20,

    packet_loss_requirement_pct=0.1,

    throughput_requirement_mbps=100,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.HIGH,

    slice_type=SliceType.EMBB,

    mobility=MobilityProfile.STATIC,

    device_type=DeviceType.GATEWAY,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "image_type": "MRI",

        "image_resolution": "4096x4096",

        "compression": "Lossless",

        "dicom": True,

        "ai_assisted_diagnosis": True,

    },

)