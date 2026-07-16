"""
Healthcare Traffic Profiles
"""

from .telemedicine import TELEMEDICINE
from .remote_surgery import REMOTE_SURGERY
from .ecg_streaming import ECG_STREAMING
from .ambulance import AMBULANCE_TELEMETRY
from .health_monitoring import HEALTH_MONITORING
from .medical_imaging import MEDICAL_IMAGING
from .pharmacy import PHARMACY_SERVICE
from .emergency_voice import EMERGENCY_VOICE

from .registry import (
    HEALTHCARE_PROFILE_REGISTRY,
    HEALTHCARE_PROFILE_WEIGHTS,
)