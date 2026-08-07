from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass

FLOOD = Scenario(
    name="Flood",
    description="Widespread water damage disrupting normal agriculture and knocking out lower elevation cell sites.",
    network_load_range=(60.0, 95.0),
    cell_load_range=(70.0, 100.0),
    active_users_range=(200, 800),
    signal_strength_range=(-120.0, -100.0),
    sinr_range=(0.0, 8.0),
    rsrp_range=(-125.0, -105.0),
    rsrq_range=(-20.0, -15.0),
    cqi_range=(1, 6),
    resource_blocks_range=(70, 100),
    slice_utilization_range=(85.0, 100.0),
    preferred_services=[ServiceClass.HEALTHCARE, ServiceClass.GENERAL],
    service_bias_multiplier=2.5,
    handover_probability=0.20,
    daytime="day",
)
