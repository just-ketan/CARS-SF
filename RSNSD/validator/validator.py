"""
RSNSD Dataset Validator

Main orchestration class for validating generated datasets.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from RSNSD.schema.feature_registry import FEATURES

from RSNSD.validator.statistics import StatisticsAnalyzer
from RSNSD.validator.schema_checks import SchemaValidator
from RSNSD.validator.distributions import DistributionAnalyzer
from RSNSD.validator.correlations import CorrelationAnalyzer
from RSNSD.validator.qos_checks import QoSValidator
from RSNSD.validator.outliers import OutlierAnalyzer
from RSNSD.validator.report import ValidationReport


class DatasetValidator:

    def __init__(self):

        self.statistics_analyzer = StatisticsAnalyzer()

        self.schema_validator = SchemaValidator(
            expected_columns=[
                feature.name
                for feature in FEATURES
            ],
            required_columns=[
                feature.name
                for feature in FEATURES
                if feature.required
            ],
        )

        self.distribution_analyzer = DistributionAnalyzer()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.qos_validator = QoSValidator()
        self.outlier_analyzer = OutlierAnalyzer()

    def validate(
        self,
        dataset_path: str | Path,
    ) -> ValidationReport:

        dataset_path = Path(dataset_path)

        if not dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {dataset_path}"
            )

        dataframe = pd.read_csv(dataset_path)

        statistics = self.statistics_analyzer.analyze(dataframe)

        schema = self.schema_validator.validate(dataframe)

        distributions = self.distribution_analyzer.analyze(dataframe)

        correlations = self.correlation_analyzer.analyze(dataframe)

        qos = self.qos_validator.validate(dataframe)

        outliers = self.outlier_analyzer.analyze(dataframe)

        schema_score = self._compute_schema_score(schema)

        qos_score = self._compute_qos_score(qos)

        correlation_score = self._compute_correlation_score(
            correlations
        )

        distribution_score = self._compute_distribution_score(
            distributions
        )

        outlier_score = self._compute_outlier_score(
            outliers,
            statistics.rows,
        )

        total_score = round(
            schema_score
            + qos_score
            + correlation_score
            + distribution_score
            + outlier_score,
            2,
        )

        recommendations = self._generate_recommendations(
            schema,
            qos,
            correlations,
            outliers,
        )

        return ValidationReport(
            statistics=statistics,
            schema=schema,
            distributions=distributions,
            correlations=correlations,
            qos=qos,
            outliers=outliers,

            schema_score=schema_score,
            qos_score=qos_score,
            correlation_score=correlation_score,
            distribution_score=distribution_score,
            outlier_score=outlier_score,

            score=total_score,
            passed=total_score >= 85,

            recommendations=recommendations,
        )

    def _compute_schema_score(self, schema):

        score = 25.0

        score -= len(schema.missing_columns) * 2

        score -= len(schema.unexpected_columns)

        score -= schema.duplicate_flow_ids * 0.25

        score -= len(schema.missing_values) * 0.5

        return max(0.0, score)

    def _compute_qos_score(self, qos):

        if qos.total_rows == 0:
            return 25.0

        ratio = len(qos.violations) / qos.total_rows

        return max(0.0, 25 * (1 - ratio))

    def _compute_correlation_score(
        self,
        correlations,
    ):

        if not correlations:
            return 20.0

        passed = sum(
            c.passed
            for c in correlations
        )

        return 20 * (passed / len(correlations))

    def _compute_distribution_score(
        self,
        distributions,
    ):

        return 15.0

    def _compute_outlier_score(
        self,
        outliers,
        rows,
    ):

        if rows == 0:
            return 15.0

        total = sum(
            o.iqr_outliers
            for o in outliers
        )

        ratio = total / rows

        return max(
            0.0,
            15 * (1 - ratio),
        )

    def _generate_recommendations(
        self,
        schema,
        qos,
        correlations,
        outliers,
    ):

        recommendations = []

        if not schema.passed:
            recommendations.append(
                "Resolve schema validation issues."
            )

        if qos.violations:
            recommendations.append(
                "Resolve QoS consistency violations."
            )

        failed = [
            c
            for c in correlations
            if not c.passed
        ]

        if failed:
            recommendations.append(
                f"Improve {len(failed)} feature correlations."
            )

        if any(
            o.iqr_outliers > 0
            for o in outliers
        ):
            recommendations.append(
                "Reduce unrealistic outliers."
            )

        return recommendations