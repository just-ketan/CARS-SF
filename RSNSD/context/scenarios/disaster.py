"""
Disaster Scenario

Represents emergency situations such as floods, cyclones,
earthquakes or large-scale accidents where emergency
communications dominate the network.

Author: RSNSD
"""

from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass


DISASTER = Scenario(

    # ======================================================
    # Identity
    # ======================================================

    name="Disaster",

    description=(
        "Emergency operating conditions with overloaded "
        "network resources and priority given to healthcare "
        "and rescue communications."
    ),

    # ======================================================
    # Network Conditions
    # ======================================================

    network_load_range=(90.0, 100.0),

    cell_load_range=(90.0, 100.0),

    active_users_range=(500, 1200),

    signal_strength_range=(-112.0, -92.0),

    sinr_range=(2.0, 12.0),

    rsrp_range=(-115.0, -95.0),

    rsrq_range=(-18.0, -11.0),

    # ======================================================
    # Radio
    # ======================================================

    cqi_range=(2, 8),

    resource_blocks_range=(85, 100),

    slice_utilization_range=(95.0, 100.0),

    # ======================================================
    # Preferred Services
    # ======================================================

    preferred_services=[

        ServiceClass.HEALTHCARE,

        ServiceClass.GENERAL,

    ],

    service_bias_multiplier=3.0,

    # ======================================================
    # Misc
    # ======================================================

    handover_probability=0.40,

    daytime="day",

)