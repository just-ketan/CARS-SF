from pydantic import BaseModel

class QoSProfile(BaseModel):
    latency_ms: float
    jitter_ms: float
    reliability: float
    bandwidth_mbps: float

class Application(BaseModel):
    name: str
    protocol: str
    transport: str
    packet_distribution: str
    avg_packet_size: float
    session_duration: float

class Service(BaseModel):
    id: str
    name: str
    priority: str
    qos: QoSProfile
    applications: list[Application]

