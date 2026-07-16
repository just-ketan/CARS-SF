"""
Core Flow Feature Definitions

These are the fundamental attributes extracted from every
network flow before higher-level feature engineering.

Author: RSNSD
"""

from .feature import Feature
from .feature_groups import FeatureGroup
from .data_types import DataType
from .normalization import Normalization
from .ml_role import MLRole
from .feature_source import FeatureSource

FLOW_FEATURES = [

    Feature(
        name="flow_id",
        description="Unique identifier of the network flow",
        category=FeatureGroup.FLOW,
        datatype=DataType.STRING,
        unit="",
        nullable=False,
        normalization=Normalization.NONE,
        source=FeatureSource.FLOW_EXTRACTOR,
        required=True,
        derived=False,
        ml_role=MLRole.METADATA,
    ),

    Feature(
        name="flow_duration_ms",
        description="Total duration of the network flow",
        category=FeatureGroup.FLOW,
        datatype=DataType.FLOAT,
        unit="ms",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        required=True,
        derived=False,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="packet_count",
        description="Total number of packets in the flow",
        category=FeatureGroup.FLOW,
        datatype=DataType.INTEGER,
        unit="packets",
        minimum=1,
        normalization=Normalization.LOG,
        source=FeatureSource.FLOW_EXTRACTOR,
        required=True,
        derived=False,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="byte_count",
        description="Total bytes transferred",
        category=FeatureGroup.FLOW,
        datatype=DataType.INTEGER,
        unit="bytes",
        minimum=1,
        normalization=Normalization.LOG,
        source=FeatureSource.FLOW_EXTRACTOR,
        required=True,
        derived=False,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="forward_packet_count",
        description="Packets sent from source to destination",
        category=FeatureGroup.FLOW,
        datatype=DataType.INTEGER,
        unit="packets",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.FLOW_EXTRACTOR,
        required=True,
        derived=False,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="backward_packet_count",
        description="Packets sent from destination to source",
        category=FeatureGroup.FLOW,
        datatype=DataType.INTEGER,
        unit="packets",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.FLOW_EXTRACTOR,
        required=True,
        derived=False,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="forward_byte_count",
        description="Bytes transferred from source to destination",
        category=FeatureGroup.FLOW,
        datatype=DataType.INTEGER,
        unit="bytes",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.FLOW_EXTRACTOR,
        required=True,
        derived=False,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="backward_byte_count",
        description="Bytes transferred from destination to source",
        category=FeatureGroup.FLOW,
        datatype=DataType.INTEGER,
        unit="bytes",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.FLOW_EXTRACTOR,
        required=True,
        derived=False,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="packet_rate_pps",
        description="Packets transmitted per second",
        category=FeatureGroup.FLOW,
        datatype=DataType.FLOAT,
        unit="packets/sec",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        required=True,
        derived=False,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="byte_rate_bps",
        description="Bytes transmitted per second",
        category=FeatureGroup.FLOW,
        datatype=DataType.FLOAT,
        unit="bytes/sec",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        required=True,
        derived=False,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="flow_start_time",
        description="Timestamp when the flow started",
        category=FeatureGroup.FLOW,
        datatype=DataType.DATETIME,
        unit="UTC",
        normalization=Normalization.NONE,
        source=FeatureSource.FLOW_EXTRACTOR,
        required=True,
        derived=False,
        ml_role=MLRole.METADATA,
    ),

    Feature(
        name="flow_end_time",
        description="Timestamp when the flow ended",
        category=FeatureGroup.FLOW,
        datatype=DataType.DATETIME,
        unit="UTC",
        normalization=Normalization.NONE,
        source=FeatureSource.FLOW_EXTRACTOR,
        required=True,
        derived=False,
        ml_role=MLRole.METADATA,
    ),

]