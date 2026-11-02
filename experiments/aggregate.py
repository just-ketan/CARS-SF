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
        row["online_final_accuracy"] = online.get("final_accuracy")
        row["online_time_to_decision_s"] = online.get("median_time_to_decision_s")
        row["online_flows"] = online.get("flows_classified")
        row["controller_reactions"] = len(summary.get("controller_reactions") or [])
        shares = [row.get(f"{s}_sla_satisfied_share") for s in SERVICES]
        shares = [v for v in shares if v is not None]
        row["mean_class_sla"] = round(float(np.mean(shares)), 4) if shares else None
        row["min_class_sla"] = round(float(np.min(shares)), 4) if shares else None
        row["condition"] = _condition(row, params)
        row["switch"] = summary.get("switch")
        row.update(_transient_sla(run_dir, summary))
        row.update(_safety_evidence(summary))
        row["starvation"] = _starved(row)
        row.update(_mixed_ue_metrics(run_dir))
        rows.append(row)
    return pd.DataFrame(rows)


def _condition(row: dict, params: dict) -> str:
    """Scenario plus any non-default capacity / load, e.g. school@50Mbps or disaster@1.5x."""
    label = str(row.get("scenario"))
    if params.get("topo_bottleneck_mbps") not in (None, 100):
        label += f"@{params['topo_bottleneck_mbps']}Mbps"
    if params.get("load_scale") not in (None, 1.0):
        label += f"@{params['load_scale']}x"
    return label


def _transient_sla(run_dir, summary) -> dict:
    """Mean per-class SLA-met share in the flow windows overlapping 10 s after each context change."""
    changes = [c["tick"] for c in summary.get("context_history") or []
               if (c.get("changed") or c.get("load_changed")) and c["tick"] > 0]
    # The summary's context history lists context changes only; load changes of a workload
    # timeline (load_scale events) are read from the timeline definition the run used.
    if summary.get("timeline"):
        from core.config import load_yaml
        events = (load_yaml("timelines.yaml").get("timelines", {}).get(summary["timeline"]) or {}).get("events", [])
        changes += [e["tick"] for e in events if "load_scale" in e and 0 < e["tick"] <= summary.get("duration", 10**6)]
        changes = sorted(set(changes))
    path = run_dir / "dataset.csv"
    if not changes or not path.exists():
        return {}
    df = pd.read_csv(path, usecols=lambda c: c in {"service_class", "sla_satisfied", "window_index"})
    keep = set()
    for tick in changes:
        keep.update(range(int(tick // 5), int((tick + 10 - 1e-6) // 5) + 1))
    part = df[df["window_index"].isin(keep)]
    if part.empty:
        return {}
    per_class = part.groupby("service_class")["sla_satisfied"].apply(lambda v: v.astype(bool).mean())
    return {"transient_mean_class_sla": round(float(per_class.mean()), 4),
            "transient_min_class_sla": round(float(per_class.min()), 4)}


def _safety_evidence(summary) -> dict:
    """Safety invariants and planning regimes, recomputed from the run's controller history."""
    from slicing.safety import validate

    history = summary.get("controller_history") or []
    capacity = float(summary.get("capacity_mbps") or 100.0)
    planned_violations = 0
    regimes = []
    for h in history:
        if h.get("directional_allocation"):
            planned_violations += bool(validate(h["directional_allocation"], capacity, h.get("protected")))
        feas = h.get("feasibility") or {}
        if feas:
            regimes.append(all(v.get("regime") == "sla_feasible" for v in feas.values()))
    return {
        "safety_rejections": sum(1 for h in history if (h.get("safety") or {}).get("accepted") is False),
        "planned_violations": planned_violations,
        "all_decisions_sla_feasible": (all(regimes) if regimes else None),
        "overload_decisions": sum(1 for h in history
                                  if any(v.get("regime") == "overload" for v in (h.get("feasibility") or {}).values())),
        "learned_accepted": sum(1 for h in history if (h.get("learned_proposal") or {}).get("accepted") is True),
        "learned_rejected": sum(1 for h in history if (h.get("learned_proposal") or {}).get("accepted") is False),
    }


def _starved(row) -> bool | None:
    """An active class with SLA share < 0.1 while another class in the same direction has ≥ 0.9."""
    pairs = (("healthcare", "agriculture"), ("education", "general"))   # uplink / downlink services
    shares = {s: row.get(f"{s}_sla_satisfied_share") for s in SERVICES}
    if all(v is None for v in shares.values()):
        return None
    for a, b in pairs:
        va, vb = shares.get(a), shares.get(b)
        if va is not None and vb is not None and ((va < 0.1 and vb >= 0.9) or (vb < 0.1 and va >= 0.9)):
            return True
    return False


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
                 metrics: list[str] = MAIN_METRICS, pair_keys: tuple = ("scenario", "seed")) -> pd.DataFrame:
    rows = []
    ref = df[df[column] == reference].set_index(list(pair_keys))
    for other in sorted(set(df[column].dropna()) - {reference}):
        cmp = df[df[column] == other].set_index(list(pair_keys))
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


QOS_STUDIES = ("qos_emergency", "qos_capacity", "qos_load", "qos_transitions")
QOS_METRICS = ["mean_class_sla", "min_class_sla", "healthcare_sla_satisfied_share", "education_sla_satisfied_share",
               "agriculture_sla_satisfied_share", "general_sla_satisfied_share", "healthcare_loss_pct",
               "weighted_utility", "decisions_applied", "transient_mean_class_sla"]

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
    "qos_emergency": ["condition", "scheduler"],
    "qos_capacity": ["condition", "scheduler"],
    "qos_load": ["condition", "scheduler"],
    "qos_transitions": ["condition", "scheduler"],
    "qos_slicenet": ["condition", "classification"],
    "qos_online": ["condition"],
}


def main():
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df = load_runs()
    if df.empty:
        raise SystemExit("no runs found")
    df.to_csv(TABLES_DIR / "runs.csv", index=False)
    all_runs = df
    # Summaries and tests use only runs made with the current code and models; stale
    # runs stay listed in runs.csv (column `stale`) but never mix into a comparison.
    df = df[~df["stale"]] if "stale" in df else df
    stale = all_runs[all_runs["stale"] & all_runs["study"].isin(GROUP_KEYS)]
    if not stale.empty:
        print(f"WARNING: {len(stale)} matrix runs were made with other code/models "
              f"(see the 'stale' column); they are excluded from all tables — re-run them with run_matrix.py --rerun-stale")
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
    qos = df[df["study"].isin(QOS_STUDIES)]
    if not qos.empty:
        summarise(qos, ["condition", "scheduler"]).to_csv(TABLES_DIR / "qos_summary.csv", index=False)
        paired_tests(qos, reference="qos_adaptive", metrics=QOS_METRICS,
                     pair_keys=("condition", "seed")).to_csv(TABLES_DIR / "qos_stats.csv", index=False)
    qsn = df[df["study"] == "qos_slicenet"]
    if not qsn.empty:
        paired_tests(qsn, reference="host", column="classification", metrics=QOS_METRICS[:6],
                     pair_keys=("condition", "seed")).to_csv(TABLES_DIR / "qos_slicenet_stats.csv", index=False)
    resilience = df[df["study"] == "resilience"]
    if not resilience.empty:
        paired_tests(resilience, reference="full", column="variant", metrics=RESILIENCE_METRICS).to_csv(
            TABLES_DIR / "resilience_stats.csv", index=False)
        main_runs.groupby("scheduler")[HEADLINE].mean().round(4).to_csv(TABLES_DIR / "main_by_scheduler.csv")


if __name__ == "__main__":
    main()
