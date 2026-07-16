"""
Layer 2 (Data Link Layer) Feature Definitions

These features describe Ethernet-level characteristics of a network
flow. Only features relevant to SDN, OpenFlow and future network
extensions are included.
"""

from .feature import Feature
from .feature_groups import FeatureGroup
from .data_types import DataType
from .normalization import Normalization
from .ml_role import MLRole
from .feature_source import FeatureSource


LAYER2_FEATURES = [

    Feature(
        name="ether_type",
        description="Ethernet frame type",
        category=FeatureGroup.L2,
        datatype=DataType.CATEGORY,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="vlan_present",
        description="Whether the Ethernet frame contains a VLAN tag",
        category=FeatureGroup.L2,
        datatype=DataType.BOOLEAN,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="vlan_priority",
        description="IEEE 802.1p VLAN priority value",
        category=FeatureGroup.L2,
        datatype=DataType.INTEGER,
        unit="priority",
        minimum=0,
        maximum=7,
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="broadcast_frame",
        description="Whether the frame is broadcast",
        category=FeatureGroup.L2,
        datatype=DataType.BOOLEAN,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="multicast_frame",
        description="Whether the frame is multicast",
        category=FeatureGroup.L2,
        datatype=DataType.BOOLEAN,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

]