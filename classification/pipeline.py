"""
SliceNet training pipeline:
  1. Baseline on the RSNSD v1 synthetic dataset (random forest)
  2. Mininet-measured dataset (experiments/collect_dataset.py)
  3. SliceNet on Mininet data: random forest (shape features) and 1D-CNN
     (packet sequences + shape), both scored on held-out runs × UEs
  4. Transfer study: synthetic model zero-shot on Mininet data, and the same
     model fine-tuned with a growing share of Mininet groups
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from classification.slicenet import (
    MODEL_DIR, SERVICE_CLASSES, SliceNetClassifier, SliceNetCNN, group_labels,
)
from core.config import GENERATED_DIR, REPO_ROOT
from features.schema_mapper import ML_FEATURE_COLUMNS

SYNTHETIC_DATASET = REPO_ROOT / "RSNSD" / "dataset" / "raw" / "rsnsd_v1.0.csv"
BASELINE_MODEL = MODEL_DIR / "slicenet_baseline.pkl"
MININET_MODEL = MODEL_DIR / "slicenet_mininet.pkl"
RESULTS_DIR = REPO_ROOT / "results"
MININET_MERGED = GENERATED_DIR / "datasets" / "mininet_full_dataset.csv"
MININET_SEQUENCES = GENERATED_DIR / "datasets" / "mininet_full_dataset.npz"
COMPARISON_REPORT = RESULTS_DIR / "slicenet_comparison.json"


def _save(name: str, payload: dict[str, Any]):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(RESULTS_DIR / name, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)


def train_baseline(test_size: float = 0.2) -> dict[str, Any]:
    """Step 1: SliceNet (RF) on RSNSD v1 synthetic data."""
    if not SYNTHETIC_DATASET.exists():
        raise FileNotFoundError(f"Synthetic dataset not found: {SYNTHETIC_DATASET} (run `make data`)")
    print("STEP 1: baseline on RSNSD v1 synthetic dataset")
    df = pd.read_csv(SYNTHETIC_DATASET, low_memory=False)
    metrics = SliceNetClassifier(model_path=str(BASELINE_MODEL)).train(df, test_size=test_size)
    metrics.update({
        "dataset": "RSNSD_v1_synthetic", "dataset_path": str(SYNTHETIC_DATASET),
        "rows": len(df), "model_path": str(BASELINE_MODEL), "timestamp": datetime.now().isoformat(),
    })
    _save("slicenet_baseline_metrics.json", metrics)
    print(f"  F1 macro {metrics['f1_macro']:.4f} ({metrics['split']})")
    return metrics


def load_mininet() -> tuple[pd.DataFrame, np.ndarray | None]:
    if not MININET_MERGED.exists():
        raise FileNotFoundError(
            f"Mininet dataset not found: {MININET_MERGED}\n"
            "Collect it first: python experiments/collect_dataset.py"
        )
    df = pd.read_csv(MININET_MERGED, low_memory=False)
    seqs = np.load(MININET_SEQUENCES)["X"] if MININET_SEQUENCES.exists() else None
    if seqs is not None and len(seqs) != len(df):
        seqs = None
    return df, seqs


def train_mininet(test_size: float = 0.25) -> dict[str, Any]:
    """Step 3: RF and 1D-CNN on Mininet-measured traffic shape."""
    print("STEP 3: SliceNet on Mininet-measured dataset")
    df, seqs = load_mininet()
    results: dict[str, Any] = {
        "dataset": "mininet_measured", "rows": len(df),
        "runs": int(df["run_id"].nunique()) if "run_id" in df else None,
        "groups": int(len(set(group_labels(df)))),
        "timestamp": datetime.now().isoformat(),
    }
    rf = SliceNetClassifier(model_path=str(MININET_MODEL)).train(df, test_size=test_size)
    results["random_forest"] = rf
    print(f"  RF  F1 macro {rf['f1_macro']:.4f} ({rf['split']}, {rf['test_size']} test windows)")
    if seqs is not None:
        cnn = SliceNetCNN().train(df, seqs, test_size=test_size)
        results["cnn_1d"] = cnn
        print(f"  CNN F1 macro {cnn['f1_macro']:.4f}")
    _save("slicenet_mininet_metrics.json", results)
    return results


def transfer_study(fractions=(0.0, 0.1, 0.25, 0.5), seed: int = 42) -> dict[str, Any]:
    """Step 4: does synthetic pre-training transfer to measured traffic?

    Uses the feature columns both datasets share. Mininet groups (run × UE)
    are split once into a held-out test half; a growing fraction of the other
    half is mixed into the synthetic training data.
    """
    from sklearn.ensemble import RandomForestClassifier

    print("STEP 4: synthetic → Mininet transfer study")
    synthetic = pd.read_csv(SYNTHETIC_DATASET, low_memory=False)
    mininet, _ = load_mininet()
    columns = [c for c in ML_FEATURE_COLUMNS if c in synthetic.columns and c in mininet.columns]
    columns = [c for c in columns if pd.api.types.is_numeric_dtype(synthetic[c])]
    label = {c: i for i, c in enumerate(SERVICE_CLASSES)}

    def xy(df):
        df = df[df["service_class"].isin(SERVICE_CLASSES)]
        X = df[columns].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy()
        return X, df["service_class"].map(label).to_numpy()

    groups = group_labels(mininet)
    unique = np.array(sorted(set(groups)))
    rng = np.random.default_rng(seed)
    rng.shuffle(unique)
    test_groups = set(unique[: len(unique) // 2])
    pool_groups = list(unique[len(unique) // 2:])
    test = mininet[np.isin(groups, list(test_groups))]
    X_test, y_test = xy(test)
    X_syn, y_syn = xy(synthetic.sample(min(len(synthetic), 40_000), random_state=seed))

    from sklearn.metrics import f1_score

    curve = []
    for fraction in fractions:
        chosen = set(pool_groups[: int(round(fraction * len(pool_groups)))])
        X_train, y_train = X_syn, y_syn
        if chosen:
            X_add, y_add = xy(mininet[np.isin(groups, list(chosen))])
            X_train, y_train = np.vstack([X_syn, X_add]), np.concatenate([y_syn, y_add])
        model = RandomForestClassifier(n_estimators=200, max_depth=16, random_state=seed, n_jobs=-1)
        model.fit(X_train, y_train)
        f1 = f1_score(y_test, model.predict(X_test), average="macro", labels=list(range(4)), zero_division=0)
        curve.append({"mininet_fraction": fraction, "mininet_groups": len(chosen), "f1_macro": round(float(f1), 4)})
        print(f"  synthetic + {fraction:.0%} Mininet groups → F1 macro {f1:.4f}")

    X_pool, y_pool = xy(mininet[np.isin(groups, pool_groups)])
    only = RandomForestClassifier(n_estimators=200, max_depth=16, random_state=seed, n_jobs=-1).fit(X_pool, y_pool)
    mininet_only = f1_score(y_test, only.predict(X_test), average="macro", labels=list(range(4)), zero_division=0)
    result = {
        "shared_columns": columns,
        "test_groups": len(test_groups),
        "curve": curve,
        "mininet_only_f1_macro": round(float(mininet_only), 4),
    }
    _save("slicenet_transfer.json", result)
    return result


def compare(baseline: dict | None = None, mininet: dict | None = None, transfer: dict | None = None) -> dict[str, Any]:
    def load(name):
        path = RESULTS_DIR / name
        return json.load(open(path, encoding="utf-8")) if path.exists() else None

    baseline = baseline or load("slicenet_baseline_metrics.json")
    mininet = mininet or load("slicenet_mininet_metrics.json")
    transfer = transfer or load("slicenet_transfer.json")
    if not baseline or not mininet:
        raise FileNotFoundError("run the baseline and Mininet training steps first")

    def per_class(m):
        return {c: round(m["report"][c]["f1-score"], 4) for c in SERVICE_CLASSES if c in m.get("report", {})}

    best = mininet.get("cnn_1d") or mininet["random_forest"]
    comparison = {
        "timestamp": datetime.now().isoformat(),
        "baseline": {
            "dataset": "RSNSD_v1_synthetic", "model": "random_forest",
            "rows": baseline.get("rows"), "features": baseline.get("feature_count"),
            "f1_macro": baseline["f1_macro"], "f1_weighted": baseline["f1_weighted"],
            "per_class": per_class(baseline),
        },
        "mininet": {
            "dataset": "mininet_measured", "model": best.get("model"),
            "rows": mininet.get("rows"), "runs": mininet.get("runs"),
            "f1_macro": best["f1_macro"], "f1_weighted": best["f1_weighted"],
            "per_class": per_class(best),
        },
        "mininet_models": {
            name: {"f1_macro": m["f1_macro"], "accuracy": m["accuracy"], "per_class": per_class(m)}
            for name, m in mininet.items() if isinstance(m, dict) and "f1_macro" in m
        },
        "transfer": transfer,
        "delta": {
            "f1_macro": round(best["f1_macro"] - baseline["f1_macro"], 4),
            "f1_weighted": round(best["f1_weighted"] - baseline["f1_weighted"], 4),
        },
        "interpretation": (
            "Baseline: random forest on RSNSD synthetic flows, scored on held-out RSNSD scenarios. "
            "Mininet: classifiers on measured traffic shape, scored on held-out runs × UEs. "
            "The transfer curve shows how much measured data is needed on top of synthetic pre-training."
        ),
    }
    _save("slicenet_comparison.json", comparison)
    return comparison


def run_full_pipeline(skip_collect: bool = True, **collect_args) -> dict[str, Any]:
    baseline = train_baseline()
    if not skip_collect:
        import subprocess
        import sys
        cmd = [sys.executable, str(REPO_ROOT / "experiments" / "collect_dataset.py")]
        for key, value in collect_args.items():
            cmd += [f"--{key.replace('_', '-')}"] + ([str(v) for v in value] if isinstance(value, (list, tuple)) else [str(value)])
        subprocess.run(cmd, check=True)
    mininet = train_mininet()
    transfer = transfer_study()
    comparison = compare(baseline, mininet, transfer)
    try:
        from experiments.plots.plot_slicenet_evaluation import generate_comparison_plots
        generate_comparison_plots(comparison)
    except Exception as exc:
        print(f"  Plot generation skipped: {exc}")
    return {"baseline": baseline, "mininet": mininet, "transfer": transfer, "comparison": comparison}
