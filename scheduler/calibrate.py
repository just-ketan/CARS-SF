"""Calibrate the sequential environment from Mininet feedback logs.

    python -m scheduler.calibrate [generated/telemetry/feedback_*.csv ...]

Estimates the delivered/allocated efficiency of saturated slices (how much of
an HTB allocation turns into delivered throughput) and per-service propagation
delay (minimum probe RTT / 2).
"""

from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.env_seq import CALIBRATION_PATH, DEFAULT_CALIBRATION, SERVICES

FEEDBACK_GLOB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "runs", "*", "feedback.csv"
)


def calibrate(paths: list[str]) -> dict:
    frames = [pd.read_csv(p) for p in paths if os.path.getsize(p) > 0]
    if not frames:
        return dict(DEFAULT_CALIBRATION)
    df = pd.concat(frames, ignore_index=True)
    ratios, prop = [], {}
    for s in SERVICES:
        alloc, demand, tput = df[f"{s}_alloc_mbps"], df[f"{s}_demand_mbps"], df[f"{s}_tput_mbps"]
        saturated = (demand > alloc * 1.1) & (alloc > 1)
        ratios.extend((tput[saturated] / alloc[saturated]).clip(0, 1.2).tolist())
        rtt = df[f"{s}_rtt_ms"].dropna()
        prop[s] = round(float(rtt.min() / 2), 2) if len(rtt) else DEFAULT_CALIBRATION["prop_delay_ms"][s]
    efficiency = float(np.median(ratios)) if ratios else DEFAULT_CALIBRATION["efficiency"]
    return {
        "efficiency": round(min(max(efficiency, 0.5), 1.0), 3),
        "prop_delay_ms": prop,
        "samples": len(df),
        "sources": len(frames),
    }


def main():
    paths = sys.argv[1:] or sorted(glob.glob(FEEDBACK_GLOB))
    result = calibrate(paths)
    os.makedirs(os.path.dirname(CALIBRATION_PATH), exist_ok=True)
    with open(CALIBRATION_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
