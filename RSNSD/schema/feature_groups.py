"""
Feature group definitions used throughout RSNSD.
"""

from enum import Enum


class FeatureGroup(str, Enum):

    L2 = "layer2"
    L3 = "layer3"
    L4 = "layer4"

    FLOW = "flow"

    TEMPORAL = "temporal"

    STATISTICAL = "statistical"

    QOS = "qos"

    CONTEXT = "context"

    LABEL = "label"