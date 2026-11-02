"""Statistics of the predeclared final analysis (experiments/final_analysis.py)."""

import pandas as pd
import pytest

from experiments.final_analysis import holm, paired, verdict


def test_holm_adjustment_is_monotone_and_bounded():
    adjusted = holm([0.01, 0.04, 0.03, 0.5])
    assert adjusted == pytest.approx([0.04, 0.09, 0.09, 0.5])


def test_paired_difference_ci_and_rank_biserial():
    rows = [{"condition": "c", "seed": s, "scheduler": k, "m": v}
            for s in range(8) for k, v in (("a", 0.9 + 0.01 * s), ("b", 0.8 + 0.01 * s))]
    out = paired(pd.DataFrame(rows), "scheduler", "a", "b", "m")
    assert out["n"] == 8 and out["mean_diff"] == pytest.approx(0.1) and out["rank_biserial"] == 1.0
    assert out["ci_low"] <= 0.1 <= out["ci_high"]


@pytest.mark.parametrize("row,expected", [
    ({"n": 40, "mean_diff": 0.05, "p_holm": 0.01, "rule": "gt0"}, "supported"),
    ({"n": 40, "mean_diff": 0.05, "p_holm": 0.20, "rule": "gt0"}, "unsupported"),
    ({"n": 40, "mean_diff": -0.05, "p_holm": 0.001, "rule": "gt0"}, "unsupported"),
    ({"n": 10, "mean_diff": -0.01, "ci_low": -0.015, "ci_high": 0.0, "rule": "noninferior_0.02"}, "supported"),
    ({"n": 10, "mean_diff": 0.0, "ci_low": -0.02, "ci_high": 0.005, "rule": "equivalent_0.01"}, "unsupported"),
    ({"n": 0, "mean_diff": None, "rule": "gt0"}, "not yet evaluated"),
])
def test_verdict_rules(row, expected):
    assert verdict(row) == expected
