"""
Voice over IP

Represents real-time voice communication services including
VoLTE, VoNR, VoIP and internet calling applications.

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


VOICE_OVER_IP = ApplicationProfile(

    # ======================================================
    # Identity
    # ======================================================

    name="Voice over IP",

    application_id="general.voice_over_ip",

    service_class=ServiceClass.GENERAL,

    description=(
        "Real-time voice communication including VoLTE, "
        "VoNR and internet calling services."
    ),

    # ======================================================
    # Network Behaviour
    # ======================================================

    protocol=TransportProtocol.UDP,

    transport_mode="bidirectional",

    default_port=5060,

    # ======================================================
    # Traffic Characteristics
    # ======================================================

    packet_size_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=220,

        std=30,

    ),

    inter_arrival_distribution=Distribution(

        distribution=DistributionType.EXPONENTIAL,

        rate=50,

    ),

    session_duration_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=420,

        std=180,

    ),

    bitrate_distribution=Distribution(

        distribution=DistributionType.NORMAL,

        mean=0.12,

        std=0.03,

    ),

    # ======================================================
    # QoS Targets
    # ======================================================

    latency_requirement_ms=20,

    jitter_requirement_ms=5,

    packet_loss_requirement_pct=0.5,

    throughput_requirement_mbps=0.1,

    # ======================================================
    # Service Context
    # ======================================================

    priority=PriorityLevel.HIGH,

    slice_type=SliceType.URLLC,

    mobility=MobilityProfile.PEDESTRIAN,

    device_type=DeviceType.SMARTPHONE,

    # ======================================================
    # Metadata
    # ======================================================

    metadata={

        "codec": "AMR-WB",

        "supports_hd_voice": True,

        "echo_cancellation": True,

        "sample_rate_hz": 16000,

    },

)