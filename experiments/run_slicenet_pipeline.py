#!/usr/bin/env python3
"""
SliceNet pipeline: synthetic baseline → Mininet dataset → RF + 1D-CNN → transfer study.

    python experiments/run_slicenet_pipeline.py                  # uses the collected dataset
    python experiments/run_slicenet_pipeline.py --collect --seeds 0 1 --duration 45
    python experiments/run_slicenet_pipeline.py --baseline-only
    python experiments/run_slicenet_pipeline.py --compare-only
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classification.pipeline import compare, run_full_pipeline, train_baseline  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="SliceNet training pipeline")
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--compare-only", action="store_true")
    parser.add_argument("--collect", action="store_true", help="collect Mininet runs first")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1])
    parser.add_argument("--duration", type=int, default=45)
    args = parser.parse_args()

    if args.baseline_only:
        train_baseline()
        return
    if args.compare_only:
        print(json.dumps(compare(), indent=2))
        return
    result = run_full_pipeline(skip_collect=not args.collect, seeds=args.seeds, duration=args.duration)
    print(json.dumps(result["comparison"], indent=2, default=str))


if __name__ == "__main__":
    main()
