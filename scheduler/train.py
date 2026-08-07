#!/usr/bin/env python3
"""Train RL scheduler agent."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.agent import RLAgent


def main():
    parser = argparse.ArgumentParser(description="Train RL scheduler")
    parser.add_argument("--episodes", type=int, default=200)
    args = parser.parse_args()

    agent = RLAgent()
    results = agent.train(episodes=args.episodes)

    print("\n=== RL Scheduler Training Results ===")
    for key, value in results.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
