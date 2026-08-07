from dataclasses import dataclass
from traffic.enums import (
    ServiceClass,
    TransportProtocol,
    TrafficPattern,
    QoSClass,
)


@dataclass(slots=True)
class ApplicationProfile:
    """
    Complete behavioral specification of an application.

    Every traffic generator samples an ApplicationProfile
    to generate realistic network traffic.
    """

    application_name: str

    service_class: ServiceClass

    transport_protocol: TransportProtocol

    destination_port: int

    traffic_pattern: TrafficPattern

    qos_class: QoSClass

    average_packet_size: int          # Bytes

    average_bitrate_mbps: float

    session_duration_sec: int

    priority: int