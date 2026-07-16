"""
Rainfall Scenario

Represents adverse weather conditions affecting rural
wireless communication. Rain attenuation and environmental
conditions degrade radio quality while critical services
continue to operate.

Author: RSNSD
"""

from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass


RAINFALL = Scenario(

    # ======================================================
    # Identity
    # ======================================================

    name="Heavy Rainfall",

    description=(
        "Adverse weather causing degraded radio conditions "
        "and reduced network performance."
    ),

    # ======================================================
    # Network Conditions
    # ======================================================

    network_load_range=(45.0, 75.0),

    cell_load_range=(40.0, 70.0),

    active_users_range=(90, 220),

    signal_strength_range=(-108.0, -90.0),

    sinr_range=(5.0, 15.0),

    rsrp_range=(-110.0, -92.0),

    rsrq_range=(-17.0, -10.0),

    # ======================================================
    # Radio
    # ======================================================

    cqi_range=(4, 9),

    resource_blocks_range=(40, 75),

    slice_utilization_range=(45.0, 75.0),

    # ======================================================
    # Preferred Services
    # ======================================================

    preferred_services=[

        ServiceClass.HEALTHCARE,

        ServiceClass.GENERAL,

        ServiceClass.AGRICULTURE,

    ],

    service_bias_multiplier=3.0,
    
    # ======================================================
    # Misc
    # ======================================================

    handover_probability=0.20,

    daytime="day",

)