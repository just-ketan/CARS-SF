"""Experiment matrix expansion and aggregation statistics."""

import numpy as np
import pandas as pd
import yaml

from experiments.aggregate import paired_tests, summarise
from experiments.run_matrix import expand


def _config():
    with open("configs/experiments/thesis.yaml", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_matrix_run_ids_are_unique_and_variants_applied():
    config = _config()
    runs = [r for study in config["studies"] for r in expand(config, study)]
    ids = [r["run_id"] for r in runs]
    assert len(ids) == len(set(ids))
    ablation = {r["variant"]: r for r in expand(config, "ablation") if r["seed"] == 0 and r["scenario"] == "school"}
    assert ablation["no_surplus_strict"]["scheduler"] == "no_surplus"
    assert ablation["no_surplus_strict"]["work_conserving"] is False
    assert ablation["full"]["scheduler"] == "proposed"
    main = expand(config, "main")
    assert len(main) == 5 * 8 * 5 and all(r["apply_qos"] for r in main)


def test_summary_confidence_interval():
    df = pd.DataFrame({"scheduler": ["a"] * 5, "metric": [1.0, 2.0, 3.0, 4.0, 5.0]})
    row = summarise(df, ["scheduler"]).iloc[0]
    assert row["metric_mean"] == 3.0
    assert abs(row["metric_ci95"] - 2.776 * np.std([1, 2, 3, 4, 5], ddof=1) / np.sqrt(5)) < 1e-3


def test_paired_wilcoxon_detects_consistent_improvement():
    rows = []
    for scenario in ("a", "b"):
        for seed in range(5):
            rows.append({"scenario": scenario, "seed": seed, "scheduler": "proposed", "weighted_utility": 0.9 + seed * 0.01})
            rows.append({"scenario": scenario, "seed": seed, "scheduler": "static", "weighted_utility": 0.7 + seed * 0.01})
    result = paired_tests(pd.DataFrame(rows))
    row = result[(result["baseline"] == "static") & (result["metric"] == "weighted_utility")].iloc[0]
    assert row["pairs"] == 10 and row["significant_0.05"] and row["mean_difference"] > 0
