"""
Statistical Feature Definitions

These features summarize the statistical properties of packet sizes
within a network flow.
"""

from .feature import Feature
from .feature_groups import FeatureGroup
from .data_types import DataType
from .normalization import Normalization
from .ml_role import MLRole
from .feature_source import FeatureSource


STATISTICAL_FEATURES = [

    Feature(
        name="mean_packet_size",
        description="Average packet size within the flow",
        category=FeatureGroup.STATISTICAL,
        datatype=DataType.FLOAT,
        unit="bytes",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="median_packet_size",
        description="Median packet size within the flow",
        category=FeatureGroup.STATISTICAL,
        datatype=DataType.FLOAT,
        unit="bytes",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="min_packet_size",
        description="Minimum packet size observed in the flow",
        category=FeatureGroup.STATISTICAL,
        datatype=DataType.INTEGER,
        unit="bytes",
        minimum=0,
        normalization=Normalization.NONE,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="max_packet_size",
        description="Maximum packet size observed in the flow",
        category=FeatureGroup.STATISTICAL,
        datatype=DataType.INTEGER,
        unit="bytes",
        minimum=0,
        normalization=Normalization.NONE,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="std_packet_size",
        description="Standard deviation of packet sizes",
        category=FeatureGroup.STATISTICAL,
        datatype=DataType.FLOAT,
        unit="bytes",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="variance_packet_size",
        description="Variance of packet sizes",
        category=FeatureGroup.STATISTICAL,
        datatype=DataType.FLOAT,
        unit="bytes²",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="packet_size_range",
        description="Difference between maximum and minimum packet sizes",
        category=FeatureGroup.STATISTICAL,
        datatype=DataType.INTEGER,
        unit="bytes",
        minimum=0,
        normalization=Normalization.NONE,
        source=FeatureSource.FLOW_EXTRACTOR,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="packet_size_skewness",
        description="Skewness of packet size distribution",
        category=FeatureGroup.STATISTICAL,
        datatype=DataType.FLOAT,
        unit="",
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        derived=True,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="packet_size_kurtosis",
        description="Kurtosis of packet size distribution",
        category=FeatureGroup.STATISTICAL,
        datatype=DataType.FLOAT,
        unit="",
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        derived=True,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="coefficient_of_variation_packet_size",
        description="Coefficient of variation of packet sizes",
        category=FeatureGroup.STATISTICAL,
        datatype=DataType.FLOAT,
        unit="",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.FLOW_EXTRACTOR,
        derived=True,
        ml_role=MLRole.FEATURE,
    ),

]