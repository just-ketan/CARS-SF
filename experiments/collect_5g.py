#!/usr/bin/env python3
"""
SliceNet on the 5G deployment: collect measured traffic, train, validate on all 32 combinations.

    python experiments/collect_5g.py                  # collect, then train
    python experiments/collect_5g.py --train-only

Traffic comes from the live 5G stack (8 scenarios × seeds 30–32, rules controller, address
rules, so labels come from the generator). The Random Forest trains on the Mininet dataset
plus 5G runs of seeds 30 and 31; seed 32 is held out, and the report gives per-scenario ×
per-class recall and precision on that held-out seed (results/slicenet_5g_metrics.json).
The model is saved to classification/models/slicenet_5g.pkl.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "deployment" / "5g"))

from classification.slicenet import MODEL_DIR, SliceNetClassifier  # noqa: E402
from core.config import RESULTS_DIR  # noqa: E402
from scheduler.env_dir import EVALUATED_SCENARIOS  # noqa: E402

SEEDS, HELD_OUT_SEED, PREFIX = (30, 31, 32), 32, "collect5g"
OUT = RESULTS_DIR / "5g"
CLASSES = ("healthcare", "education", "agriculture", "general")


def collect():
    from run_5g import run_loop

    for seed in SEEDS:
        for scenario in EVALUATED_SCENARIOS:
            r = run_loop(scenario, "qos_adaptive", "host", 60, 100.0, seed, run_prefix=PREFIX)
            print(r["run_id"], r["records"], r["enforcement"], flush=True)


def train() -> dict:
    frames = []
    for scenario in EVALUATED_SCENARIOS:
        for seed in SEEDS:
            path = OUT / f"{PREFIX}__{scenario}__qos_adaptive__host__s{seed}.csv"
            df = pd.read_csv(path, low_memory=False)
            df["scenario_5g"], df["seed_5g"] = scenario, seed
            frames.append(df)
    data = pd.concat(frames, ignore_index=True)
    train_5g, test = data[data.seed_5g != HELD_OUT_SEED], data[data.seed_5g == HELD_OUT_SEED]
    mininet = pd.read_csv(REPO_ROOT / "generated" / "datasets" / "mininet_full_dataset.csv", low_memory=False)
    shape = sorted(c for c in data.columns if c.startswith("shape_"))
    pool = pd.concat([mininet, train_5g], ignore_index=True)

    model = SliceNetClassifier(model_path=str(MODEL_DIR / "slicenet_5g.pkl"))
    fit = model.train(pool[shape + ["service_class", "run_id"] + [c for c in ("ue_host",) if c in pool]],
                      test_size=0.2)
    predicted = np.array(model.predict_batch(test))
    per_cell = {}
    for scenario in EVALUATED_SCENARIOS:
        part = test.scenario_5g == scenario
        per_cell[scenario] = {}
        for c in CLASSES:
            truth, guess = part & (test.service_class == c), part & (predicted == c)
            hits = int((truth & guess).sum())
            per_cell[scenario][c] = {"windows": int(truth.sum()),
                                     "recall": round(hits / truth.sum(), 3) if truth.sum() else None,
                                     "precision": round(hits / guess.sum(), 3) if guess.sum() else None}
    report = {"rows_train": len(pool), "rows_test": len(test), "held_out_seed": HELD_OUT_SEED,
              "held_out_accuracy": round(float((predicted == test.service_class).mean()), 4),
              "internal_split": {k: fit[k] for k in ("f1_macro", "split", "test_size") if k in fit},
              "per_scenario_class": per_cell}
    (RESULTS_DIR / "slicenet_5g_metrics.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "per_scenario_class"}, indent=2))
    print(pd.DataFrame({s: {c: v["recall"] for c, v in row.items()} for s, row in per_cell.items()}).T.to_string())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--train-only", action="store_true")
    args = parser.parse_args()
    if not args.train_only:
        collect()
    train()


if __name__ == "__main__":
    main()
