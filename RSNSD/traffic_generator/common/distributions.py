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
    GAMMA = "gamma"
    WEIBULL = "weibull"
    PARETO = "pareto"
    DISCRETE_CHOICE = "discrete_choice"
    BERNOULLI = "bernoulli"
    CATEGORICAL = "categorical"
    TRIANGULAR = "triangular"
    BETA = "beta"
    CUSTOM = "custom"


from pydantic import BaseModel, Field, model_validator
from typing import Any, List

class Distribution(BaseModel):
    """
    Generic statistical distribution with robust parameter validation.
    """
    distribution: DistributionType
    
    # Common parameters
    mean: Optional[float] = None
    std: Optional[float] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    
    # Specific parameters
    rate: Optional[float] = None
    lambda_: Optional[float] = None
    sigma: Optional[float] = None
    value: Optional[Any] = None
    seed: Optional[int] = None
    
    # New parameters for Gamma, Weibull, Beta, etc.
    alpha: Optional[float] = None
    beta_param: Optional[float] = None
    shape: Optional[float] = None
    scale: Optional[float] = None
    choices: Optional[List[Any]] = None
    weights: Optional[List[float]] = None
    probability: Optional[float] = None
    mode: Optional[float] = None

    @model_validator(mode='after')
    def validate_parameters(self) -> 'Distribution':
        dist = self.distribution
        
        # Backward compatibility for exponential rate
        if dist == DistributionType.EXPONENTIAL and self.rate is not None and self.lambda_ is None:
            self.lambda_ = self.rate
            
        if dist == DistributionType.CONSTANT and self.value is None:
            raise ValueError("Constant distribution requires 'value'")
        elif dist == DistributionType.NORMAL and (self.mean is None or self.std is None):
            raise ValueError("Normal distribution requires 'mean' and 'std'")
        elif dist == DistributionType.UNIFORM and (self.minimum is None or self.maximum is None):
            raise ValueError("Uniform distribution requires 'minimum' and 'maximum'")
        elif dist in [DistributionType.EXPONENTIAL, DistributionType.POISSON] and self.lambda_ is None:
            raise ValueError(f"{dist.value} distribution requires 'lambda_'")
        elif dist == DistributionType.LOGNORMAL and (self.mean is None or self.sigma is None):
            raise ValueError("Lognormal distribution requires 'mean' and 'sigma'")
        elif dist == DistributionType.GAMMA and (self.shape is None or self.scale is None):
            raise ValueError("Gamma distribution requires 'shape' and 'scale'")
        elif dist == DistributionType.WEIBULL and (self.shape is None or self.scale is None):
            raise ValueError("Weibull distribution requires 'shape' and 'scale'")
        elif dist == DistributionType.PARETO and (self.shape is None):
            raise ValueError("Pareto distribution requires 'shape'")
        elif dist in [DistributionType.DISCRETE_CHOICE, DistributionType.CATEGORICAL] and self.choices is None:
            raise ValueError(f"{dist.value} distribution requires 'choices'")
        elif dist == DistributionType.BERNOULLI and self.probability is None:
            raise ValueError("Bernoulli distribution requires 'probability'")
        elif dist == DistributionType.TRIANGULAR and (self.minimum is None or self.maximum is None or self.mode is None):
            raise ValueError("Triangular distribution requires 'minimum', 'maximum', and 'mode'")
        elif dist == DistributionType.BETA and (self.alpha is None or self.beta_param is None):
            raise ValueError("Beta distribution requires 'alpha' and 'beta_param'")
            
        return self