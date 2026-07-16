"""
Network Scenarios

Defines realistic operating conditions under which traffic
is generated.
"""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Scenario:

    name: str

    network_load_min: float
    network_load_max: float

    active_users_min: int
    active_users_max: int

    cqi_min: int
    cqi_max: int

    rsrp_min: float
    rsrp_max: float

    slice_utilization_min: float
    slice_utilization_max: float


NORMAL = Scenario(

    name="Normal",

    network_load_min=30,
    network_load_max=55,

    active_users_min=40,
    active_users_max=90,

    cqi_min=11,
    cqi_max=15,

    rsrp_min=-90,
    rsrp_max=-70,

    slice_utilization_min=25,
    slice_utilization_max=55,
)


SCHOOL_HOURS = Scenario(

    name="School Hours",

    network_load_min=65,
    network_load_max=90,

    active_users_min=200,
    active_users_max=450,

    cqi_min=9,
    cqi_max=13,

    rsrp_min=-95,
    rsrp_max=-75,

    slice_utilization_min=60,
    slice_utilization_max=90,
)


HARVEST = Scenario(

    name="Harvest",

    network_load_min=45,
    network_load_max=70,

    active_users_min=80,
    active_users_max=180,

    cqi_min=10,
    cqi_max=14,

    rsrp_min=-92,
    rsrp_max=-72,

    slice_utilization_min=40,
    slice_utilization_max=70,
)


DISASTER = Scenario(

    name="Disaster",

    network_load_min=80,
    network_load_max=100,

    active_users_min=300,
    active_users_max=700,

    cqi_min=5,
    cqi_max=11,

    rsrp_min=-110,
    rsrp_max=-90,

    slice_utilization_min=80,
    slice_utilization_max=100,
)