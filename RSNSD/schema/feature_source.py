"""
Origin of a dataset feature.

Tracks which module is responsible for generating or
extracting a particular feature.
"""

from enum import Enum


class FeatureSource(str, Enum):

    FLOW_EXTRACTOR = "flow_extractor"

    PACKET_PARSER = "packet_parser"

    TRAFFIC_GENERATOR = "traffic_generator"

    QOS_ESTIMATOR = "qos_estimator"

    CONTEXT_INJECTOR = "context_injector"

    LABELER = "labeler"

    MANUAL = "manual"