#!/usr/bin/env python3
"""
Train SliceNet classifier.

For the full baseline → Mininet → compare pipeline, use:
    python experiments/run_slicenet_pipeline.py
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classification.slicenet import SliceNetClassifier, MODEL_DIR
from core.config import GENERATED_DIR, REPO_ROOT


def main():
    parser = argparse.ArgumentParser(description="Train SliceNet classifier")
    parser.add_argument(
        "--dataset",
        default=str(REPO_ROOT / "RSNSD" / "dataset" / "raw" / "rsnsd_v1.0.csv"),
        help="Path to training dataset CSV",
    )
    parser.add_argument("--mininet", action="store_true",
                        help="Train on Mininet-generated dataset")
    parser.add_argument("--baseline", action="store_true",
                        help="Save as baseline model (slicenet_baseline.pkl)")
    args = parser.parse_args()

    if args.mininet:
        dataset_path = str(GENERATED_DIR / "datasets" / "mininet_full_dataset.csv")
        model_path = str(MODEL_DIR / "slicenet_mininet.pkl")
        label = "Mininet"
    elif args.baseline:
        dataset_path = args.dataset
        model_path = str(MODEL_DIR / "slicenet_baseline.pkl")
        label = "Baseline (Synthetic)"
    else:
        dataset_path = args.dataset
        model_path = str(MODEL_DIR / "slicenet_model.pkl")
        label = "Default"

    if not os.path.exists(dataset_path):
        print(f"Dataset not found: {dataset_path}")
        if args.mininet:
            print("Run: sudo python3 experiments/run_slicenet_pipeline.py")
            print("  or: python3 experiments/run_slicenet_pipeline.py --skip-collect")
        sys.exit(1)

    print(f"[{label}] Loading: {dataset_path}")
    df = pd.read_csv(dataset_path, low_memory=False)
    print(f"  {len(df):,} rows, {len(df.columns)} columns")

    classifier = SliceNetClassifier(model_path=model_path)
    metrics = classifier.train(df)

    print(f"\n=== SliceNet Training Results ({label}) ===")
    print(f"F1 (macro):    {metrics['f1_macro']:.4f}")
    print(f"F1 (weighted): {metrics['f1_weighted']:.4f}")
    print(f"Train size:    {metrics['train_size']}")
    print(f"Test size:     {metrics['test_size']}")
    print(f"Model saved:   {model_path}")


if __name__ == "__main__":
    main()
