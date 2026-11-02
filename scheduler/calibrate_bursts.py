#!/usr/bin/env python3
"""
Calibrate the simulator's sub-second burstiness (σ per slice) from live runs.

    python -m scheduler.calibrate_bursts [run-dir glob ...]

Every live tick with per-slice loss telemetry (feedback.csv columns
``<slice>_loss_pct``, written since the leaf-qdisc fix) is replayed through the
simulator's one-direction service model: the slice's offered load (uplink
access-port rate, i.e. before the bottleneck), its uplink allocation and the competing uplink slice, over one
second of 100 ms sub-steps. The σ pair minimising the squared error between
predicted and measured mean loss (per slice, over all ticks) is written to
``scheduler/models/burst_calibration.json`` with the fit quality.

Only the inelastic uplink slices (healthcare, agriculture) are fitted: their
loss is the overflow the model describes. Elastic (TCP) slices back off instead
of dropping and keep the default σ, which only shapes their queueing delay.
"""

from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.env_dir import BURST_PATH, DEFAULT_BURSTINESS, SERVICES, serve_direction  # noqa: E402

FIT = ("healthcare", "agriculture")
DEFAULT_GLOBS = ("results/runs/devB__*/feedback.csv", "results/runs/devC__*/feedback.csv",
                 "results/runs/calib__*/feedback.csv")


def load_ticks(paths: list[str]) -> pd.DataFrame:
    frames = []
    for path in paths:
        df = pd.read_csv(path)
        if "healthcare_loss_pct" not in df:
            continue
        frames.append(df[df["tick"] >= 5].assign(run=os.path.basename(os.path.dirname(path))))   # skip ramp-up
    if not frames:
        raise SystemExit("no live feedback with per-slice loss telemetry")
    return pd.concat(frames, ignore_index=True)


def predicted_loss(ticks: pd.DataFrame, sigma: dict[str, float], reps: int = 3, seed: int = 0,
                   borrow: float = 1.0) -> pd.DataFrame:
    """Per-tick predicted loss (columns <slice>) aligned with ``ticks``."""
    from core.config import load_yaml

    slices = load_yaml("slices.yaml")["service_slices"]
    target = np.array([(slices[s].get("queue", {}).get("target_ms", 5)
                        + slices[s].get("queue", {}).get("interval_ms", 100)) / 1000 for s in SERVICES])
    order = sorted(range(len(SERVICES)), key=lambda i: slices[SERVICES[i]]["htb_prio"])
    sig = np.array([sigma.get(s, DEFAULT_BURSTINESS[s]) for s in SERVICES])
    rng = np.random.default_rng(seed)
    pred = {s: [] for s in FIT}
    for _, row in ticks.iterrows():
        demand = np.zeros(len(SERVICES))
        alloc = np.full(len(SERVICES), 0.5)
        for i, s in enumerate(SERVICES):
            if s in FIT:
                # Uplink counters are read on the UE access ports, before the bottleneck:
                # for these uplink slices "tput" is already the offered load.
                demand[i] = float(row[f"{s}_tput_mbps"])
                alloc[i] = max(float(row[f"{s}_alloc_mbps"]), 0.5)
        losses = np.zeros(len(SERVICES))
        for _ in range(reps):
            offered, _, dropped, _, _ = serve_direction(
                rng, demand, alloc, order, sig, np.zeros(len(SERVICES)), target, 100.0, 1.0, 10,
                borrow_efficiency=borrow)
            losses += np.where(offered > 0, 100 * dropped / np.maximum(offered, 1e-9), 0.0)
        for i, s in enumerate(SERVICES):
            if s in FIT:
                pred[s].append(losses[i] / reps)
    return pd.DataFrame(pred, index=ticks.index)


def run_means(ticks: pd.DataFrame, values: pd.DataFrame) -> pd.DataFrame:
    return values.assign(run=ticks["run"]).groupby("run").mean()


def main():
    patterns = sys.argv[1:] or list(DEFAULT_GLOBS)
    paths = sorted({p for pattern in patterns for p in glob.glob(pattern)})
    ticks = load_ticks(paths)
    # Fit per-run mean loss (each run is one operating condition), not one pooled mean:
    # a pooled fit can match the average while being wrong in every condition.
    observed = run_means(ticks, pd.DataFrame({s: ticks[f"{s}_loss_pct"].fillna(0) for s in FIT}))
    grid = np.round(np.arange(0.05, 1.25, 0.1), 2)
    best, best_err, best_beta = None, float("inf"), 1.0
    for beta in (0.0, 0.25, 0.5, 0.75, 1.0):
        for sh in grid:
            for sa in grid:
                pred = run_means(ticks, predicted_loss(ticks, {"healthcare": sh, "agriculture": sa}, reps=1,
                                                       borrow=beta))
                err = float(((pred - observed) ** 2).to_numpy().sum())
                if err < best_err:
                    best, best_err, best_beta = {"healthcare": float(sh), "agriculture": float(sa)}, err, beta
    final = run_means(ticks, predicted_loss(ticks, best, reps=5, seed=1, borrow=best_beta))
    record = {
        "sigma": best,
        "borrow_efficiency": best_beta,
        "fit": "least squares over per-run mean loss",
        "per_run": {run: {s: {"observed": round(float(observed.loc[run, s]), 3),
                              "predicted": round(float(final.loc[run, s]), 3)} for s in FIT}
                    for run in observed.index},
        "observed_mean_loss_pct": {s: round(float(observed[s].mean()), 4) for s in FIT},
        "predicted_mean_loss_pct": {s: round(float(final[s].mean()), 4) for s in FIT},
        "rmse_pct": {s: round(float(np.sqrt(((final[s] - observed[s]) ** 2).mean())), 3) for s in FIT},
        "ticks": int(len(ticks)), "runs": len(paths),
    }
    os.makedirs(os.path.dirname(BURST_PATH), exist_ok=True)
    with open(BURST_PATH, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
