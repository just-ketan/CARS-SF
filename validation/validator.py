"""Statistical validation for Mininet-generated datasets."""

from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import load_features


class DatasetValidator:
    """Validates dataset schema, QoS consistency, and basic statistics."""

    PASS_THRESHOLD = 85

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.feature_config = load_features()
        self.score = 0
        self.report: dict[str, Any] = {}

    def validate(self) -> dict[str, Any]:
        schema_score = self._check_schema()
        qos_score = self._check_qos_consistency()
        corr_score = self._check_correlations()
        outlier_score = self._check_outliers()

        self.score = schema_score + qos_score + corr_score + outlier_score
        self.report = {
            "total_score": self.score,
            "passed": self.score >= self.PASS_THRESHOLD,
            "schema_score": schema_score,
            "qos_score": qos_score,
            "correlation_score": corr_score,
            "outlier_score": outlier_score,
            "row_count": len(self.df),
            "column_count": len(self.df.columns),
        }
        return self.report

    def _check_schema(self) -> int:
        required = (
            self.feature_config.get("ml_feature_columns", [])
            + self.feature_config.get("label_columns", [])
        )
        present = sum(1 for col in required if col in self.df.columns)
        ratio = present / max(len(required), 1)
        return int(25 * ratio)

    def _check_qos_consistency(self) -> int:
        score = 25
        if "goodput_mbps" in self.df.columns and "throughput_mbps" in self.df.columns:
            violations = (self.df["goodput_mbps"] > self.df["throughput_mbps"] + 0.01).sum()
            score -= min(10, violations)
        if "packet_loss_rate" in self.df.columns:
            out_of_range = (
                (self.df["packet_loss_rate"] < 0) | (self.df["packet_loss_rate"] > 100)
            ).sum()
            score -= min(10, out_of_range)
        if "end_to_end_latency_ms" in self.df.columns:
            negative = (self.df["end_to_end_latency_ms"] < 0).sum()
            score -= min(5, negative)
        return max(0, score)

    def _check_correlations(self) -> int:
        if "network_load_pct" not in self.df.columns or "end_to_end_latency_ms" not in self.df.columns:
            return 15
        if len(self.df) < 5:
            return 15
        corr = self.df["network_load_pct"].corr(self.df["end_to_end_latency_ms"])
        return 20 if corr >= 0 else 10

    def _check_outliers(self) -> int:
        numeric_cols = self.df.select_dtypes(include="number").columns
        if len(numeric_cols) == 0:
            return 15
        outlier_count = 0
        for col in numeric_cols:
            q1, q3 = self.df[col].quantile(0.25), self.df[col].quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                outliers = ((self.df[col] < q1 - 3 * iqr) | (self.df[col] > q3 + 3 * iqr)).sum()
                outlier_count += outliers
        ratio = outlier_count / max(len(self.df) * len(numeric_cols), 1)
        return 15 if ratio < 0.05 else max(5, int(15 * (1 - ratio)))

    def format_report(self) -> str:
        lines = [
            "CARS-SF Dataset Validation Report",
            "=" * 40,
            f"Score: {self.report.get('total_score', 0)}/100",
            f"Passed: {self.report.get('passed', False)}",
            f"Rows: {self.report.get('row_count', 0)}",
            f"Columns: {self.report.get('column_count', 0)}",
            f"  Schema: {self.report.get('schema_score', 0)}/25",
            f"  QoS: {self.report.get('qos_score', 0)}/25",
            f"  Correlations: {self.report.get('correlation_score', 0)}/20",
            f"  Outliers: {self.report.get('outlier_score', 0)}/15",
        ]
        return "\n".join(lines)
