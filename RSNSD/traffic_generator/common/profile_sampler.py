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

    ):

        adjusted_weights = []

        for profile, weight in zip(profiles, weights):

            if profile.service_class in scenario.preferred_services:

                weight *= scenario.service_bias_multiplier

            adjusted_weights.append(weight)

        return self.random.choices(

            profiles,

            weights=adjusted_weights,

            k=1,

        )[0]