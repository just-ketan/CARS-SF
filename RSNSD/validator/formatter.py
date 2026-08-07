from __future__ import annotations

from RSNSD.validator.report import ValidationReport
from RSNSD.validator.correlations import CorrelationResult
from RSNSD.validator.distributions import DistributionResult
from RSNSD.validator.outliers import OutlierSummary
from RSNSD.validator.qos_checks import QoSValidationResult
from RSNSD.validator.schema_checks import SchemaValidationResult
from RSNSD.validator.statistics import DatasetStatistics

class ValidationFormatter:

    def print_report(
        self,
        report: ValidationReport,
    ):

        self.print_header(report)

        self.print_statistics(report.statistics)

        self.print_schema(report.schema)

        self.print_distribution(report.distributions)

        self.print_correlations(report.correlations)

        self.print_qos(report.qos)

        self.print_outliers(report.outliers)

        self.print_recommendations(report.recommendations)

        self.print_footer(report)