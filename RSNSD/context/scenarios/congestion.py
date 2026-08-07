from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass

CONGESTION = Scenario(
    name="Congestion",
    description="Generic massive surge in traffic causing buffers to bloat and packet drops.",
    network_load_range=(90.0, 100.0),
    cell_load_range=(85.0, 100.0),
    active_users_range=(1000, 3000),
    signal_strength_range=(-115.0, -90.0),
    sinr_range=(2.0, 8.0),
    rsrp_range=(-110.0, -90.0),
    rsrq_range=(-16.0, -10.0),
    cqi_range=(3, 9),
    resource_blocks_range=(90, 100),
    slice_utilization_range=(95.0, 100.0),
    preferred_services=[ServiceClass.GENERAL, ServiceClass.EDUCATION],
    service_bias_multiplier=1.5,
    handover_probability=0.25,
    daytime="day",
)
