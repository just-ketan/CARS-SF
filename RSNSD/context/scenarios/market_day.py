"""
Market Day Scenario

Represents weekly village market activity where a large
number of people gather in a concentrated geographical area,
leading to temporary spikes in network utilization.
"""

from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass


MARKET_DAY = Scenario(

    # ======================================================
    # Identity
    # ======================================================

    name="Market Day",

    description=(
        "Weekly rural market with increased commercial, "
        "banking, communication and mobile internet usage."
    ),

    # ======================================================
    # Network Conditions
    # ======================================================

    network_load_range=(65.0, 88.0),

    cell_load_range=(60.0, 85.0),

    active_users_range=(220, 420),

    signal_strength_range=(-98.0, -78.0),

    sinr_range=(10.0, 24.0),

    rsrp_range=(-100.0, -80.0),

    rsrq_range=(-13.0, -7.0),

    # ======================================================
    # Radio
    # ======================================================

    cqi_range=(8, 13),

    resource_blocks_range=(45, 90),

    slice_utilization_range=(65.0, 90.0),

    # ======================================================
    # Preferred Services
    # ======================================================

    preferred_services=[

        ServiceClass.GENERAL,

        ServiceClass.AGRICULTURE,

        ServiceClass.HEALTHCARE,

    ],

    service_bias_multiplier=3.0,

    # ======================================================
    # Misc
    # ======================================================

    handover_probability=0.18,

    daytime="day",

)