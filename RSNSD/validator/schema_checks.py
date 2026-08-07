"""
Schema Validation

Verifies that the generated dataset conforms to the RSNSD schema.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class SchemaValidationResult:

    missing_columns: list[str]

    unexpected_columns: list[str]

    duplicate_flow_ids: int

    missing_values: dict[str, int]

    passed: bool


class SchemaValidator:

    def __init__(

        self,

        expected_columns: list[str],

        required_columns: list[str],

    ):

        self.expected_columns = expected_columns

        self.required_columns = required_columns

    def validate(

        self,

        dataframe: pd.DataFrame,

    ) -> SchemaValidationResult:

        dataframe_columns = set(dataframe.columns)

        expected_columns = set(self.expected_columns)

        missing_columns = sorted(

            expected_columns - dataframe_columns

        )

        unexpected_columns = sorted(

            dataframe_columns - expected_columns

        )

        duplicate_flow_ids = 0

        if "flow_id" in dataframe.columns:

            duplicate_flow_ids = dataframe.duplicated(

                subset=["flow_id"]

            ).sum()

        missing_values = {}

        for column in self.required_columns:

            if column in dataframe.columns:

                count = int(

                    dataframe[column].isna().sum()

                )

                if count > 0:

                    missing_values[column] = count

        passed = (

            len(missing_columns) == 0

            and len(unexpected_columns) == 0

            and duplicate_flow_ids == 0

            and len(missing_values) == 0

        )

        return SchemaValidationResult(

            missing_columns=missing_columns,

            unexpected_columns=unexpected_columns,

            duplicate_flow_ids=duplicate_flow_ids,

            missing_values=missing_values,

            passed=passed,

        )