@dataclass
class Service:
    id: str
    name: str
    priority: str
    qos: QoSProfile
    applications: list[Application]

@dataclass
class QoSProfile:
    latency_ms: float
    jitter_ms: float
    reliability: float
    bandwidth_mbps: float

@dataclass 
class Application:
    name: str
    protocol: str
    transport: str
    packet_distribution: str
    avg_packet_size: float
    session_duration: float

