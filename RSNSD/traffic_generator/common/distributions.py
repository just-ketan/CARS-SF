"""
Traffic Distribution Models

Defines probability distributions used to generate realistic
network traffic characteristics.

These distribution definitions are later sampled by the traffic
generator to create unique traffic flows.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DistributionType(str, Enum):
    """Supported probability distributions."""

    CONSTANT = "constant"

    NORMAL = "normal"

    UNIFORM = "uniform"

    EXPONENTIAL = "exponential"

    POISSON = "poisson"

    LOGNORMAL = "lognormal"


@dataclass(slots=True, frozen=True)
class Distribution:
    """
    Generic statistical distribution.

    The traffic generator interprets these parameters and performs
    the actual sampling.
    """

    distribution: DistributionType

    # Common parameters
    mean: Optional[float] = None
    std: Optional[float] = None

    minimum: Optional[float] = None
    maximum: Optional[float] = None

    rate: Optional[float] = None

    lambda_: Optional[float] = None

    sigma: Optional[float] = None

    value: Optional[float] = None

    seed: Optional[int] = None