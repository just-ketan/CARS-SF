from enum import Enum


class ServiceClass(Enum):
    HEALTHCARE = "Healthcare"
    EDUCATION = "Education"
    AGRICULTURE = "Agriculture"
    INTERNET = "General Internet"
    EMERGENCY = "Emergency"
    GOVERNMENT = "Government"
    INDUSTRIAL_IOT = "Industrial IoT"


class TransportProtocol(Enum):
    TCP = "TCP"
    UDP = "UDP"


class TrafficPattern(Enum):
    CONSTANT = "Constant"
    PERIODIC = "Periodic"
    BURSTY = "Bursty"
    INTERACTIVE = "Interactive"


class QoSClass(Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    BEST_EFFORT = "Best Effort"