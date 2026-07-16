from typing import List, Literal
from pydantic import BaseModel, Field


class QoSProfile(BaseModel):
    latency_ms: float = Field(..., ge=0)
    jitter_ms: float = Field(..., ge=0)
    reliability: float = Field(..., ge=0, le=100)
    bandwidth_mbps: float = Field(..., ge=0)


class SliceProfile(BaseModel):
    type: Literal["URLLC", "eMBB", "mMTC"]
    priority: Literal["Critical", "High", "Medium", "Low"]


class TrafficProfile(BaseModel):
    protocol: str
    transport: Literal["TCP", "UDP"]
    average_packet_size: int
    packet_rate: float
    average_session_duration: float


class Application(BaseModel):
    id: str
    name: str
    description: str
    traffic: TrafficProfile


class Service(BaseModel):
    id: str
    name: str
    description: str

    slice: SliceProfile
    qos: QoSProfile

    applications: List[Application]