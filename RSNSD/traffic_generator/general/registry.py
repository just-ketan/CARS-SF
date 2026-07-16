"""
General Application Registry

Central registry of all general application profiles.

Author: RSNSD
"""

from .e_governance import E_GOVERNANCE
from .emergency_alert import EMERGENCY_ALERT
from .mobile_banking import MOBILE_BANKING
from .social_media import SOCIAL_MEDIA
from .video_conferencing import VIDEO_CONFERENCING
from .video_streaming import VIDEO_STREAMING
from .voice_over_ip import VOICE_OVER_IP
from .web_browsing import WEB_BROWSING


# ==========================================================
# Registry
# ==========================================================

GENERAL_PROFILE_REGISTRY = [

    WEB_BROWSING,

    VIDEO_STREAMING,

    VOICE_OVER_IP,

    VIDEO_CONFERENCING,

    MOBILE_BANKING,

    SOCIAL_MEDIA,

    E_GOVERNANCE,

    EMERGENCY_ALERT,

]

# ==========================================================
# Sampling Weights
# ==========================================================

GENERAL_PROFILE_WEIGHTS = [

    0.20,   # Web Browsing

    0.22,   # Video Streaming

    0.10,   # Voice over IP

    0.12,   # Video Conferencing

    0.08,   # Mobile Banking

    0.16,   # Social Media

    0.07,   # E-Governance

    0.05,   # Emergency Alert

]

assert abs(sum(GENERAL_PROFILE_WEIGHTS) - 1.0) < 1e-6