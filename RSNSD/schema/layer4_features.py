"""
Transport Layer (Layer 4) Feature Definitions

These features describe transport-layer behaviour
and protocol characteristics of each network flow.
"""

from .feature import Feature
from .feature_groups import FeatureGroup
from .data_types import DataType
from .normalization import Normalization
from .ml_role import MLRole
from .feature_source import FeatureSource


LAYER4_FEATURES = [

    Feature(
        name="transport_protocol",
        description="Transport layer protocol used by the flow",
        category=FeatureGroup.L4,
        datatype=DataType.STRING,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="source_port",
        description="Source transport layer port",
        category=FeatureGroup.L4,
        datatype=DataType.INTEGER,
        unit="",
        minimum=0,
        maximum=65535,
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="destination_port",
        description="Destination transport layer port",
        category=FeatureGroup.L4,
        datatype=DataType.INTEGER,
        unit="",
        minimum=0,
        maximum=65535,
        normalization=Normalization.NONE,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="tcp_syn_count",
        description="Number of TCP SYN packets",
        category=FeatureGroup.L4,
        datatype=DataType.INTEGER,
        unit="packets",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="tcp_ack_count",
        description="Number of TCP ACK packets",
        category=FeatureGroup.L4,
        datatype=DataType.INTEGER,
        unit="packets",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="tcp_fin_count",
        description="Number of TCP FIN packets",
        category=FeatureGroup.L4,
        datatype=DataType.INTEGER,
        unit="packets",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="tcp_rst_count",
        description="Number of TCP RST packets",
        category=FeatureGroup.L4,
        datatype=DataType.INTEGER,
        unit="packets",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="tcp_window_size",
        description="Average TCP receive window size",
        category=FeatureGroup.L4,
        datatype=DataType.INTEGER,
        unit="bytes",
        minimum=0,
        normalization=Normalization.STANDARD,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="tcp_retransmissions",
        description="Number of retransmitted TCP packets",
        category=FeatureGroup.L4,
        datatype=DataType.INTEGER,
        unit="packets",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

    Feature(
        name="udp_packet_count",
        description="Number of UDP packets",
        category=FeatureGroup.L4,
        datatype=DataType.INTEGER,
        unit="packets",
        minimum=0,
        normalization=Normalization.LOG,
        source=FeatureSource.PACKET_PARSER,
        ml_role=MLRole.FEATURE,
    ),

]