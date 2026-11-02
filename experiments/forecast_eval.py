#!/usr/bin/env python3
"""
Forecast quality of the demand predictors on live runs (Step 5 of the evaluation).

    python experiments/forecast_eval.py "results/runs/final_prediction__*"   [--out results/tables/forecast_quality.csv]

For every run and slice, the per-tick measured offered load (feedback.csv,
``<slice>_tput_mbps``: uplink access-port rate + downlink offered rate) is
replayed. At each control decision t (every 5 ticks) each predictor sees only
samples ≤ t and forecasts the mean offered load of the next control interval
(t, t+5]; the realised mean is the target.

  reactive    mean of the last interval (what the QoS-aware allocator plans for)
  holt        Holt level+trend, one interval ahead (the original estimator)
  ramp        reactive + least-squares ramp extrapolation (the predictive scheduler)
  oracle      the realised value (upper bound; zero error by construction, kept as a
              row so tables show the gap explicitly)

Reported per predictor (and per workload): MAE, MAPE, and the share of
decisions that under-predict by more than 10 % (under-provisioning risk), on
decisions where the slice offered ≥ 0.5 Mb/s.
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from slicing.demand_estimator import HoltForecaster, _ramp_forecast  # noqa: E402

SERVICES = ("healthcare", "education", "agriculture", "general")
INTERVAL = 5


def predictions(series: np.ndarray) -> list[dict]:
    rows = []
    holt = HoltForecaster()
    for t in range(len(series)):
        holt.update(series[t])
        if t < INTERVAL or (t + 1) % INTERVAL or t + INTERVAL >= len(series):
            continue
        window = series[t - INTERVAL + 1:t + 1]
        target = float(series[t + 1:t + 1 + INTERVAL].mean())
        reactive = float(window.mean())
        rows.append({"t": t, "target": target, "reactive": reactive,
                     "holt": holt.forecast(INTERVAL // 2 + 1),
                     "ramp": max(reactive, _ramp_forecast(list(window), 2)),
                     "oracle": target})
    return rows


def evaluate(pattern: str) -> pd.DataFrame:
    records = []
    for run_dir in sorted(glob.glob(pattern)):
        path = Path(run_dir) / "feedback.csv"
        if not path.exists():
            continue
        fb = pd.read_csv(path)
        summary_path = Path(run_dir) / "summary.json"
        summary = __import__("json").loads(summary_path.read_text()) if summary_path.exists() else {}
        workload = summary.get("timeline") or summary.get("scenario_id") or Path(run_dir).name
        for s in SERVICES:
            col = f"{s}_tput_mbps"
            if col not in fb:
                continue
            for row in predictions(fb[col].fillna(0).to_numpy(dtype=float)):
                if row["target"] < 0.5:
                    continue
                for name in ("reactive", "holt", "ramp", "oracle"):
                    err = row[name] - row["target"]
                    records.append({"run": Path(run_dir).name, "workload": workload, "slice": s,
                                    "predictor": name, "abs_err": abs(err),
                                    "ape": abs(err) / row["target"], "under10": err < -0.1 * row["target"]})
    return pd.DataFrame(records)


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby(["workload", "predictor"]).agg(
        decisions=("abs_err", "size"), mae_mbps=("abs_err", "mean"), mape=("ape", "mean"),
        under_provision_share=("under10", "mean")).round(4).reset_index()
    overall = df.groupby("predictor").agg(
        decisions=("abs_err", "size"), mae_mbps=("abs_err", "mean"), mape=("ape", "mean"),
        under_provision_share=("under10", "mean")).round(4).reset_index().assign(workload="all")
    return pd.concat([out, overall], ignore_index=True)


def main():
    pattern = sys.argv[1]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else str(
        REPO_ROOT / "results" / "tables" / "forecast_quality.csv")
    df = evaluate(pattern)
    if df.empty:
        raise SystemExit(f"no feedback logs match {pattern}")
    table = summarise(df)
    table.to_csv(out, index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
