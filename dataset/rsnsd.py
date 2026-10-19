"""
Seeded, contract-conformant RSNSD generation (data path A).

    python -m dataset.rsnsd --per-scenario 6000 --seed 42

Reuses the RSNSD generator components (scenarios → profile mix → flow
behaviour → context → QoS models → feature extraction), stamps every record
with ``rsnsd-contract-2.0`` provenance, validates it against the shared
contract (``features.contract``) and writes a manifest beside the CSV
(seed, configuration, row and class counts, sha256, code fingerprint).

The RSNSD behaviour and QoS models draw from the module-level ``random``
generator; it is seeded for the duration of a generation and then restored,
so the same seed reproduces the same dataset byte for byte.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import pandas as pd

from core.config import REPO_ROOT
from core.provenance import file_sha256, write_manifest
from features.contract import SCHEMA_VERSION, stamp, validate

SOURCE = "synthetic_rsnsd"
DEFAULT_OUTPUT = REPO_ROOT / "RSNSD" / "dataset" / "raw" / "rsnsd_v1.0.csv"


def generate(n_per_scenario: int, seed: int) -> pd.DataFrame:
    from RSNSD.context.scenarios import ALL_SCENARIOS
    from RSNSD.feature_extractor.extractor import FeatureExtractor
    from RSNSD.scripts.generate_release import balance_weights
    from RSNSD.traffic_generator import ALL_PROFILES
    from RSNSD.traffic_generator.common.context_generator import ContextGenerator
    from RSNSD.traffic_generator.common.dataset_builder import DatasetBuilder
    from RSNSD.traffic_generator.common.flow_generator import FlowGenerator
    from RSNSD.traffic_generator.common.sampler import Sampler

    saved = random.getstate()
    random.seed(seed)
    try:
        builder = DatasetBuilder(FlowGenerator(Sampler(seed=seed)), ContextGenerator(seed=seed), seed=seed)
        weights = balance_weights(ALL_PROFILES)
        extractor = FeatureExtractor()
        rows = [
            {**extractor.extract(record), "rsnsd_scenario": scenario.name}
            for scenario in ALL_SCENARIOS
            for record in builder.generate_dataset(
                profiles=ALL_PROFILES, weights=weights, scenario=scenario, n_records=n_per_scenario,
            )
        ]
    finally:
        random.setstate(saved)
    df = pd.DataFrame(rows)
    # Columns the RSNSD models never populate stay empty in the raw export;
    # the contract treats them as configured constants, filled with 0.
    return df.dropna(axis=1, how="all").pipe(_fill_unpopulated)


def _fill_unpopulated(df: pd.DataFrame) -> pd.DataFrame:
    from features.schema_mapper import SCHEMA_COLUMNS

    for column in SCHEMA_COLUMNS:
        if column not in df.columns:
            df[column] = 0
    return df.fillna(0)


def build(n_per_scenario: int, seed: int, output: str | Path = DEFAULT_OUTPUT) -> dict:
    config_id = f"rsnsd-n{n_per_scenario}-s{seed}"
    df = stamp(generate(n_per_scenario, seed), SOURCE, seed, config_id)
    report = validate(df, SOURCE)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    manifest = {
        "schema_version": SCHEMA_VERSION, "provenance_source": SOURCE, "seed": seed,
        "config_id": config_id, "n_per_scenario": n_per_scenario, "rows": len(df),
        "columns": len(df.columns),
        "class_counts": df["service_class"].value_counts().sort_index().to_dict(),
        "scenarios": int(df["rsnsd_scenario"].nunique()),
        "output": str(output), "sha256": file_sha256(output), "validation": report.as_dict(),
        "statistical_validation": statistical_validation(output),
    }
    write_manifest(output.with_suffix(".manifest.json"), manifest)
    return manifest


def statistical_validation(csv_path: str | Path) -> dict:
    """RSNSD's distribution/QoS/correlation/outlier checks (schema score is
    reduced only by the contract's provenance columns, which it does not know)."""
    from RSNSD.validator.validator import DatasetValidator

    report = DatasetValidator().validate(str(csv_path))
    return {
        "score": round(report.score, 2), "passed": bool(report.passed),
        "components": {
            "schema": report.schema_score, "qos": report.qos_score, "correlation": report.correlation_score,
            "distribution": report.distribution_score, "outliers": round(report.outlier_score, 2),
        },
        "unexpected_columns": list(report.schema.unexpected_columns),
        "recommendations": list(report.recommendations),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--per-scenario", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    manifest = build(args.per_scenario, args.seed, args.output)
    print(f"{manifest['rows']} rows, {manifest['columns']} columns → {manifest['output']}")
    stats = manifest["statistical_validation"]
    print(f"classes {manifest['class_counts']}  sha256 {manifest['sha256'][:16]}  contract OK")
    print(f"statistical validation {stats['score']}/100 ({'PASS' if stats['passed'] else 'FAIL'})")


if __name__ == "__main__":
    main()
