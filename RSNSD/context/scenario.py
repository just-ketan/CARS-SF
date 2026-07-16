"""
Scenario Model

Represents a rural operating scenario that influences
network conditions and application behaviour.
"""

from dataclasses import dataclass

from RSNSD.domain.enums import ServiceClass


@dataclass(slots=True)
class Scenario:
    """
    Defines a complete rural network context.
    """

    # ======================================================
    # Identity
    # ======================================================

    name: str

    description: str

    # ======================================================
    # Network Conditions
    # ======================================================

    network_load_range: tuple[float, float]

    cell_load_range: tuple[float, float]

    active_users_range: tuple[int, int]

    signal_strength_range: tuple[float, float]

    sinr_range: tuple[float, float]

    rsrp_range: tuple[float, float]

    rsrq_range: tuple[float, float]

    # ======================================================
    # Radio
    # ======================================================

    cqi_range: tuple[int, int]

    resource_blocks_range: tuple[int, int]

    slice_utilization_range: tuple[float, float]

    # ======================================================
    # Service Bias
    # ======================================================

    preferred_services: list[ServiceClass]
    service_bias_multiplier: float

    # ======================================================
    # Misc
    # ======================================================

    handover_probability: float

    daytime: str