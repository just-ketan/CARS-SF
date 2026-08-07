from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass

ELECTION = Scenario(
    name="Election",
    description="Regional elections triggering high general traffic, mobile polling, and live news streams.",
    network_load_range=(80.0, 95.0),
    cell_load_range=(75.0, 95.0),
    active_users_range=(1200, 2500),
    signal_strength_range=(-110.0, -85.0),
    sinr_range=(5.0, 12.0),
    rsrp_range=(-100.0, -85.0),
    rsrq_range=(-14.0, -9.0),
    cqi_range=(4, 10),
    resource_blocks_range=(80, 95),
    slice_utilization_range=(80.0, 98.0),
    preferred_services=[ServiceClass.GENERAL],
    service_bias_multiplier=2.0,
    handover_probability=0.30,
    daytime="day",
)
