#!/usr/bin/env python3
"""Train SliceNet. See experiments/run_slicenet_pipeline.py for the full study."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classification.pipeline import train_baseline, train_mininet  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Train SliceNet classifier")
    parser.add_argument("--mininet", action="store_true", help="train RF + CNN on the collected Mininet dataset")
    args = parser.parse_args()
    train_mininet() if args.mininet else train_baseline()


if __name__ == "__main__":
    main()
