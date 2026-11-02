#!/usr/bin/env python3
"""
Should the RL agent use a semantic state? Decided by this experiment, in simulation.

    python experiments/semantic_study.py            # comparison, writes results/semantic_study.json
    python experiments/semantic_study.py --deploy   # trains and deploys the closed-loop PPO

Each run trains the residual PPO for 300k steps on the eight evaluated scenarios minus one
held-out scenario, then scores it against the rules (zero residual) on held-out test seeds:
in-distribution and on the scenario it never saw. The only difference between arms is the
observation; PPO, its loss and the reward are identical.

    arms       state v2 (scenario one-hot) | semantic (scheduler/semantic.py)
    held out   medical_emergency, harvest, fiber_cut
    seeds      0, 1, 2     → 9 pairs (held-out scenario, seed)

Decision rule, fixed before running: semantic is adopted only if its held-out gain over
the rules exceeds state v2's by a mean of ≥ 0.25 percentage points with a paired Wilcoxon
p < 0.05, and its in-distribution gain is not lower by more than 0.25 points. Otherwise
the conventional state v2 stays.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

ARMS, HELD_OUT, SEEDS = ("v2", "semantic"), ("medical_emergency", "harvest", "fiber_cut"), (0, 1, 2)
TIMESTEPS, MARGIN = 300_000, 0.25
RUNS = REPO_ROOT / "scheduler" / "models" / "semantic_study"
RESULT = REPO_ROOT / "results" / "semantic_study.json"


def one_run(job: tuple) -> dict:
    os.environ["OMP_NUM_THREADS"] = "1"
    import torch
    torch.set_num_threads(1)
    from stable_baselines3 import PPO

    from scheduler.agent import compare_residual, train_residual_ppo
    from scheduler.env_dir import EVALUATED_SCENARIOS

    state, held_out, seed = job
    train = [c for c in EVALUATED_SCENARIOS if c != held_out]
    base = {"state": state, "triggered": True, "include_failures": True}
    run = train_residual_ppo(TIMESTEPS, seed=seed, run_dir=str(RUNS / f"{state}_{held_out}_s{seed}"),
                             env_kwargs={**base, "contexts": train})
    model = PPO.load(run["model_path"], device="cpu")
    inside = compare_residual(model, env_kwargs={**base, "contexts": train})
    outside = compare_residual(model, env_kwargs={**base, "contexts": [held_out]})
    return {"state": state, "held_out": held_out, "seed": seed,
            "in_distribution_pct": inside["paired_vs_heuristic"]["relative_pct"],
            "held_out_pct": outside["paired_vs_heuristic"]["relative_pct"],
            "held_out_violations": outside["rl_residual"]["sla_violations_per_episode"],
            "heuristic_violations": outside["qos_heuristic"]["sla_violations_per_episode"]}


def compare(workers: int) -> dict:
    import numpy as np
    from scipy import stats

    jobs = [(s, h, seed) for s in ARMS for h in HELD_OUT for seed in SEEDS]
    with ProcessPoolExecutor(workers) as pool:
        rows = list(pool.map(one_run, jobs))
    key = lambda r: (r["held_out"], r["seed"])
    v2 = {key(r): r for r in rows if r["state"] == "v2"}
    semantic = {key(r): r for r in rows if r["state"] == "semantic"}
    keys = sorted(v2)
    outside = np.array([semantic[k]["held_out_pct"] - v2[k]["held_out_pct"] for k in keys])
    inside = np.array([semantic[k]["in_distribution_pct"] - v2[k]["in_distribution_pct"] for k in keys])
    p = float(stats.wilcoxon(outside).pvalue) if np.any(outside) else 1.0
    adopt = bool(outside.mean() >= MARGIN and p < 0.05 and inside.mean() >= -MARGIN)
    result = {"rule": __doc__.split("Decision rule")[1].strip(), "runs": rows,
              "held_out_gain_difference": round(float(outside.mean()), 3), "wilcoxon_p": round(p, 4),
              "in_distribution_gain_difference": round(float(inside.mean()), 3),
              "mean_held_out_pct": {a: round(float(np.mean([r["held_out_pct"] for r in rows if r["state"] == a])), 3) for a in ARMS},
              "mean_in_distribution_pct": {a: round(float(np.mean([r["in_distribution_pct"] for r in rows if r["state"] == a])), 3) for a in ARMS},
              "adopt_semantic": adopt}
    RESULT.write_text(json.dumps(result, indent=2))
    return result


def deploy(workers: int) -> dict:
    """Train on all eight scenarios with the decided state; deploy the best validated seed."""
    from scheduler.agent import MODEL_DIR, ClosedLoopResidualPolicy

    state = "semantic" if json.loads(RESULT.read_text())["adopt_semantic"] else "v2"
    with ProcessPoolExecutor(workers) as pool:
        runs = list(pool.map(_train_final, [(state, s) for s in SEEDS]))
    best = max(runs, key=lambda r: r["best_validation_reward"] or -1e18)
    shutil.copy(best["model_path"], ClosedLoopResidualPolicy.MODEL_PATH)
    metadata = {"state": state, "seed": best["seed"], "seeds": runs, "scenarios": "all eight, failures included"}
    Path(ClosedLoopResidualPolicy.METADATA_PATH).write_text(json.dumps(metadata, indent=2))
    print(MODEL_DIR, {k: v for k, v in metadata.items() if k != "seeds"})
    return metadata


def _train_final(job: tuple) -> dict:
    os.environ["OMP_NUM_THREADS"] = "1"
    import torch
    torch.set_num_threads(1)
    from stable_baselines3 import PPO

    from scheduler.agent import MODEL_DIR, compare_residual, train_residual_ppo
    from scheduler.env_dir import EVALUATED_SCENARIOS

    state, seed = job
    kwargs = {"state": state, "triggered": True, "include_failures": True, "contexts": list(EVALUATED_SCENARIOS)}
    run = train_residual_ppo(TIMESTEPS, seed=seed, run_dir=os.path.join(MODEL_DIR, "ppo_closed_loop_runs", f"seed{seed}"),
                             env_kwargs=kwargs)
    paired = compare_residual(PPO.load(run["model_path"], device="cpu"), env_kwargs=kwargs)["paired_vs_heuristic"]
    return {"seed": seed, "model_path": run["model_path"], "best_validation_reward": run["best_validation_reward"],
            "paired_vs_rules": paired}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--deploy", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    out = deploy(min(args.workers, 3)) if args.deploy else compare(args.workers)
    print(json.dumps({k: v for k, v in out.items() if k not in ("runs", "seeds", "rule")}, indent=2))


if __name__ == "__main__":
    main()
