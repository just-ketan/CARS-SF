"""
Harvest Season Scenario

Represents peak agricultural activity during harvest.
Network resources are dominated by precision agriculture,
IoT sensors, drones and agricultural machinery.
"""

from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass


HARVEST = Scenario(

    # ======================================================
    # Identity
    # ======================================================

    name="Harvest Season",

    description=(
        "Peak agricultural operations with intensive IoT, "
        "drone monitoring and machinery telemetry."
    ),

    # ======================================================
    # Network Conditions
    # ======================================================

    network_load_range=(55.0, 80.0),

    cell_load_range=(45.0, 70.0),

    active_users_range=(120, 250),

    signal_strength_range=(-100.0, -82.0),

    sinr_range=(12.0, 25.0),

    rsrp_range=(-102.0, -84.0),

    rsrq_range=(-13.0, -7.0),

    # ======================================================
    # Radio
    # ======================================================

    cqi_range=(8, 13),

    resource_blocks_range=(35, 70),

    slice_utilization_range=(55.0, 80.0),

    # ======================================================
    # Preferred Services
    # ======================================================

    preferred_services=[

        ServiceClass.AGRICULTURE,

        ServiceClass.GENERAL,

        ServiceClass.HEALTHCARE,

    ],

    service_bias_multiplier=3.0,

    # ======================================================
    # Misc
    # ======================================================

    handover_probability=0.15,

    daytime="day",

)