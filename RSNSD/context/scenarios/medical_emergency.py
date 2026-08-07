from RSNSD.context.scenario import Scenario
from RSNSD.domain.enums import ServiceClass

MEDICAL_EMERGENCY = Scenario(
    name="Medical Emergency",
    description="Localized medical emergency triggering immediate telemedicine and ambulance telemetry.",
    network_load_range=(40.0, 75.0),
    cell_load_range=(50.0, 85.0),
    active_users_range=(100, 400),
    signal_strength_range=(-100.0, -80.0),
    sinr_range=(10.0, 20.0),
    rsrp_range=(-95.0, -75.0),
    rsrq_range=(-10.0, -5.0),
    cqi_range=(8, 14),
    resource_blocks_range=(40, 80),
    slice_utilization_range=(50.0, 95.0),
    preferred_services=[ServiceClass.HEALTHCARE],
    service_bias_multiplier=5.0,
    handover_probability=0.30,
    daytime="day",
)
