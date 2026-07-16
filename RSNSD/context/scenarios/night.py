"""
Night Scenario

Represents off-peak nighttime operation in rural networks.
Most human activity has ceased, leaving background IoT,
healthcare monitoring and essential services active.

Author: RSNSD
"""

from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass


NIGHT = Scenario(

    # ======================================================
    # Identity
    # ======================================================

    name="Night",

    description=(
        "Off-peak network operation with low user density "
        "and predominantly background traffic."
    ),

    # ======================================================
    # Network Conditions
    # ======================================================

    network_load_range=(10.0, 30.0),

    cell_load_range=(10.0, 25.0),

    active_users_range=(20, 80),

    signal_strength_range=(-90.0, -70.0),

    sinr_range=(20.0, 35.0),

    rsrp_range=(-90.0, -72.0),

    rsrq_range=(-10.0, -5.0),

    # ======================================================
    # Radio
    # ======================================================

    cqi_range=(12, 15),

    resource_blocks_range=(10, 35),

    slice_utilization_range=(10.0, 30.0),

    # ======================================================
    # Preferred Services
    # ======================================================

    preferred_services=[

        ServiceClass.HEALTHCARE,

        ServiceClass.AGRICULTURE,

        ServiceClass.GENERAL,

    ],

    service_bias_multiplier=3.0,
    
    # ======================================================
    # Misc
    # ======================================================

    handover_probability=0.02,

    daytime="night",

)