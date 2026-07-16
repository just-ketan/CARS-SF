"""
Temporal Feature Definitions

These features characterize the timing behaviour of a network flow.
They are among the most important features for distinguishing
different service classes.
"""

from .feature import Feature
from .feature_groups import FeatureGroup
from .data_types import DataType
from .normalization import Normalization
from .ml_role import MLRole
from .feature_source import FeatureSource


TEMPORAL_FEATURES = [

    Feature(
        name="mean_iat_ms",
        description="Mean inter-arrival time between packets",
        category=FeatureGroup.TEMPORAL,
        datatype=DataType.FLOAT,
        unit="ms",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="std_iat_ms",
        description="Standard deviation of packet inter-arrival time",
        category=FeatureGroup.TEMPORAL,
        datatype=DataType.FLOAT,
        unit="ms",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="min_iat_ms",
        description="Minimum packet inter-arrival time",
        category=FeatureGroup.TEMPORAL,
        datatype=DataType.FLOAT,
        unit="ms",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="max_iat_ms",
        description="Maximum packet inter-arrival time",
        category=FeatureGroup.TEMPORAL,
        datatype=DataType.FLOAT,
        unit="ms",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="forward_mean_iat_ms",
        description="Mean forward-direction inter-arrival time",
        category=FeatureGroup.TEMPORAL,
        datatype=DataType.FLOAT,
        unit="ms",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="backward_mean_iat_ms",
        description="Mean backward-direction inter-arrival time",
        category=FeatureGroup.TEMPORAL,
        datatype=DataType.FLOAT,
        unit="ms",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="flow_active_time_ms",
        description="Total active transmission time",
        category=FeatureGroup.TEMPORAL,
        datatype=DataType.FLOAT,
        unit="ms",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="flow_idle_time_ms",
        description="Total idle time during the flow",
        category=FeatureGroup.TEMPORAL,
        datatype=DataType.FLOAT,
        unit="ms",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

]