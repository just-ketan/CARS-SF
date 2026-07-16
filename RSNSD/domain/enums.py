"""
Domain Enumerations

These enums define the core concepts used throughout the RSNSD
dataset generation pipeline.
"""

from enum import Enum


# ==========================================================
# Service Classes
# ==========================================================

class ServiceClass(str, Enum):

    HEALTHCARE = "healthcare"

    EDUCATION = "education"

    AGRICULTURE = "agriculture"

    GENERAL = "general"


# ==========================================================
# Network Slice Types
# ==========================================================

class SliceType(str, Enum):

    URLLC = "URLLC"

    EMBB = "eMBB"

    MMTC = "mMTC"


# ==========================================================
# Transport Protocol
# ==========================================================

class TransportProtocol(str, Enum):

    TCP = "TCP"

    UDP = "UDP"


# ==========================================================
# Mobility Profile
# ==========================================================

class MobilityProfile(str, Enum):

    STATIC = "static"

    PEDESTRIAN = "pedestrian"

    VEHICULAR = "vehicular"

    AERIAL = "aerial"


# ==========================================================
# Device Type
# ==========================================================

class DeviceType(str, Enum):

    SMARTPHONE = "smartphone"

    TABLET = "tablet"

    LAPTOP = "laptop"

    SENSOR = "sensor"

    DRONE = "drone"

    VEHICLE = "vehicle"

    GATEWAY = "gateway"


# ==========================================================
# Priority Levels
# ==========================================================

class PriorityLevel(int, Enum):

    CRITICAL = 1

    HIGH = 2

    MEDIUM = 3

    LOW = 4