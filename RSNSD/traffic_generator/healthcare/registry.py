"""
Healthcare Application Registry

Central registry of all healthcare application profiles used
for synthetic dataset generation.

Author: RSNSD
"""

from .telemedicine import TELEMEDICINE
from .remote_surgery import REMOTE_SURGERY
from .ecg_streaming import ECG_STREAMING
from .ambulance import AMBULANCE_TELEMETRY
from .health_monitoring import HEALTH_MONITORING
from .medical_imaging import MEDICAL_IMAGING
from .pharmacy import PHARMACY_SERVICE
from .emergency_voice import EMERGENCY_VOICE


# ==========================================================
# Registry
# ==========================================================

HEALTHCARE_PROFILE_REGISTRY = [

    TELEMEDICINE,

    REMOTE_SURGERY,

    ECG_STREAMING,

    AMBULANCE_TELEMETRY,

    HEALTH_MONITORING,

    MEDICAL_IMAGING,

    PHARMACY_SERVICE,

    EMERGENCY_VOICE,

]


# ==========================================================
# Realistic Traffic Distribution
#
# Weights roughly represent relative occurrence frequency
# in a rural healthcare deployment.
# ==========================================================

HEALTHCARE_PROFILE_WEIGHTS = [

    0.30,   # Telemedicine

    0.02,   # Remote Surgery

    0.15,   # ECG Streaming

    0.08,   # Ambulance

    0.25,   # Health Monitoring

    0.08,   # Medical Imaging

    0.08,   # Pharmacy

    0.04,   # Emergency Voice

]


assert len(HEALTHCARE_PROFILE_REGISTRY) == len(
    HEALTHCARE_PROFILE_WEIGHTS
)