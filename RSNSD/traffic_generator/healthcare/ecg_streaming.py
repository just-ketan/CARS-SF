"""
ECG Streaming Application Profile

Continuous electrocardiogram (ECG) streaming from wearable
or bedside medical devices to edge/cloud healthcare systems.

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


ECG_STREAMING = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="ECG Streaming",

    application_id="healthcare.ecg_streaming",

    service_class=ServiceClass.HEALTHCARE,

    description=(
        "Continuous ECG waveform transmission for remote "
        "cardiac monitoring."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.TCP,

    transport_mode="uplink",

    default_port=5002,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=512,
        std=32,
    ),

    inter_arrival_distribution=Distribution(
        distribution=DistributionType.CONSTANT,
        value=0.02,
    ),

    session_duration_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=86400,
        std=3600,
    ),

    bitrate_distribution=Distribution(
        distribution=DistributionType.NORMAL,
        mean=0.5,
        std=0.1,
    ),

    # ======================================================
    # QoS
    # ======================================================

    latency_requirement_ms=50,

    jitter_requirement_ms=10,

    packet_loss_requirement_pct=0.1,

    throughput_requirement_mbps=0.5,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.HIGH,

    slice_type=SliceType.URLLC,

    mobility=MobilityProfile.PEDESTRIAN,

    device_type=DeviceType.SENSOR,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "sampling_rate_hz": 500,

        "channels": 12,

        "compression": "Lossless",

        "alarm_enabled": True,

    },

)