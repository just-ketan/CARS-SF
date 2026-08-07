#!/usr/bin/env python3
"""
CARS-SF experiment entry point.

Usage:
    sudo python run_experiment.py [--scenario normal] [--duration 30] [--apply-qos]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="CARS-SF Mininet Experiment")
    parser.add_argument(
        "--scenario", default="normal",
        choices=["normal", "school", "harvest", "disaster", "medical_emergency", "fiber_cut"],
    )
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--apply-qos", action="store_true", help="Apply HTB QoS enforcement")
    args = parser.parse_args()

    if os.geteuid() != 0:
        print("ERROR: Mininet requires root privileges. Run with sudo.")
        sys.exit(1)

    from core.orchestrator import run_experiment

    results = run_experiment(
        scenario_id=args.scenario,
        duration=args.duration,
        apply_qos=args.apply_qos,
    )

    print("\n=== Experiment Complete ===")
    print(f"Scenario:    {results['scenario_id']}")
    print(f"Records:     {results.get('record_count', 0)}")
    print(f"Dataset:     {results.get('dataset_path', 'N/A')}")
    print(f"Validation:  {results.get('validation_report', {}).get('total_score', 'N/A')}/100")
    print(f"Allocation:  {results.get('allocation', {})}")


if __name__ == "__main__":
    main()
