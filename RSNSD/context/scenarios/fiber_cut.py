from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass

FIBER_CUT = Scenario(
    name="Fiber Cut",
    description="Backhaul fiber is severed, pushing traffic onto congested microwave backups or satellite links.",
    network_load_range=(95.0, 100.0),
    cell_load_range=(95.0, 100.0),
    active_users_range=(200, 600),
    signal_strength_range=(-100.0, -80.0),
    sinr_range=(5.0, 15.0),
    rsrp_range=(-95.0, -75.0),
    rsrq_range=(-12.0, -8.0),
    cqi_range=(4, 10),
    resource_blocks_range=(95, 100),
    slice_utilization_range=(98.0, 100.0),
    preferred_services=[],
    service_bias_multiplier=1.0,
    handover_probability=0.05,
    daytime="day",
)
