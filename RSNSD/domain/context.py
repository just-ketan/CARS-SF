"""
Context Domain Model

Represents the network context associated with a generated flow.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class ContextRecord:

    # ==========================================================
    # Service Context
    # ==========================================================

    service_type: str

    application_name: str

    slice_type: str

    service_priority: int

    # ==========================================================
    # Network Context
    # ==========================================================

    network_load_pct: float

    cell_load_pct: float

    active_users: int

    # ==========================================================
    # User Context
    # ==========================================================

    device_type: str

    mobility_state: str

    time_of_day: str

    # ==========================================================
    # Radio Context
    # ==========================================================

    signal_strength_dbm: float

    sinr_db: float

    rsrp_dbm: float

    rsrq_db: float

    cqi: int

    # ==========================================================
    # Slice Context
    # ==========================================================

    network_slice_id: str

    slice_resource_utilization_pct: float

    radio_resource_blocks_used: int

    handover_in_progress: bool