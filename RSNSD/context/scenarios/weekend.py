from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass

WEEKEND = Scenario(
    name="Weekend",
    description="Normal weekend usage with high recreational streaming and very low educational/agricultural usage.",
    network_load_range=(60.0, 85.0),
    cell_load_range=(55.0, 80.0),
    active_users_range=(600, 1500),
    signal_strength_range=(-105.0, -80.0),
    sinr_range=(8.0, 18.0),
    rsrp_range=(-95.0, -75.0),
    rsrq_range=(-12.0, -7.0),
    cqi_range=(6, 12),
    resource_blocks_range=(50, 85),
    slice_utilization_range=(60.0, 85.0),
    preferred_services=[ServiceClass.GENERAL],
    service_bias_multiplier=2.5,
    handover_probability=0.15,
    daytime="day",
)
