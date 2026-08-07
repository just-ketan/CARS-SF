"""
QoS Consistency Validation

Detects logically impossible or unrealistic QoS records.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class QoSViolation:

    row: int

    feature: str

    value: float

    rule: str


@dataclass(slots=True)
class QoSValidationResult:

    total_rows: int

    violations: list[QoSViolation]

    passed: bool


class QoSValidator:

    def validate(

        self,

        dataframe: pd.DataFrame,

    ) -> QoSValidationResult:

        violations = []

        for index, row in dataframe.iterrows():

            # --------------------------------------------
            # Throughput / Goodput
            # --------------------------------------------

            if (

                row["goodput_mbps"]

                >

                row["throughput_mbps"]

            ):

                violations.append(

                    QoSViolation(

                        row=index,

                        feature="goodput_mbps",

                        value=row["goodput_mbps"],

                        rule="Goodput cannot exceed throughput",

                    )

                )

            # --------------------------------------------
            # Packet Loss
            # --------------------------------------------

            if not (

                0

                <=

                row["packet_loss_rate"]

                <=

                100

            ):

                violations.append(

                    QoSViolation(

                        row=index,

                        feature="packet_loss_rate",

                        value=row["packet_loss_rate"],

                        rule="Packet loss must be between 0 and 100",

                    )

                )

            # --------------------------------------------
            # Latency
            # --------------------------------------------

            if row["end_to_end_latency_ms"] < 0:

                violations.append(

                    QoSViolation(

                        row=index,

                        feature="end_to_end_latency_ms",

                        value=row["end_to_end_latency_ms"],

                        rule="Latency cannot be negative",

                    )

                )

            # --------------------------------------------
            # Jitter
            # --------------------------------------------

            if row["jitter_ms"] < 0:

                violations.append(

                    QoSViolation(

                        row=index,

                        feature="jitter_ms",

                        value=row["jitter_ms"],

                        rule="Jitter cannot be negative",

                    )

                )

            # --------------------------------------------
            # Queue Delay
            # --------------------------------------------

            if row["queueing_delay_ms"] < 0:

                violations.append(

                    QoSViolation(

                        row=index,

                        feature="queueing_delay_ms",

                        value=row["queueing_delay_ms"],

                        rule="Queue delay cannot be negative",

                    )

                )

            # --------------------------------------------
            # Retransmissions
            # --------------------------------------------

            if row["retransmission_rate"] < 0:

                violations.append(

                    QoSViolation(

                        row=index,

                        feature="retransmission_rate",

                        value=row["retransmission_rate"],

                        rule="Retransmission rate cannot be negative",

                    )

                )

            # --------------------------------------------
            # QoS Score
            # --------------------------------------------

            if not (

                0

                <=

                row["qos_satisfaction_score"]

                <=

                100

            ):

                violations.append(

                    QoSViolation(

                        row=index,

                        feature="qos_satisfaction_score",

                        value=row["qos_satisfaction_score"],

                        rule="QoS score must be between 0 and 100",

                    )

                )

        return QoSValidationResult(

            total_rows=len(dataframe),

            violations=violations,

            passed=len(violations) == 0,

        )