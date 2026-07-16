"""
Normal Day Scenario

Represents routine network conditions in a rural deployment.
Serves as the baseline scenario for all experiments.
"""

from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass


NORMAL_DAY = Scenario(

    # ======================================================
    # Identity
    # ======================================================

    name="Normal Day",

    description=(
        "Routine operating conditions with balanced "
        "network utilization across all rural services."
    ),

    # ======================================================
    # Network Conditions
    # ======================================================

    network_load_range=(35.0, 60.0),

    cell_load_range=(30.0, 55.0),

    active_users_range=(80, 180),

    signal_strength_range=(-95.0, -75.0),

    sinr_range=(15.0, 30.0),

    rsrp_range=(-95.0, -80.0),

    rsrq_range=(-12.0, -6.0),

    # ======================================================
    # Radio
    # ======================================================

    cqi_range=(9, 15),

    resource_blocks_range=(20, 60),

    slice_utilization_range=(30.0, 65.0),

    # ======================================================
    # Preferred Services
    # ======================================================

    preferred_services=[

        ServiceClass.HEALTHCARE,

        ServiceClass.EDUCATION,

        ServiceClass.AGRICULTURE,

        ServiceClass.GENERAL,

    ],

    service_bias_multiplier=3.0,
    
    # ======================================================
    # Misc
    # ======================================================

    handover_probability=0.05,

    daytime="day",

)