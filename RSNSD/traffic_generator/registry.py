"""
Global Application Registry

Author: RSNSD
"""

from RSNSD.traffic_generator.domain_registry import DOMAIN_WEIGHTS

from RSNSD.traffic_generator.healthcare import (
    HEALTHCARE_PROFILE_REGISTRY,
    HEALTHCARE_PROFILE_WEIGHTS,
)

from RSNSD.traffic_generator.education import (
    EDUCATION_PROFILE_REGISTRY,
    EDUCATION_PROFILE_WEIGHTS,
)

from RSNSD.traffic_generator.agriculture import (
    AGRICULTURE_PROFILE_REGISTRY,
    AGRICULTURE_PROFILE_WEIGHTS,
)

from RSNSD.traffic_generator.general import (
    GENERAL_PROFILE_REGISTRY,
    GENERAL_PROFILE_WEIGHTS,
)

DOMAIN_REGISTRIES = {

    "healthcare": (
        HEALTHCARE_PROFILE_REGISTRY,
        HEALTHCARE_PROFILE_WEIGHTS,
    ),

    "education": (
        EDUCATION_PROFILE_REGISTRY,
        EDUCATION_PROFILE_WEIGHTS,
    ),

    "agriculture": (
        AGRICULTURE_PROFILE_REGISTRY,
        AGRICULTURE_PROFILE_WEIGHTS,
    ),

    "general": (
        GENERAL_PROFILE_REGISTRY,
        GENERAL_PROFILE_WEIGHTS,
    ),

}

ALL_PROFILES = []

ALL_WEIGHTS = []

for domain, (profiles, weights) in DOMAIN_REGISTRIES.items():

    domain_weight = DOMAIN_WEIGHTS[domain]

    ALL_PROFILES.extend(profiles)

    ALL_WEIGHTS.extend(

        w * domain_weight

        for w in weights

    )