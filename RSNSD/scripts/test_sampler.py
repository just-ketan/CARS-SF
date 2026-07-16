from RSNSD.traffic_generator.common.sampler import Sampler
from RSNSD.traffic_generator.common.distributions import (
    Distribution,
    DistributionType,
)

sampler = Sampler(seed=42)

dist = Distribution(
    distribution=DistributionType.NORMAL,
    mean=1200,
    std=100,
)

for _ in range(10):
    print(sampler.sample(dist))