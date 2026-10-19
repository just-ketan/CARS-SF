#!/usr/bin/env python3
"""
Collect a Mininet-measured dataset across scenarios and seeds.

    python experiments/collect_dataset.py --scenarios normal school harvest disaster \
        --seeds 0 1 2 --duration 60

As root it runs the real pipeline (Open vSwitch); otherwise it uses the
sudo-free namespace harness (Linux bridges). Per-run artefacts land in
results/runs/collect__<scenario>__s<seed>/; the merged dataset and aligned
packet sequences are written to generated/datasets/mininet_full_dataset.{csv,npz}.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from core.config import GENERATED_DIR, RESULTS_DIR  # noqa: E402
from core.provenance import file_sha256, write_manifest  # noqa: E402
from features.contract import SCHEMA_VERSION, stamp, validate  # noqa: E402

MERGED_CSV = GENERATED_DIR / "datasets" / "mininet_full_dataset.csv"
MERGED_NPZ = GENERATED_DIR / "datasets" / "mininet_full_dataset.npz"


def run_one(scenario: str, seed: int, duration: int, scheduler: str, ues: int) -> dict:
    run_id = f"collect__{scenario}__s{seed}"
    options = dict(apply_qos=True, scheduler=scheduler, seed=seed, run_id=run_id, ues_per_service=ues)
    if os.geteuid() == 0:
        from core.orchestrator import run_experiment
        return run_experiment(scenario, duration, **options)
    from tests.integration.harness import run_in_namespace, userns_available
    if not userns_available():
        raise SystemExit("Need root (sudo .venv/bin/python ...) or unprivileged user namespaces")
    return run_in_namespace(scenario, duration, timeout=duration * 6 + 300, **options)


def merge(prefix: str = "collect__") -> tuple[pd.DataFrame, np.ndarray | None]:
    frames, sequences, rejected = [], [], []
    for run_dir in sorted((RESULTS_DIR / "runs").glob(f"{prefix}*")):
        csv_path, npz_path = run_dir / "dataset.csv", run_dir / "sequences.npz"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path, low_memory=False)
        if "provenance_source" not in df.columns:      # runs recorded before the contract existed
            df = stamp(df, "mininet_measured", int(df["seed"].iloc[0]) if "seed" in df else None, run_dir.name)
        report = validate(df, "mininet_measured", raise_on_error=False)
        if not report.ok:
            print(f"rejecting {run_dir.name}: {report.errors}")
            rejected.append({"run": run_dir.name, "errors": report.errors})
            continue
        if npz_path.exists():
            seq = np.load(npz_path, allow_pickle=True)["X"]
            if len(seq) != len(df):
                continue
            sequences.append(seq)
        frames.append(df)
    if not frames:
        raise SystemExit("no collected runs found")
    merged = pd.concat(frames, ignore_index=True)
    validate(merged, "mininet_measured")
    seqs = np.concatenate(sequences) if len(sequences) == len(frames) else None
    MERGED_CSV.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(MERGED_CSV, index=False)
    if seqs is not None:
        np.savez_compressed(MERGED_NPZ, X=seqs)
    write_manifest(MERGED_CSV.with_suffix(".manifest.json"), {
        "schema_version": SCHEMA_VERSION, "provenance_source": "mininet_measured",
        "rows": len(merged), "runs": sorted(merged["run_id"].unique().tolist()),
        "seeds": sorted(int(s) for s in merged["seed"].unique()),
        "class_counts": merged["service_class"].value_counts().sort_index().to_dict(),
        "rejected_runs": rejected, "sha256": file_sha256(MERGED_CSV), "sequences": seqs is not None,
    })
    return merged, seqs


def main():
    parser = argparse.ArgumentParser(description="Collect Mininet-measured dataset")
    parser.add_argument("--scenarios", nargs="+",
                        default=["normal", "school", "harvest", "disaster", "medical_emergency", "fiber_cut"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1])
    parser.add_argument("--duration", type=int, default=45)
    parser.add_argument("--scheduler", default="proposed")
    parser.add_argument("--ues-per-service", type=int, default=2)
    parser.add_argument("--merge-only", action="store_true")
    args = parser.parse_args()

    if not args.merge_only:
        for scenario in args.scenarios:
            for seed in args.seeds:
                result = run_one(scenario, seed, args.duration, args.scheduler, args.ues_per_service)
                print(json.dumps({
                    "run": result.get("run_id"), "records": result.get("record_count"),
                    "source": result.get("data_source"),
                    "validation": result.get("validation_report", {}).get("total_score"),
                }), flush=True)
    merged, seqs = merge()
    print(f"merged {len(merged)} records from {merged['run_id'].nunique()} runs; "
          f"sequences: {None if seqs is None else seqs.shape}")


if __name__ == "__main__":
    main()
