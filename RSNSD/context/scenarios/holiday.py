from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass

HOLIDAY = Scenario(
    name="Holiday",
    description="Public holiday. Very high baseline usage, but distributed evenly across the day.",
    network_load_range=(70.0, 95.0),
    cell_load_range=(65.0, 90.0),
    active_users_range=(800, 2000),
    signal_strength_range=(-105.0, -80.0),
    sinr_range=(7.0, 15.0),
    rsrp_range=(-95.0, -75.0),
    rsrq_range=(-13.0, -8.0),
    cqi_range=(5, 11),
    resource_blocks_range=(60, 95),
    slice_utilization_range=(70.0, 95.0),
    preferred_services=[ServiceClass.GENERAL],
    service_bias_multiplier=3.0,
    handover_probability=0.20,
    daytime="day",
)
