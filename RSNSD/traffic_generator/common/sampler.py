"""
Traffic Distribution Sampler

Provides sampling utilities for all supported probability
distributions used in traffic generation.
"""

import numpy as np
import random

from .distributions import Distribution, DistributionType

class Sampler:
    def __init__(self, seed: int | None = None):
        self.random = random.Random(seed)
        self.np_random = np.random.default_rng(seed)

    def sample(self, distribution: Distribution):
        dist = distribution.distribution
        
        if dist == DistributionType.CONSTANT:
            return distribution.value
        elif dist == DistributionType.NORMAL:
            return max(0, self.random.gauss(distribution.mean, distribution.std))
        elif dist == DistributionType.UNIFORM:
            return self.random.uniform(distribution.minimum, distribution.maximum)
        elif dist == DistributionType.EXPONENTIAL:
            # Note: numpy exponential takes scale = 1/lambda
            return self.np_random.exponential(1.0 / distribution.lambda_)
        elif dist == DistributionType.POISSON:
            return self.np_random.poisson(distribution.lambda_)
        elif dist == DistributionType.LOGNORMAL:
            return self.np_random.lognormal(distribution.mean, distribution.sigma)
        elif dist == DistributionType.GAMMA:
            return self.np_random.gamma(distribution.shape, distribution.scale)
        elif dist == DistributionType.WEIBULL:
            # numpy weibull takes shape 'a'. To scale it, multiply by scale 'lambda'
            return distribution.scale * self.np_random.weibull(distribution.shape)
        elif dist == DistributionType.PARETO:
            return self.np_random.pareto(distribution.shape)
        elif dist in [DistributionType.DISCRETE_CHOICE, DistributionType.CATEGORICAL]:
            weights = distribution.weights
            if weights is not None:
                weights = np.array(weights) / np.sum(weights)
            return self.np_random.choice(distribution.choices, p=weights)
        elif dist == DistributionType.BERNOULLI:
            return self.np_random.binomial(1, distribution.probability)
        elif dist == DistributionType.TRIANGULAR:
            return self.np_random.triangular(distribution.minimum, distribution.mode, distribution.maximum)
        elif dist == DistributionType.BETA:
            return self.np_random.beta(distribution.alpha, distribution.beta_param)
        else:
            raise ValueError(f"Unsupported distribution: {dist}")