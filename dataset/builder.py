"""Build and export time-aligned dataset records."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

from core.config import GENERATED_DIR, load_features


class DatasetBuilder:
    """Assembles feature records with context and labels into a dataset."""

    def __init__(
        self,
        records: list[dict[str, Any]],
        scenario_id: str = "normal",
        context_name: str = "Normal Day",
    ):
        self.records = records
        self.scenario_id = scenario_id
        self.context_name = context_name
        self.feature_config = load_features()

    def build(self) -> pd.DataFrame:
        enriched = []
        for i, record in enumerate(self.records):
            row = dict(record)
            row["scenario_id"] = self.scenario_id
            row["context_name"] = self.context_name
            row["record_id"] = i
            enriched.append(row)
        return pd.DataFrame(enriched)

    def export(self, output_path: str | None = None) -> str:
        df = self.build()
        if output_path is None:
            os.makedirs(GENERATED_DIR / "datasets", exist_ok=True)
            output_path = str(GENERATED_DIR / "datasets" / "cars_sf_dataset.csv")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        return output_path

    @staticmethod
    def get_ml_columns() -> list[str]:
        return load_features().get("ml_feature_columns", [])

    @staticmethod
    def get_label_columns() -> list[str]:
        return load_features().get("label_columns", [])
