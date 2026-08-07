"""
Validation Report

Aggregates all validation results into a single object.
"""

from dataclasses import dataclass

from RSNSD.validator.correlations import CorrelationResult
from RSNSD.validator.distributions import DistributionResult
from RSNSD.validator.outliers import OutlierSummary
from RSNSD.validator.qos_checks import QoSValidationResult
from RSNSD.validator.schema_checks import SchemaValidationResult
from RSNSD.validator.statistics import DatasetStatistics


@dataclass(slots=True)
class ValidationReport:

    statistics: DatasetStatistics

    schema: SchemaValidationResult

    distributions: DistributionResult

    correlations: list[CorrelationResult]

    qos: QoSValidationResult

    outliers: list[OutlierSummary]

    schema_score: float

    qos_score: float

    correlation_score: float

    distribution_score: float

    outlier_score: float

    score: float

    passed: bool

    recommendations: list[str]