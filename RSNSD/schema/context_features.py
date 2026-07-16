"""
Context Feature Definitions

These features describe the surrounding network, user, radio and
service environment in which a network flow exists.

Unlike packet or flow statistics, these features capture network
state and service context, making them essential for AI-driven
5G service-aware network slicing.
"""

from .feature import Feature
from .feature_groups import FeatureGroup
from .data_types import DataType
from .normalization import Normalization
from .ml_role import MLRole
from .feature_source import FeatureSource


CONTEXT_FEATURES = [

    # ==========================================================
    # Service Context
    # ==========================================================

    Feature(
        name="service_type",
        description="High-level service category",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.CATEGORY,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="application_name",
        description="Application generating the traffic",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.STRING,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="slice_type",
        description="Target network slice type",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.CATEGORY,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="service_priority",
        description="Priority assigned to the service",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.INTEGER,
        unit="level",
        minimum=1,
        maximum=4,
        normalization=Normalization.NONE,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    # ==========================================================
    # Network Context
    # ==========================================================

    Feature(
        name="network_load_pct",
        description="Overall network utilization",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.FLOAT,
        unit="%",
        minimum=0,
        maximum=100,
        normalization=Normalization.MINMAX,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="cell_load_pct",
        description="Serving cell utilization",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.FLOAT,
        unit="%",
        minimum=0,
        maximum=100,
        normalization=Normalization.MINMAX,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="active_users",
        description="Number of active users in the serving cell",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.INTEGER,
        unit="users",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    # ==========================================================
    # User Context
    # ==========================================================

    Feature(
        name="device_type",
        description="Type of user equipment",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.CATEGORY,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="mobility_state",
        description="Mobility state of the user",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.CATEGORY,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="time_of_day",
        description="Time period when the flow was generated",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.CATEGORY,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    # ==========================================================
    # Radio Context (5G Specific)
    # ==========================================================

    Feature(
        name="signal_strength_dbm",
        description="Average received signal strength",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.FLOAT,
        unit="dBm",
        normalization=Normalization.STANDARD,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="sinr_db",
        description="Signal-to-Interference-plus-Noise Ratio",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.FLOAT,
        unit="dB",
        normalization=Normalization.STANDARD,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="rsrp_dbm",
        description="Reference Signal Received Power",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.FLOAT,
        unit="dBm",
        normalization=Normalization.STANDARD,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="rsrq_db",
        description="Reference Signal Received Quality",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.FLOAT,
        unit="dB",
        normalization=Normalization.STANDARD,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="cqi",
        description="Channel Quality Indicator",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.INTEGER,
        unit="index",
        minimum=1,
        maximum=15,
        normalization=Normalization.NONE,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    # ==========================================================
    # Slice Context (Novel Contribution)
    # ==========================================================

    Feature(
        name="network_slice_id",
        description="Identifier of the serving network slice",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.CATEGORY,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="slice_resource_utilization_pct",
        description="Percentage of slice resources currently utilized",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.FLOAT,
        unit="%",
        minimum=0,
        maximum=100,
        normalization=Normalization.MINMAX,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="radio_resource_blocks_used",
        description="Allocated Physical Resource Blocks",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.INTEGER,
        unit="PRBs",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="handover_in_progress",
        description="Whether the UE is undergoing handover",
        category=FeatureGroup.CONTEXT,
        datatype=DataType.BOOLEAN,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.CONTEXT_INJECTOR,
        ml_role=MLRole.FEATURE,
    ),

]