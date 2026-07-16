"""
Core feature definition for RSNSD.
"""

from dataclasses import dataclass
from typing import Optional

from .data_types import DataType
from .feature_groups import FeatureGroup
from .ml_role import MLRole
from .normalization import Normalization
from .feature_source import FeatureSource

@dataclass(slots=True)
class Feature:
    """
    Metadata describing one dataset column.
    """

    # Basic Information
    name: str
    description: str

    # Organization
    category: FeatureGroup

    # Data Definition
    datatype: DataType
    unit: str

    # Value Constraints
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    nullable: bool = False

    # Processing
    normalization: Normalization = Normalization.NONE

    # Dataset Metadata
    source: FeatureSource = FeatureSource.MANUAL

    required: bool = True

    derived: bool = False

    # ML
    ml_role: MLRole = MLRole.FEATURE