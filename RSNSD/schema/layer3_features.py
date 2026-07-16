"""
Layer 3 (Network Layer) Feature Definitions

These features describe IP-layer properties of a network flow.
Only fields relevant to traffic characterization and QoS-aware
network slicing are included.
"""

from .feature import Feature
from .feature_groups import FeatureGroup
from .data_types import DataType
from .normalization import Normalization
from .ml_role import MLRole
from .feature_source import FeatureSource


LAYER3_FEATURES = [

    Feature(
        name="ip_version",
        description="Internet Protocol version",
        category=FeatureGroup.L3,
        datatype=DataType.CATEGORY,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="ttl",
        description="IPv4 Time-To-Live or IPv6 Hop Limit",
        category=FeatureGroup.L3,
        datatype=DataType.INTEGER,
        unit="hops",
        minimum=0,
        maximum=255,
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="dscp",
        description="Differentiated Services Code Point",
        category=FeatureGroup.L3,
        datatype=DataType.INTEGER,
        unit="",
        minimum=0,
        maximum=63,
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="ecn",
        description="Explicit Congestion Notification value",
        category=FeatureGroup.L3,
        datatype=DataType.INTEGER,
        unit="",
        minimum=0,
        maximum=3,
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="ip_packet_length",
        description="Total IP packet length",
        category=FeatureGroup.L3,
        datatype=DataType.INTEGER,
        unit="bytes",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="fragmented",
        description="Whether the packet is fragmented",
        category=FeatureGroup.L3,
        datatype=DataType.BOOLEAN,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="ip_header_length",
        description="Length of the IP header",
        category=FeatureGroup.L3,
        datatype=DataType.INTEGER,
        unit="bytes",
        minimum=20,
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="hop_limit",
        description="IPv6 Hop Limit (mirrors TTL for IPv6)",
        category=FeatureGroup.L3,
        datatype=DataType.INTEGER,
        unit="hops",
        minimum=0,
        maximum=255,
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

]