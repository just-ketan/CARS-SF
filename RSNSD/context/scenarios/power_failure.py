from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass

POWER_FAILURE = Scenario(
    name="Power Failure",
    description="Grid failure forces cell towers onto battery backup, reducing transmission power and capabilities.",
    network_load_range=(20.0, 60.0),
    cell_load_range=(30.0, 80.0),
    active_users_range=(50, 300),
    signal_strength_range=(-125.0, -105.0),
    sinr_range=(0.0, 6.0),
    rsrp_range=(-120.0, -100.0),
    rsrq_range=(-18.0, -12.0),
    cqi_range=(1, 5),
    resource_blocks_range=(20, 50),
    slice_utilization_range=(40.0, 70.0),
    preferred_services=[ServiceClass.GENERAL],
    service_bias_multiplier=1.2,
    handover_probability=0.10,
    daytime="night",
)
