"""
Quality of Service (QoS) Feature Definitions

These features characterize the quality experienced by a network
flow and are fundamental to service-aware network slicing.
"""

from .feature import Feature
from .feature_groups import FeatureGroup
from .data_types import DataType
from .normalization import Normalization
from .ml_role import MLRole
from .feature_source import FeatureSource


QOS_FEATURES = [

    Feature(
        name="end_to_end_latency_ms",
        description="Average end-to-end latency experienced by the flow",
        category=FeatureGroup.QOS,
        datatype=DataType.FLOAT,
        unit="ms",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.QOS_ESTIMATOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="jitter_ms",
        description="Variation in packet arrival time",
        category=FeatureGroup.QOS,
        datatype=DataType.FLOAT,
        unit="ms",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.QOS_ESTIMATOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="packet_loss_rate",
        description="Percentage of packets lost during transmission",
        category=FeatureGroup.QOS,
        datatype=DataType.FLOAT,
        unit="%",
        minimum=0,
        maximum=100,
        normalization=Normalization.MINMAX,
        source=FeatureSource.QOS_ESTIMATOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="throughput_mbps",
        description="Average throughput achieved by the flow",
        category=FeatureGroup.QOS,
        datatype=DataType.FLOAT,
        unit="Mbps",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.QOS_ESTIMATOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="goodput_mbps",
        description="Application-level useful throughput excluding retransmissions",
        category=FeatureGroup.QOS,
        datatype=DataType.FLOAT,
        unit="Mbps",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.QOS_ESTIMATOR,
        derived=True,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="bandwidth_utilization_pct",
        description="Percentage of allocated bandwidth utilized",
        category=FeatureGroup.QOS,
        datatype=DataType.FLOAT,
        unit="%",
        minimum=0,
        maximum=100,
        normalization=Normalization.MINMAX,
        source=FeatureSource.QOS_ESTIMATOR,
        derived=True,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="queueing_delay_ms",
        description="Average queueing delay experienced by packets",
        category=FeatureGroup.QOS,
        datatype=DataType.FLOAT,
        unit="ms",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.QOS_ESTIMATOR,
        derived=True,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="retransmission_rate",
        description="Percentage of retransmitted packets",
        category=FeatureGroup.QOS,
        datatype=DataType.FLOAT,
        unit="%",
        minimum=0,
        maximum=100,
        normalization=Normalization.MINMAX,
        source=FeatureSource.QOS_ESTIMATOR,
        derived=True,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="link_utilization_pct",
        description="Percentage utilization of the serving link",
        category=FeatureGroup.QOS,
        datatype=DataType.FLOAT,
        unit="%",
        minimum=0,
        maximum=100,
        normalization=Normalization.MINMAX,
        source=FeatureSource.QOS_ESTIMATOR,
        derived=True,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="qos_satisfaction_score",
        description="Composite QoS score derived from latency, jitter, packet loss and throughput",
        category=FeatureGroup.QOS,
        datatype=DataType.FLOAT,
        unit="score",
        minimum=0,
        maximum=1,
        normalization=Normalization.NONE,
        source=FeatureSource.QOS_ESTIMATOR,
        derived=True,
        ml_role=MLRole.FEATURE,
    ),

]