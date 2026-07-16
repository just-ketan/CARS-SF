"""
Machine Learning role of a dataset column.
"""

from enum import Enum


class MLRole(str, Enum):

    FEATURE = "feature"

    LABEL = "label"

    METADATA = "metadata"