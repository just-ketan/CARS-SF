"""
Traffic Distribution Sampler

Provides sampling utilities for all supported probability
distributions used in traffic generation.
"""

import random

from .distributions import Distribution, DistributionType


class Sampler:

    def __init__(self, seed: int | None = None):

        self.random = random.Random(seed)

    def sample(self, distribution: Distribution):

        match distribution.distribution:

            case DistributionType.CONSTANT:

                return distribution.value

            case DistributionType.NORMAL:

                return max(
                    0,
                    self.random.gauss(
                        distribution.mean,
                        distribution.std,
                    ),
                )

            case DistributionType.UNIFORM:

                return self.random.uniform(
                    distribution.minimum,
                    distribution.maximum,
                )

            case DistributionType.EXPONENTIAL:

                return self.random.expovariate(
                    distribution.rate,
                )

            case DistributionType.POISSON:

                # Simple approximation using exponential arrivals.
                # We will replace this with NumPy later.
                return round(
                    self.random.expovariate(
                        1 / distribution.lambda_
                    )
                )

            case DistributionType.LOGNORMAL:

                return self.random.lognormvariate(
                    distribution.mean,
                    distribution.sigma,
                )

            case _:

                raise ValueError(
                    f"Unsupported distribution: {distribution.distribution}"
                )