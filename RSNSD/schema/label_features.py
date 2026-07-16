"""
Label Feature Definitions

These columns represent the ground-truth outputs of the dataset.

They are NOT input features and should never be used as model inputs.
Instead, they act as supervision targets for classification models
and reference decisions for reinforcement learning.
"""

from .feature import Feature
from .feature_groups import FeatureGroup
from .data_types import DataType
from .normalization import Normalization
from .ml_role import MLRole
from .feature_source import FeatureSource


LABEL_FEATURES = [

    # ==========================================================
    # Supervised Learning Labels
    # ==========================================================

    Feature(
        name="service_class",
        description="Ground truth service class",
        category=FeatureGroup.LABEL,
        datatype=DataType.CATEGORY,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.LABELER,
        ml_role=MLRole.LABEL,
    ),

    Feature(
        name="application_id",
        description="Application responsible for generating the flow",
        category=FeatureGroup.LABEL,
        datatype=DataType.CATEGORY,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.LABELER,
        ml_role=MLRole.LABEL,
    ),

    Feature(
        name="slice_type_label",
        description="Ground truth slice type",
        category=FeatureGroup.LABEL,
        datatype=DataType.CATEGORY,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.LABELER,
        ml_role=MLRole.LABEL,
    ),

    Feature(
        name="priority_level",
        description="Ground truth service priority",
        category=FeatureGroup.LABEL,
        datatype=DataType.INTEGER,
        unit="level",
        minimum=1,
        maximum=4,
        normalization=Normalization.NONE,
        source=FeatureSource.LABELER,
        ml_role=MLRole.LABEL,
    ),

    # ==========================================================
    # RL / Scheduling Reference Labels
    # ==========================================================

    Feature(
        name="allocated_slice",
        description="Slice allocated by the scheduling policy",
        category=FeatureGroup.LABEL,
        datatype=DataType.CATEGORY,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.LABELER,
        derived=True,
        ml_role=MLRole.LABEL,
    ),

    Feature(
        name="sla_satisfied",
        description="Whether the flow met its SLA requirements",
        category=FeatureGroup.LABEL,
        datatype=DataType.BOOLEAN,
        unit="",
        normalization=Normalization.NONE,
        source=FeatureSource.LABELER,
        derived=True,
        ml_role=MLRole.LABEL,
    ),

    Feature(
        name="reward_score",
        description="Reward assigned to the scheduling decision",
        category=FeatureGroup.LABEL,
        datatype=DataType.FLOAT,
        unit="score",
        normalization=Normalization.NONE,
        source=FeatureSource.LABELER,
        derived=True,
        ml_role=MLRole.LABEL,
    ),

]