from traffic.application_profile import ApplicationProfile
from traffic.enums import *


ZOOM_CLASS = ApplicationProfile(
    application_name="Zoom Meeting",

    service_class=ServiceClass.EDUCATION,

    transport_protocol=TransportProtocol.UDP,

    destination_port=8801,

    traffic_pattern=TrafficPattern.INTERACTIVE,

    qos_class=QoSClass.HIGH,

    average_packet_size=1200,

    average_bitrate_mbps=3.5,

    session_duration_sec=180,

    priority=2,
)