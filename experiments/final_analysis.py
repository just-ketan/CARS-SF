#!/usr/bin/env python3
"""
Final evaluation analysis — implements docs/thesis/final_evaluation_plan.md exactly.

    python experiments/aggregate.py && python experiments/final_analysis.py

Writes (results/tables/):
  final_summary.csv        per (study, condition, scheduler): mean ± 95 % CI of every metric
  final_claims.csv         C1–C11: paired n, mean difference, 95 % CI, rank-biserial r, Wilcoxon p,
                           Holm-adjusted p (primary family), decision rule and verdict
  final_requirements.csv   R1–R3 pass/fail with the counts behind them
Only current (non-stale) runs of the final_* studies and the resilience study are used.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.config import RESULTS_DIR  # noqa: E402

TABLES = RESULTS_DIR / "tables"
CONTENDED = ("final_contended_emergency", "final_contended_capacity", "final_contended_load",
             "final_contended_timelines")
QOS_SCHEDULERS = ("qos_blind", "qos_aware", "qos_reactive", "qos_adaptive", "rl_residual", "rl_residual_safe")
METRICS = ["mean_class_sla", "min_class_sla", "healthcare_sla_satisfied_share", "education_sla_satisfied_share",
           "agriculture_sla_satisfied_share", "general_sla_satisfied_share", "transient_mean_class_sla",
           "weighted_utility", "healthcare_loss_pct", "decisions_applied", "safety_rejections",
           "planned_violations", "enforcement_failed"]


def load() -> pd.DataFrame:
    runs = pd.read_csv(TABLES / "runs.csv")
    runs = runs[~runs["stale"]] if "stale" in runs else runs
    runs = runs[runs["study"].str.startswith("final_") | (runs["study"] == "resilience")].copy()
    runs.loc[runs["study"].isin(CONTENDED), "family"] = "final_contended"
    runs["family"] = runs["family"].fillna(runs["study"])
    return runs


def paired(df: pd.DataFrame, column: str, a: str, b: str, metric: str, keys=("condition", "seed")):
    A = df[df[column] == a].set_index(list(keys))[metric]
    B = df[df[column] == b].set_index(list(keys))[metric]
    pair = pd.concat([A, B], axis=1, keys=["a", "b"]).dropna()
    diff = (pair["a"] - pair["b"]).to_numpy(dtype=float)
    n = len(diff)
    if n < 3:
        return {"n": n, "mean_diff": None, "ci_low": None, "ci_high": None, "rank_biserial": None, "p": None}
    mean = diff.mean()
    half = stats.t.ppf(0.975, n - 1) * diff.std(ddof=1) / np.sqrt(n) if n > 1 else 0.0
    nonzero = diff[diff != 0]
    if len(nonzero):
        ranks = stats.rankdata(np.abs(nonzero))
        r = (ranks[nonzero > 0].sum() - ranks[nonzero < 0].sum()) / ranks.sum()
        p = float(stats.wilcoxon(nonzero).pvalue)
    else:
        r, p = 0.0, 1.0
    return {"n": n, "mean_diff": round(float(mean), 4), "ci_low": round(float(mean - half), 4),
            "ci_high": round(float(mean + half), 4), "rank_biserial": round(float(r), 3), "p": round(p, 6)}


def holm(pvalues: list[float]) -> list[float]:
    order = np.argsort(pvalues)
    m = len(pvalues)
    adjusted, running = [0.0] * m, 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[idx]))
        adjusted[idx] = running
    return adjusted


def claims(runs: pd.DataFrame) -> pd.DataFrame:
    cont = runs[runs["family"] == "final_contended"]
    informative = cont[cont["condition"].isin(["disaster", "medical_emergency", "disaster@1.5x",
                                               "rural_day", "medical_night"])]
    timelines = cont[cont["condition"].isin(["rural_day", "medical_night"])]
    pred = runs[runs["study"] == "final_prediction"]
    feas = runs[runs["study"] == "final_feasible"]
    sn = runs[runs["study"] == "final_slicenet"]
    online = runs[runs["study"].isin(["final_rl_online", "final_rl_online_nolearn"])]
    res = runs[runs["study"] == "resilience"].copy()
    if len(res):
        res["core_outage_s"] = res[["education_outage_s", "general_outage_s"]].max(axis=1)

    spec = [
        ("C1", "QoS-targeted allocation protects the critical class", cont, "scheduler", "qos_adaptive", "proposed",
         "healthcare_sla_satisfied_share", "gt0"),
        ("C2", "…without hurting the worst-off class", cont, "scheduler", "qos_adaptive", "proposed",
         "min_class_sla", "noninferior_0.01"),
        ("C3a", "Context helps where informative (critical class)", informative, "scheduler", "qos_aware",
         "qos_blind", "healthcare_sla_satisfied_share", "gt0"),
        ("C3b", "Context helps where informative (after changes)", timelines, "scheduler", "qos_aware",
         "qos_blind", "transient_mean_class_sla", "gt0"),
        ("C4", "Context is redundant where demand fits", feas, "scheduler", "qos_adaptive", "qos_blind",
         "mean_class_sla", "equivalent_0.01"),
        ("C5", "Reactive control helps after changes", pred, "scheduler", "qos_reactive", "qos_aware",
         "transient_mean_class_sla", "gt0"),
        ("C6a", "Prediction helps beyond reaction (after changes)", pred, "scheduler", "qos_adaptive",
         "qos_reactive", "transient_mean_class_sla", "gt0"),
        ("C6b", "Prediction helps beyond reaction (overall)", pred, "scheduler", "qos_adaptive", "qos_reactive",
         "mean_class_sla", "gt0"),
        ("C7", "RL improves on the heuristic", cont, "scheduler", "rl_residual", "qos_adaptive",
         "mean_class_sla", "gt0"),
        ("C8", "The safe RL hybrid improves on the heuristic", cont, "scheduler", "rl_residual_safe",
         "qos_adaptive", "mean_class_sla", "gt0"),
        ("C9", "Online learning helps", online, "scheduler", "rl_residual_online", "rl_residual_online_nolearn",
         "mean_class_sla", "gt0"),
        ("C10", "SliceNet on every flow is non-inferior", sn, "classification", "slicenet_all", "host",
         "mean_class_sla", "noninferior_0.02"),
        ("C11", "Self-healing reduces outage", res, "variant", "full", "no_healing", "core_outage_s", "lt0"),
    ]
    rows = []
    for cid, text, frame, column, a, b, metric, rule in spec:
        stat = paired(frame, column, a, b, metric) if len(frame) else {"n": 0}
        rows.append({"claim": cid, "statement": text, "comparison": f"{a} vs {b}", "metric": metric,
                     "rule": rule, **stat})
    df = pd.DataFrame(rows)
    primary = df["p"].notna() & df["rule"].isin(["gt0", "lt0"])
    df["p_holm"] = None
    if primary.any():
        df.loc[primary, "p_holm"] = [round(v, 6) for v in holm(df.loc[primary, "p"].astype(float).tolist())]
    df["verdict"] = [verdict(r) for _, r in df.iterrows()]
    return df


def verdict(r) -> str:
    if not r.get("n") or r.get("mean_diff") is None:
        return "not yet evaluated"
    if r["rule"] == "gt0":
        return "supported" if r["mean_diff"] > 0 and r["p_holm"] is not None and r["p_holm"] < 0.05 else "unsupported"
    if r["rule"] == "lt0":
        return "supported" if r["mean_diff"] < 0 and r["p_holm"] is not None and r["p_holm"] < 0.05 else "unsupported"
    margin = float(r["rule"].split("_")[1])
    if r["rule"].startswith("noninferior"):
        return "supported" if r["ci_low"] >= -margin else "unsupported"
    if r["rule"].startswith("equivalent"):
        return "supported" if r["ci_low"] >= -margin and r["ci_high"] <= margin else "unsupported"
    return "unsupported"


def requirements(runs: pd.DataFrame) -> pd.DataFrame:
    final = runs[runs["study"].str.startswith("final_")]
    feas = final[(final["study"] == "final_feasible") & (final["scheduler"] == "qos_adaptive")]
    feasible_runs = feas[feas["all_decisions_sla_feasible"] == True]  # noqa: E712
    shares = feasible_runs[[f"{s}_sla_satisfied_share" for s in
                            ("healthcare", "education", "agriculture", "general")]]
    r1_fail = int((shares < 0.95).any(axis=1).sum())
    contended_qos = final[final["study"].isin(CONTENDED) & final["scheduler"].isin(QOS_SCHEDULERS)]
    rows = [
        {"requirement": "R1", "text": "All four classes ≥ 0.95 SLA share in verified-feasible runs (qos_adaptive)",
         "runs_checked": int(len(feasible_runs)), "runs_not_verified_feasible": int(len(feas) - len(feasible_runs)),
         "failures": r1_fail, "pass": bool(len(feasible_runs) > 0 and r1_fail == 0)},
        {"requirement": "R2", "text": "0 failed verifications, 0 planned invariant violations, 0 validator rejections",
         "runs_checked": int(len(final)),
         "failures": int((final["enforcement_failed"].fillna(0) > 0).sum() + (final["planned_violations"].fillna(0) > 0).sum()
                         + (final["safety_rejections"].fillna(0) > 0).sum()),
         "pass": bool(((final["enforcement_failed"].fillna(0) == 0) & (final["planned_violations"].fillna(0) == 0)
                       & (final["safety_rejections"].fillna(0) == 0)).all())},
        {"requirement": "R3", "text": "No starvation in contended runs of the QoS-targeted schedulers",
         "runs_checked": int(len(contended_qos)), "failures": int(contended_qos["starvation"].fillna(False).sum()),
         "pass": bool(len(contended_qos) > 0 and not contended_qos["starvation"].fillna(False).any())},
    ]
    return pd.DataFrame(rows)


def summary(runs: pd.DataFrame) -> pd.DataFrame:
    out = []
    keys = ["study", "condition", "scheduler", "classification", "variant"]
    for key, group in runs.groupby(keys, dropna=False):
        row = dict(zip(keys, key))
        row["n"] = len(group)
        for metric in METRICS:
            if metric not in group:
                continue
            v = group[metric].dropna().astype(float)
            if v.empty:
                continue
            half = stats.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0.0
            row[f"{metric}_mean"], row[f"{metric}_ci95"] = round(v.mean(), 4), round(half, 4)
        out.append(row)
    return pd.DataFrame(out)


def main():
    runs = load()
    if runs.empty:
        raise SystemExit("no current final_* runs")
    TABLES.mkdir(parents=True, exist_ok=True)
    summary(runs).to_csv(TABLES / "final_summary.csv", index=False)
    c = claims(runs)
    c.to_csv(TABLES / "final_claims.csv", index=False)
    r = requirements(runs)
    r.to_csv(TABLES / "final_requirements.csv", index=False)
    pd.set_option("display.width", 220)
    print(c[["claim", "comparison", "metric", "n", "mean_diff", "ci_low", "ci_high", "rank_biserial", "p", "p_holm",
             "verdict"]].to_string(index=False))
    print(r.to_string(index=False))


if __name__ == "__main__":
    main()
