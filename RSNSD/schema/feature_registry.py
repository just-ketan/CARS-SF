"""
Master Feature Registry

Every dataset feature must be registered here.

No other module should define dataset columns.
"""

from .flow_features import FLOW_FEATURES

# Upcoming feature groups
from .layer2_features import LAYER2_FEATURES
from .layer3_features import LAYER3_FEATURES
from .layer4_features import LAYER4_FEATURES

from .temporal_features import TEMPORAL_FEATURES
from .statistical_features import STATISTICAL_FEATURES

from .qos_features import QOS_FEATURES
from .context_features import CONTEXT_FEATURES

from .label_features import LABEL_FEATURES


FEATURES = (

    FLOW_FEATURES

    + LAYER2_FEATURES

    + LAYER3_FEATURES

    + LAYER4_FEATURES

    + TEMPORAL_FEATURES

    + STATISTICAL_FEATURES

    + QOS_FEATURES

    + CONTEXT_FEATURES

    + LABEL_FEATURES

)