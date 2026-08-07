from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass

FIRE = Scenario(
    name="Fire",
    description="Rapidly spreading fire causing evacuations. Heavy network load from alerts and location tracking.",
    network_load_range=(80.0, 100.0),
    cell_load_range=(85.0, 100.0),
    active_users_range=(400, 1500),
    signal_strength_range=(-110.0, -90.0),
    sinr_range=(3.0, 10.0),
    rsrp_range=(-110.0, -95.0),
    rsrq_range=(-15.0, -10.0),
    cqi_range=(4, 9),
    resource_blocks_range=(90, 100),
    slice_utilization_range=(90.0, 100.0),
    preferred_services=[ServiceClass.HEALTHCARE, ServiceClass.GENERAL],
    service_bias_multiplier=4.0,
    handover_probability=0.60,
    daytime="day",
)
