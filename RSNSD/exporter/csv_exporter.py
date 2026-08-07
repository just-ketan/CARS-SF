"""
CSV Exporter

Exports generated DatasetRecord objects into CSV files.

Author: RSNSD
"""

from __future__ import annotations

import typing
from pathlib import Path
import pandas as pd

from RSNSD.domain.dataset import DatasetRecord
from RSNSD.feature_extractor.extractor import FeatureExtractor


class CSVExporter:

    def __init__(self):

        self.extractor = FeatureExtractor()

    def export(
        self,
        dataset: typing.Iterable[DatasetRecord],
        output_file: str | Path,
        chunk_size: int = 10000,
    ) -> None:
        import typing
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # We need to write chunk by chunk
        chunk = []
        is_first = True
        total_rows = 0
        columns = 0
        
        def flush_chunk():
            nonlocal chunk, is_first, columns
            if not chunk:
                return
            df = pd.DataFrame(chunk)
            columns = len(df.columns)
            df.to_csv(
                output_file,
                index=False,
                mode='w' if is_first else 'a',
                header=is_first
            )
            
            # Export to Parquet as well
            parquet_file = output_file.with_suffix('.parquet')
            try:
                # Fastparquet supports append
                df.to_parquet(
                    parquet_file,
                    engine='fastparquet',
                    append=not is_first
                )
            except Exception:
                # Fallback: don't fail if fastparquet isn't installed
                pass
            is_first = False
            chunk.clear()
            
        for record in dataset:
            chunk.append(self.extractor.extract(record))
            total_rows += 1
            if len(chunk) >= chunk_size:
                flush_chunk()
                print(f"Exported {total_rows} rows...")
                
        flush_chunk()

        print()

        print("=" * 60)

        print(f"Dataset exported to:\n{output_file}")

        print(f"Rows    : {total_rows}")
        print(f"Columns : {columns}")
        print("=" * 60)