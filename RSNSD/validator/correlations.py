"""
Correlation Validation

Validates relationships between networking features.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class CorrelationResult:

    feature_x: str
    feature_y: str

    pearson: float
    spearman: float

    expected_direction: str

    threshold: float

    passed: bool


class CorrelationAnalyzer:

    EXPECTED_RELATIONSHIPS = [
        (
            "network_load_pct",
            "end_to_end_latency_ms",
            "positive",
            0.05,
        ),

        (
            "network_load_pct",
            "packet_loss_rate",
            "positive",
            0.05,
        ),

        (
            "network_load_pct",
            "queueing_delay_ms",
            "positive",
            0.05,
        ),

        (
            "cqi",
            "throughput_mbps",
            "positive",
            0.05,
        ),

        (
            "cqi",
            "packet_loss_rate",
            "negative",
            -0.05,
        ),

        (
            "sinr_db",
            "throughput_mbps",
            "positive",
            0.05,
        ),

        (
            "sinr_db",
            "packet_loss_rate",
            "negative",
            -0.05,
        ),

        (
            "queueing_delay_ms",
            "end_to_end_latency_ms",
            "positive",
            0.05,
        ),

        (
            "jitter_ms",
            "qos_satisfaction_score",
            "negative",
            -0.05,
        ),

        (
            "retransmission_rate",
            "goodput_mbps",
            "negative",
            -0.05,
        ),
    ]

    def analyze(
        self,
        dataframe: pd.DataFrame,
    ) -> list[CorrelationResult]:

        results = []

        for (
            feature_x,
            feature_y,
            expected,
            threshold,
        ) in self.EXPECTED_RELATIONSHIPS:
            if (
                feature_x not in dataframe.columns
                or feature_y not in dataframe.columns
            ):
                continue

            pearson = dataframe[feature_x].corr(
                dataframe[feature_y],
                method="pearson",
            )

            spearman = dataframe[feature_x].corr(
                dataframe[feature_y],
                method="spearman",
            )

            if pd.isna(pearson):
                pearson = 0.0

            if pd.isna(spearman):
                spearman = 0.0

            if expected == "positive":

                passed = pearson >= threshold

            else:

                passed = pearson <= threshold

            results.append(

                CorrelationResult(

                    feature_x=feature_x,

                    feature_y=feature_y,

                    pearson=float(pearson),

                    spearman=float(spearman),

                    expected_direction=expected,

                    threshold=threshold,

                    passed=passed,
                )

            )

        return results