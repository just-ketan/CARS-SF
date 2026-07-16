"""
Festival Scenario

Represents large-scale rural gatherings during festivals,
religious events and community celebrations. This scenario
produces extremely high user density and multimedia traffic.
"""

from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass


FESTIVAL = Scenario(

    # ======================================================
    # Identity
    # ======================================================

    name="Festival",

    description=(
        "Large public gathering with high demand for voice, "
        "video streaming, social media and emergency services."
    ),

    # ======================================================
    # Network Conditions
    # ======================================================

    network_load_range=(85.0, 98.0),

    cell_load_range=(80.0, 98.0),

    active_users_range=(400, 900),

    signal_strength_range=(-102.0, -82.0),

    sinr_range=(8.0, 20.0),

    rsrp_range=(-104.0, -84.0),

    rsrq_range=(-15.0, -8.0),

    # ======================================================
    # Radio
    # ======================================================

    cqi_range=(6, 11),

    resource_blocks_range=(70, 100),

    slice_utilization_range=(85.0, 100.0),

    # ======================================================
    # Preferred Services
    # ======================================================

    preferred_services=[

        ServiceClass.GENERAL,

        ServiceClass.HEALTHCARE,

    ],

    service_bias_multiplier=3.0,

    # ======================================================
    # Misc
    # ======================================================

    handover_probability=0.25,

    daytime="day",

)