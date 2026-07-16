"""
CSV Exporter

Exports generated DatasetRecord objects into CSV files.

Author: RSNSD
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from RSNSD.domain.dataset import DatasetRecord
from RSNSD.feature_extractor.extractor import FeatureExtractor


class CSVExporter:

    def __init__(self):

        self.extractor = FeatureExtractor()

    def export(

        self,

        dataset: list[DatasetRecord],

        output_file: str | Path,

    ) -> None:

        rows = []

        for record in dataset:

            rows.append(

                self.extractor.extract(record)

            )

        df = pd.DataFrame(rows)

        output_file = Path(output_file)

        output_file.parent.mkdir(

            parents=True,

            exist_ok=True,

        )

        df.to_csv(

            output_file,

            index=False,

        )

        print()

        print("=" * 60)

        print(f"Dataset exported to:\n{output_file}")

        print(f"Rows    : {len(df)}")

        print(f"Columns : {len(df.columns)}")

        print("=" * 60)