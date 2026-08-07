"""
Outlier Detection

Detects statistical outliers using IQR and Z-score methods.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class OutlierSummary:

    feature: str

    iqr_outliers: int

    zscore_outliers: int

    maximum: float

    minimum: float


class OutlierAnalyzer:

    FEATURES = [

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

    ) -> list[OutlierSummary]:

        summaries = []

        for feature in self.FEATURES:

            if feature not in dataframe.columns:

                continue

            series = dataframe[feature].dropna()

            q1 = series.quantile(0.25)

            q3 = series.quantile(0.75)

            iqr = q3 - q1

            lower = q1 - 3.0 * iqr

            upper = q3 + 3.0 * iqr

            iqr_outliers = (

                (series < lower)

                |

                (series > upper)

            ).sum()

            std = series.std()

            if std == 0:

                zscore_outliers = 0

            else:

                zscores = np.abs(

                    (series - series.mean())

                    / std

                )

                zscore_outliers = (

                    zscores > 3

                ).sum()

            summaries.append(

                OutlierSummary(

                    feature=feature,

                    iqr_outliers=int(iqr_outliers),

                    zscore_outliers=int(zscore_outliers),

                    maximum=float(series.max()),

                    minimum=float(series.min()),

                )

            )

        return summaries