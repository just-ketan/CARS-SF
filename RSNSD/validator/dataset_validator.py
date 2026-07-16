"""
RSNSD Dataset Validator

Validates generated datasets against the RSNSD schema and
produces a quality report.

Author: RSNSD
"""

from pathlib import Path

import pandas as pd

from RSNSD.schema.feature_registry import FEATURES


class DatasetValidator:

    def validate(
        self,
        dataset_path: str | Path,
    ):

        df = pd.read_csv(dataset_path)

        print()
        print("=" * 72)
        print("RSNSD DATASET VALIDATION REPORT")
        print("=" * 72)

        # =====================================================
        # Dataset Summary
        # =====================================================

        print("\nDataset Summary")
        print("-" * 72)

        print(f"Rows                : {len(df)}")
        print(f"Columns             : {len(df.columns)}")
        print(f"Duplicate Flow IDs  : {df['flow_id'].duplicated().sum()}")

        # =====================================================
        # Schema Compliance
        # =====================================================

        print("\nSchema Compliance")
        print("-" * 72)

        schema_columns = [feature.name for feature in FEATURES]

        missing_columns = [
            c for c in schema_columns
            if c not in df.columns
        ]

        extra_columns = [
            c for c in df.columns
            if c not in schema_columns
        ]

        print(f"Schema Features     : {len(schema_columns)}")
        print(f"CSV Columns         : {len(df.columns)}")
        print(f"Missing Columns     : {len(missing_columns)}")
        print(f"Unexpected Columns  : {len(extra_columns)}")

        # =====================================================
        # Feature Coverage
        # =====================================================

        print("\nFeature Coverage")
        print("-" * 72)

        populated = 0
        empty = 0

        empty_columns = []

        for column in df.columns:

            if df[column].notna().any():
                populated += 1
            else:
                empty += 1
                empty_columns.append(column)

        coverage = populated * 100 / len(df.columns)

        print(f"Populated Columns   : {populated}")
        print(f"Empty Columns       : {empty}")
        print(f"Coverage            : {coverage:.2f}%")

        if empty_columns:

            print("\nColumns not yet implemented:")

            for col in empty_columns:

                print(f"   - {col}")

        # =====================================================
        # Application Distribution
        # =====================================================

        print("\nApplication Distribution")
        print("-" * 72)

        print(df["application_id"].value_counts())

        # =====================================================
        # Slice Distribution
        # =====================================================

        print("\nSlice Distribution")
        print("-" * 72)

        print(df["slice_type"].value_counts())

        # =====================================================
        # Device Distribution
        # =====================================================

        print("\nDevice Distribution")
        print("-" * 72)

        print(df["device_type"].value_counts())

        # =====================================================
        # QoS Statistics
        # =====================================================

        print("\nQoS Statistics")
        print("-" * 72)

        qos_columns = [
            c for c in [
                "end_to_end_latency_ms",
                "jitter_ms",
                "packet_loss_rate",
                "throughput_mbps",
                "goodput_mbps",
            ]
            if c in df.columns
        ]

        print(df[qos_columns].describe())

        # =====================================================
        # Quality Score
        # =====================================================

        print("\nQuality Score")
        print("-" * 72)

        score = coverage

        if df["flow_id"].duplicated().sum() > 0:
            score -= 10

        if len(missing_columns) > 0:
            score -= 10

        score = max(score, 0)

        print(f"Dataset Quality Score : {score:.1f}/100")

        print()
        print("=" * 72)