"""
Agriculture Application Registry

Central registry of all agriculture application profiles.

Author: RSNSD
"""

from .autonomous_tractor import AUTONOMOUS_TRACTOR
from .crop_surveillance import CROP_SURVEILLANCE
from .livestock_monitoring import LIVESTOCK_MONITORING
from .machinery_telemetry import MACHINERY_TELEMETRY
from .precision_agriculture import PRECISION_AGRICULTURE
from .smart_irrigation import SMART_IRRIGATION
from .soil_monitoring import SOIL_MONITORING
from .weather_station import WEATHER_STATION


# ==========================================================
# Registry
# ==========================================================

AGRICULTURE_PROFILE_REGISTRY = [

    SMART_IRRIGATION,

    SOIL_MONITORING,

    WEATHER_STATION,

    LIVESTOCK_MONITORING,

    CROP_SURVEILLANCE,

    AUTONOMOUS_TRACTOR,

    MACHINERY_TELEMETRY,

    PRECISION_AGRICULTURE,

]

# ==========================================================
# Sampling Weights
# ==========================================================

AGRICULTURE_PROFILE_WEIGHTS = [

    0.18,   # Smart Irrigation

    0.15,   # Soil Monitoring

    0.12,   # Weather Station

    0.12,   # Livestock Monitoring

    0.12,   # Crop Surveillance

    0.10,   # Autonomous Tractor

    0.11,   # Machinery Telemetry

    0.10,   # Precision Agriculture

]

assert abs(sum(AGRICULTURE_PROFILE_WEIGHTS) - 1.0) < 1e-6