"""
Distribution Validation

Analyzes feature distributions globally and per application.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class MetricSummary:

    mean: float
    median: float
    minimum: float
    maximum: float
    std: float
    percentile95: float


@dataclass(slots=True)
class DistributionResult:

    global_metrics: dict[str, MetricSummary]

    application_metrics: dict[
        str,
        dict[str, MetricSummary],
    ]


class DistributionAnalyzer:

    METRICS = [

        "end_to_end_latency_ms",

        "throughput_mbps",

        "goodput_mbps",

        "packet_loss_rate",

        "jitter_ms",

        "queueing_delay_ms",

        "retransmission_rate",

        "availability_pct",

        "qos_satisfaction_score",

    ]

    def analyze(

        self,

        dataframe: pd.DataFrame,

    ) -> DistributionResult:

        global_metrics = {}

        for metric in self.METRICS:

            if metric not in dataframe.columns:

                continue

            global_metrics[metric] = self._summarize(

                dataframe[metric]

            )

        application_metrics = {}

        grouped = dataframe.groupby(

            "application_id"

        )

        for application, group in grouped:

            application_metrics[application] = {}

            for metric in self.METRICS:

                if metric not in group.columns:

                    continue

                application_metrics[application][metric] = (

                    self._summarize(

                        group[metric]

                    )

                )

        return DistributionResult(

            global_metrics=global_metrics,

            application_metrics=application_metrics,

        )

    def _summarize(

        self,

        series: pd.Series,

    ) -> MetricSummary:

        return MetricSummary(

            mean=float(series.mean()),

            median=float(series.median()),

            minimum=float(series.min()),

            maximum=float(series.max()),

            std=float(series.std()),

            percentile95=float(

                series.quantile(0.95)

            ),

        )