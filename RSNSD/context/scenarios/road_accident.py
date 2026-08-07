from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass

ROAD_ACCIDENT = Scenario(
    name="Road Accident",
    description="Major highway accident. Sudden localized burst of emergency voice and mapping applications.",
    network_load_range=(60.0, 80.0),
    cell_load_range=(70.0, 90.0),
    active_users_range=(300, 700),
    signal_strength_range=(-100.0, -80.0),
    sinr_range=(8.0, 18.0),
    rsrp_range=(-95.0, -75.0),
    rsrq_range=(-12.0, -7.0),
    cqi_range=(7, 13),
    resource_blocks_range=(60, 85),
    slice_utilization_range=(65.0, 90.0),
    preferred_services=[ServiceClass.HEALTHCARE, ServiceClass.GENERAL],
    service_bias_multiplier=3.5,
    handover_probability=0.40,
    daytime="day",
)
