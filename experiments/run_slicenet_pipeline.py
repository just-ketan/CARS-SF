#!/usr/bin/env python3
"""
SliceNet full training pipeline.

  Step 1: Baseline on RSNSD v1 synthetic dataset
  Step 2: Mininet data collection (89-column schema)
  Step 3: Train on Mininet-measured data
  Step 4: Compare baseline vs Mininet

Usage:
    # Full pipeline (Mininet collection requires sudo)
    python experiments/run_slicenet_pipeline.py

    # Baseline only (no Mininet)
    python experiments/run_slicenet_pipeline.py --baseline-only

    # Skip Mininet collection (use existing data)
    python experiments/run_slicenet_pipeline.py --skip-collect

    # Compare existing results
    python experiments/run_slicenet_pipeline.py --compare-only
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classification.pipeline import (
    collect_mininet_data,
    compare,
    run_full_pipeline,
    train_baseline,
    train_mininet,
)


def main():
    parser = argparse.ArgumentParser(description="SliceNet training pipeline")
    parser.add_argument("--baseline-only", action="store_true",
                        help="Train baseline on synthetic data only")
    parser.add_argument("--skip-collect", action="store_true",
                        help="Skip Mininet collection, use existing data")
    parser.add_argument("--compare-only", action="store_true",
                        help="Compare existing baseline and mininet metrics")
    parser.add_argument("--duration", type=int, default=30,
                        help="Mininet experiment duration per scenario (seconds)")
    parser.add_argument("--apply-qos", action="store_true",
                        help="Apply HTB QoS during Mininet collection")
    args = parser.parse_args()

    if args.baseline_only:
        train_baseline()
        return

    if args.compare_only:
        compare()
        return

    run_full_pipeline(
        duration=args.duration,
        apply_qos=args.apply_qos,
        skip_collect=args.skip_collect,
    )


if __name__ == "__main__":
    main()
