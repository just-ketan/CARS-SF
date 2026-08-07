"""
Scenario-aware Application Profile Sampler

Selects application profiles based on both the base
application weights and the current rural scenario.
"""

import random


class ProfileSampler:

    def __init__(self, seed=None):

        self.random = random.Random(seed)

    def sample(
        self,
        profiles,
        weights,
        scenario,
        clock=None,
    ):

        adjusted_weights = []

        for profile, weight in zip(profiles, weights):

            if profile.service_class in scenario.preferred_services:
                weight *= scenario.service_bias_multiplier

            if clock:
                from RSNSD.domain.enums import ServiceClass
                if clock.is_night:
                    if profile.service_class in (ServiceClass.EDUCATION, ServiceClass.AGRICULTURE):
                        weight *= 0.1
                elif clock.is_school_hours:
                    if profile.service_class == ServiceClass.EDUCATION:
                        weight *= 2.0

            adjusted_weights.append(weight)

        return self.random.choices(

            profiles,

            weights=adjusted_weights,

            k=1,

        )[0]