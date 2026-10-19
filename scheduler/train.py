#!/usr/bin/env python3
"""Train the Learning Engine policies.

    python scheduler/train.py --algo cem --episodes 30                     # CEM on the sequential env
    python scheduler/train.py --algo ppo --timesteps 200000 --seeds 0 1 2  # PPO, one run per seed
    python scheduler/train.py --algo all

Both algorithms use SequentialSlicingEnv and the shared reward
(scheduler/reward.py). Evaluation episodes use fixed seeds disjoint from the
training and validation seeds.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.agent import RLAgent, train_ppo_seeds

RESULTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "rl_training.json"
)


def main():
    parser = argparse.ArgumentParser(description="Train RL scheduler policies")
    parser.add_argument("--algo", choices=["cem", "ppo", "all"], default="all")
    parser.add_argument("--episodes", type=int, default=30, help="CEM iterations per context")
    parser.add_argument("--timesteps", type=int, default=200_000, help="PPO environment steps")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--evaluate-only", action="store_true",
                        help="re-evaluate the deployed CEM and PPO models on the test seeds (no training)")
    args = parser.parse_args()

    results = {}
    if os.path.exists(RESULTS_PATH):          # keep the other algorithm's results when training one
        with open(RESULTS_PATH, encoding="utf-8") as handle:
            results = {k: v for k, v in json.load(handle).items() if k in ("cem", "ppo", "evaluation")}
    if args.evaluate_only:
        from stable_baselines3 import PPO

        from scheduler.agent import PPO_MODEL_PATH, compare_policies
        ppo = PPO.load(PPO_MODEL_PATH, device="cpu") if os.path.exists(PPO_MODEL_PATH) else None
        results["evaluation"] = compare_policies(ppo)
    elif args.algo in ("cem", "all"):
        results["cem"] = RLAgent().train(episodes=args.episodes, seed=args.seeds[0])
    if args.algo in ("ppo", "all") and not args.evaluate_only:
        results["ppo"] = train_ppo_seeds(args.seeds, args.timesteps)

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, default=str)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
