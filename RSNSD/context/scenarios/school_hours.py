"""
School Hours Scenario

Represents peak educational activity in rural schools.
Network usage is dominated by digital classrooms,
student devices and educational services.
"""

from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass


SCHOOL_HOURS = Scenario(

    # ======================================================
    # Identity
    # ======================================================

    name="School Hours",

    description=(
        "Peak educational activity with high student density "
        "and increased demand for online learning services."
    ),

    # ======================================================
    # Network Conditions
    # ======================================================

    network_load_range=(70.0, 90.0),

    cell_load_range=(65.0, 90.0),

    active_users_range=(250, 450),

    signal_strength_range=(-98.0, -80.0),

    sinr_range=(10.0, 22.0),

    rsrp_range=(-100.0, -82.0),

    rsrq_range=(-14.0, -8.0),

    # ======================================================
    # Radio
    # ======================================================

    cqi_range=(7, 12),

    resource_blocks_range=(50, 95),

    slice_utilization_range=(70.0, 95.0),

    # ======================================================
    # Preferred Services
    # ======================================================

    preferred_services=[

        ServiceClass.EDUCATION,

        ServiceClass.GENERAL,

        ServiceClass.HEALTHCARE,

    ],

    service_bias_multiplier=3.0,
    
    # ======================================================
    # Misc
    # ======================================================

    handover_probability=0.10,

    daytime="day",

)