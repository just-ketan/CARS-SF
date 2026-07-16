"""
Supported normalization strategies for RSNSD features.
"""

from enum import Enum


class Normalization(str, Enum):

    NONE = "none"

    STANDARD = "standard"

    MINMAX = "minmax"

    LOG = "log"

    ROBUST = "robust"