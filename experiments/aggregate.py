#!/usr/bin/env python3
"""
Aggregate matrix runs into thesis tables.

    python experiments/aggregate.py

Outputs (results/tables/):
  runs.csv                one row per run with headline and per-slice metrics
  <study>_summary.csv     mean, std, n and 95 % CI per configuration
  main_stats.csv          paired Wilcoxon signed-rank tests, proposed vs each
                          baseline, paired by (scenario, seed)
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from core.config import RESULTS_DIR  # noqa: E402

TABLES_DIR = RESULTS_DIR / "tables"
SERVICES = ("healthcare", "education", "agriculture", "general")
HEADLINE = ["weighted_utility", "fairness_satisfaction", "mean_reward"]


def _current_fingerprints():
    from core.provenance import code_fingerprint, model_fingerprint
    return code_fingerprint(), model_fingerprint()


CURRENT = _current_fingerprints()


def load_runs() -> pd.DataFrame:
    rows = []
    for run_dir in sorted((RESULTS_DIR / "runs").iterdir()):
        summary_path, meta_path = run_dir / "summary.json", run_dir / "run_meta.json"
        if not summary_path.exists():
            continue
        summary = json.loads(summary_path.read_text())
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        params = meta.get("params", {})
        row = {
            "run_id": summary["run_id"],
            "study": params.get("study", summary["run_id"].split("__")[0]),
            "variant": params.get("variant"),
            "scenario": summary.get("timeline") or summary.get("scenario_id"),
            "scheduler": summary.get("scheduler"),
            "seed": summary.get("seed"),
            "classification": summary.get("classification"),
            "load_scale": summary.get("load_scale"),
            "capacity_mbps": summary.get("capacity_mbps"),
            "ues_per_service": summary.get("ues_per_service"),
            "data_source": summary.get("data_source"),
            "records": summary.get("record_count"),
            "validation_score": (summary.get("validation_report") or {}).get("total_score"),
            "policy_fallback_to_rule": summary.get("policy_fallback_to_rule"),
            "code_fingerprint": meta.get("code_fingerprint"),
            "model_fingerprint": meta.get("model_fingerprint"),
            "stale": (meta.get("code_fingerprint"), meta.get("model_fingerprint")) != CURRENT,
        }
        enforcement = summary.get("enforcement_summary") or {}
        row["decisions_applied"] = enforcement.get("decisions_applied")
        row["enforcement_failed"] = enforcement.get("failed")
        transitions = summary.get("rl_transitions") or {}
        row["rl_transitions"] = transitions.get("transitions")
        row["rl_transition_mean_reward"] = transitions.get("mean_reward")
        healing = summary.get("resilience") or {}
        verifications = healing.get("verifications") or []
        row["recovery_verified"] = sum(bool(v.get("verified")) for v in verifications)
        row["recovery_unverified"] = sum(not v.get("verified") for v in verifications)
        row["recovery_escalations"] = len(healing.get("escalations") or [])
        row["time_to_restore_s"] = healing.get("time_to_restore_s")
        kpis = recompute_kpis(run_dir, summary)
        if kpis is not None:
            summary["slice_kpis"], summary["weighted_utility"], summary["fairness_satisfaction"] = kpis
        for key in HEADLINE:
            row[key] = summary.get(key)
        for service, kpi in (summary.get("slice_kpis") or {}).items():
            for metric in ("latency_p95_ms", "latency_p99_ms", "loss_pct", "jitter_ms",
                           "demand_satisfaction", "sla_satisfied_share"):
                row[f"{service}_{metric}"] = kpi.get(metric)
        for service, mon in (summary.get("slice_sla_monitor") or {}).items():
            row[f"{service}_sla_compliance"] = mon.get("sla_compliance")
        res = summary.get("resilience") or {}
        for key in ("mttd_s", "mttr_control_s", "proactive", "switched_before_cut",
                    "fail_back_delay_s", "diagnosed_core_switch_failure"):
            row[f"res_{key}"] = res.get(key)
        for service, out in (res.get("outage") or {}).items():
            row[f"{service}_outage_s"] = out.get("outage_s")
            row[f"{service}_failover_lost"] = out.get("lost_packets")
        online = summary.get("online_classification") or {}
        row["online_accuracy"] = online.get("accuracy")
        row.update(_mixed_ue_metrics(run_dir))
        rows.append(row)
    return pd.DataFrame(rows)


def recompute_kpis(run_dir, summary):
    """Per-slice KPIs from the run's own measured dataset and per-tick design demand.

    Recomputed here (not read from summary.json) so that a fix to the KPI
    definition applies uniformly to every stored run without re-running it.
    """
    from analysis.metrics import jain_fairness, slice_kpis, weighted_utility
    from slicing.context_engine import ContextEngine

    dataset, feedback = run_dir / "dataset.csv", run_dir / "feedback.csv"
    if not dataset.exists() or not feedback.exists() or summary.get("data_source") != "pcap":
        return None
    df = pd.read_csv(dataset, low_memory=False)
    fb = pd.read_csv(feedback)
    demand = {s: float(fb[f"{s}_demand_mbps"].mean()) for s in SERVICES if f"{s}_demand_mbps" in fb}
    kpis = slice_kpis(df, demand)
    history = summary.get("context_history") or []
    first = history[0]["context"] if history else summary.get("scenario_id", "normal")
    weights = ContextEngine().get_context(first)
    return kpis, weighted_utility(kpis, weights), jain_fairness(
        [k.get("demand_satisfaction") for k in kpis.values()]
    )


def _mixed_ue_metrics(run_dir) -> dict:
    path = run_dir / "dataset.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path, usecols=lambda c: c in {"ue_host", "service_class", "sla_satisfied", "p95_latency_ms"})
    mixed = df[df.get("ue_host", pd.Series(dtype=str)) == "h_mixed"] if "ue_host" in df else df.iloc[0:0]
    if mixed.empty:
        return {}
    out = {"mixed_sla_share": round(float(mixed["sla_satisfied"].astype(bool).mean()), 4)}
    for service, group in mixed.groupby("service_class"):
        out[f"mixed_{service}_sla_share"] = round(float(group["sla_satisfied"].astype(bool).mean()), 4)
        out[f"mixed_{service}_p95_ms"] = round(float(group["p95_latency_ms"].median()), 3)
    return out


def summarise(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    metrics = [c for c in df.columns if c not in keys and pd.api.types.is_numeric_dtype(df[c])
               and c not in ("seed", "records")]
    out = []
    for key, group in df.groupby(keys, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(keys, key))
        row["n"] = len(group)
        for metric in metrics:
            values = group[metric].dropna().astype(float)
            if values.empty:
                continue
            mean, std = values.mean(), values.std(ddof=1) if len(values) > 1 else 0.0
            half = stats.t.ppf(0.975, len(values) - 1) * std / np.sqrt(len(values)) if len(values) > 1 else 0.0
            row[f"{metric}_mean"] = round(mean, 4)
            row[f"{metric}_ci95"] = round(half, 4)
        out.append(row)
    return pd.DataFrame(out)


MAIN_METRICS = ["weighted_utility", "fairness_satisfaction", "healthcare_latency_p95_ms",
                "healthcare_demand_satisfaction", "healthcare_sla_satisfied_share", "mean_reward"]
RESILIENCE_METRICS = ["healthcare_outage_s", "education_outage_s", "general_outage_s",
                      "education_failover_lost", "general_failover_lost", "res_mttr_control_s",
                      "weighted_utility", "time_to_restore_s"]


def paired_tests(df: pd.DataFrame, reference: str = "proposed", column: str = "scheduler",
                 metrics: list[str] = MAIN_METRICS) -> pd.DataFrame:
    rows = []
    ref = df[df[column] == reference].set_index(["scenario", "seed"])
    for other in sorted(set(df[column].dropna()) - {reference}):
        cmp = df[df[column] == other].set_index(["scenario", "seed"])
        for metric in metrics:
            if metric not in df:
                continue
            pair = pd.concat([ref[metric], cmp[metric]], axis=1, keys=["ref", "other"]).dropna()
            if len(pair) < 5:
                continue
            diff = pair["ref"] - pair["other"]
            try:
                p = stats.wilcoxon(pair["ref"], pair["other"]).pvalue if (diff != 0).any() else 1.0
            except ValueError:
                p = float("nan")
            rows.append({
                "baseline": other, "metric": metric, "pairs": len(pair),
                "proposed_mean": round(pair["ref"].mean(), 4),
                "baseline_mean": round(pair["other"].mean(), 4),
                "mean_difference": round(diff.mean(), 4),
                "wilcoxon_p": round(float(p), 6),
                "significant_0.05": bool(p < 0.05),
            })
    result = pd.DataFrame(rows)
    if not result.empty:
        comparisons = len(result)
        result["bonferroni_alpha"] = round(0.05 / comparisons, 6)
        result["significant_bonferroni"] = result["wilcoxon_p"] < 0.05 / comparisons
    return result


GROUP_KEYS = {
    "main": ["scenario", "scheduler"],
    "ablation": ["scenario", "variant"],
    "sensitivity_capacity": ["scenario", "scheduler", "capacity_mbps"],
    "sensitivity_load": ["scenario", "scheduler", "load_scale"],
    "scalability": ["ues_per_service"],
    "resilience": ["scenario", "variant"],
    "timeline": ["scheduler"],
    "slicenet_inloop": ["scenario", "classification"],
    "online_rl": ["scenario"],
}


def main():
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df = load_runs()
    if df.empty:
        raise SystemExit("no runs found")
    df.to_csv(TABLES_DIR / "runs.csv", index=False)
    stale = df[df["stale"] & df["study"].isin(GROUP_KEYS)]
    if not stale.empty:
        print(f"WARNING: {len(stale)} matrix runs were made with other code/models "
              f"(see the 'stale' column); re-run them with run_matrix.py --rerun-stale")
    provenance = {
        study: sorted({f"{c}/{m}" for c, m in zip(part["code_fingerprint"], part["model_fingerprint"])})
        for study, part in df[df["study"].isin(GROUP_KEYS)].groupby("study")
    }
    (TABLES_DIR / "provenance.json").write_text(json.dumps(
        {"current": "/".join(CURRENT), "fingerprints_by_study": provenance}, indent=2, default=str))
    for study, keys in GROUP_KEYS.items():
        part = df[df["study"] == study]
        if part.empty:
            continue
        summarise(part, keys).to_csv(TABLES_DIR / f"{study}_summary.csv", index=False)
        print(f"{study}: {len(part)} runs")
    main_runs = df[df["study"] == "main"]
    if not main_runs.empty:
        paired_tests(main_runs).to_csv(TABLES_DIR / "main_stats.csv", index=False)
    resilience = df[df["study"] == "resilience"]
    if not resilience.empty:
        paired_tests(resilience, reference="full", column="variant", metrics=RESILIENCE_METRICS).to_csv(
            TABLES_DIR / "resilience_stats.csv", index=False)
        main_runs.groupby("scheduler")[HEADLINE].mean().round(4).to_csv(TABLES_DIR / "main_by_scheduler.csv")


if __name__ == "__main__":
    main()
