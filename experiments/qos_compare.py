#!/usr/bin/env python3
"""
Per-class QoS of a set of runs, from their own measured datasets.

    python experiments/qos_compare.py <run-id prefix> [--transient]

For each (scenario, scheduler): SLA-met share of flow windows per class (each
application's own targets), mean loss and median per-window p95 delay, the
share of windows failing on loss vs delay, and weighted utility. With
--transient, only flow windows overlapping the 10 s after each context change
(QoS while the controller adapts to the new traffic mix). Used to check
each control change on the network before it goes into the evaluation matrix.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
SERVICES = ("healthcare", "education", "agriculture", "general")


TRANSIENT_S = 10


def _transient_windows(summary: dict, df: pd.DataFrame) -> pd.DataFrame:
    """Windows overlapping [change tick, change tick + 10 s) for every context change after tick 0."""
    changes = [c["tick"] for c in summary.get("context_history") or [] if c.get("changed") and c["tick"] > 0]
    if not changes or "window_index" not in df:
        return df.iloc[0:0]
    window_s = summary.get("window_s", 5.0)
    keep = set()
    for tick in changes:
        first, last = int(tick // window_s), int((tick + TRANSIENT_S - 1e-6) // window_s)
        keep.update(range(first, last + 1))
    return df[df["window_index"].isin(keep)]


def load(prefix: str, transient: bool = False) -> pd.DataFrame:
    from core.config import load_yaml

    sla = {s: c["sla"] for s, c in load_yaml("slices.yaml")["service_slices"].items()}
    rows = []
    for run_dir in sorted((REPO_ROOT / "results" / "runs").glob(f"{prefix}*")):
        summary_path, data_path = run_dir / "summary.json", run_dir / "dataset.csv"
        if not summary_path.exists() or not data_path.exists():
            continue
        summary = json.loads(summary_path.read_text())
        df = pd.read_csv(data_path, low_memory=False)
        if transient:
            df = _transient_windows(summary, df)
            if df.empty:
                continue
        row = {"run": run_dir.name, "scenario": summary.get("timeline") or summary.get("scenario_id"), "scheduler": summary.get("scheduler"),
               "seed": summary.get("seed"), "utility": summary.get("weighted_utility")}
        for s in SERVICES:
            g = df[df["service_class"] == s]
            if g.empty:
                continue
            row[f"{s}_sla"] = g["sla_satisfied"].astype(bool).mean()
            row[f"{s}_loss"] = g["packet_loss_rate"].mean()
            row[f"{s}_p95"] = g["p95_latency_ms"].median()
            row[f"{s}_fail_loss"] = (g["packet_loss_rate"] > sla[s]["loss_pct"]).mean()
            row[f"{s}_fail_delay"] = (g["p95_latency_ms"] > sla[s]["latency_ms"]).mean()
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    prefix = sys.argv[1]
    df = load(prefix, transient="--transient" in sys.argv)
    if df.empty:
        raise SystemExit(f"no runs with prefix {prefix}")
    keys = ["scenario", "scheduler"]
    table = df.drop(columns=["run", "seed"]).groupby(keys).mean(numeric_only=True)
    pd.set_option("display.width", 200)
    for s in SERVICES:
        cols = [c for c in table.columns if c.startswith(s)]
        print(f"\n{s}\n" + table[cols].round(3).to_string())
    print("\nweighted utility\n" + table[["utility"]].round(4).to_string())
    print(f"\n{len(df)} runs")


if __name__ == "__main__":
    main()
