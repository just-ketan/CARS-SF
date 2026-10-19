#!/usr/bin/env python3
"""
Generate docs/thesis/results.md from aggregated results.

    python experiments/aggregate.py && python experiments/report.py

Each hypothesis from docs/thesis/research_design.md is evaluated mechanically
from the tables, so the verdicts cannot drift from the numbers.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from core.config import RESULTS_DIR  # noqa: E402

TABLES = RESULTS_DIR / "tables"
OUT = os.path.join(REPO_ROOT, "docs", "thesis", "results.md")
FIG = "../figures/thesis"
HIGH_LOAD = ["school", "disaster", "medical_emergency", "harvest"]


def load(name):
    path = TABLES / name
    return pd.read_csv(path) if path.exists() else None


def jload(name):
    path = RESULTS_DIR / name
    return json.loads(path.read_text()) if path.exists() else None


def fmt(mean, ci=None, digits=3):
    if mean is None or (isinstance(mean, float) and np.isnan(mean)):
        return "–"
    return f"{mean:.{digits}f}" + (f" ± {ci:.{digits}f}" if ci is not None and not np.isnan(ci) else "")


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def verdict(ok: bool | None) -> str:
    return {True: "**Supported**", False: "**Not supported**", None: "**Inconclusive**"}[ok]


def main_section(lines, verdicts):
    summary, stats = load("main_summary.csv"), load("main_stats.csv")
    if summary is None:
        return
    lines += ["## RQ1/RQ3 — Scheduler comparison (main study)", ""]
    pivot_rows = []
    for scheduler, group in summary.groupby("scheduler"):
        row = {"scheduler": scheduler}
        for metric, label in (("weighted_utility", "weighted utility"),
                              ("healthcare_latency_p95_ms", "healthcare p95 (ms)"),
                              ("healthcare_sla_satisfied_share", "healthcare SLA share"),
                              ("fairness_satisfaction", "Jain fairness")):
            if f"{metric}_mean" in group:
                row[label] = fmt(group[f"{metric}_mean"].mean(), None, 3)
        pivot_rows.append(row)
    lines += ["Mean across the five contexts (per-context values with 95 % CIs are in "
              "`results/tables/main_summary.csv`):", "", md_table(pd.DataFrame(pivot_rows)), ""]
    lines += [f"![weighted utility]({FIG}/main_weighted_utility.png)", "",
              f"![healthcare p95]({FIG}/main_healthcare_p95.png)", ""]
    if stats is not None and not stats.empty:
        show = stats[stats["metric"].isin(["weighted_utility", "healthcare_latency_p95_ms",
                                           "healthcare_sla_satisfied_share"])][
            ["baseline", "metric", "pairs", "proposed_mean", "baseline_mean", "mean_difference",
             "wilcoxon_p", "significant_0.05", "significant_bonferroni"]]
        lines += ["Paired Wilcoxon signed-rank tests, proposed vs each baseline, on (scenario, seed) pairs:", "",
                  md_table(show), ""]

        def better(baseline, metric, higher=True):
            row = stats[(stats["baseline"] == baseline) & (stats["metric"] == metric)]
            if row.empty:
                return None
            row = row.iloc[0]
            direction = row["mean_difference"] > 0 if higher else row["mean_difference"] < 0
            return bool(direction and row["significant_0.05"])

        h1a = [better(b, "weighted_utility") for b in ("tgpp", "static_equal", "no_slicing")]
        verdicts["H1a"] = (None if None in h1a else all(h1a),
                           "proposed vs tgpp / static_equal / no_slicing on weighted utility: "
                           + ", ".join(str(x) for x in h1a))
        hl = summary[summary["scenario"].isin(HIGH_LOAD)]
        h1b = []
        for baseline in ("tgpp", "no_slicing"):
            p = hl[hl["scheduler"] == "proposed"]["healthcare_latency_p95_ms_mean"].mean()
            b = hl[hl["scheduler"] == baseline]["healthcare_latency_p95_ms_mean"].mean()
            h1b.append(bool(p < b) if not (np.isnan(p) or np.isnan(b)) else None)
        sig = [better(b, "healthcare_latency_p95_ms", higher=False) for b in ("tgpp", "no_slicing")]
        verdicts["H1b"] = (None if None in h1b + sig else all(h1b) and all(sig),
                           f"high-load healthcare p95 lower than tgpp/no_slicing: {h1b}; significant: {sig}")
        exploratory = stats[(stats["metric"] == "healthcare_sla_satisfied_share")
                            & stats["significant_bonferroni"]]
        if not exploratory.empty:
            lines += ["**Exploratory finding (not a pre-registered hypothesis).** Differences in "
                      "healthcare SLA-met share that survive Bonferroni correction:", ""]
            for _, r in exploratory.iterrows():
                lines.append(f"* proposed vs {r['baseline']}: {r['proposed_mean']:.3f} vs "
                             f"{r['baseline_mean']:.3f} (Δ {r['mean_difference']:+.3f}, p = {r['wilcoxon_p']:.4f}, "
                             f"n = {r['pairs']} pairs)")
            lines.append("")
        # H3: does RL improve on the well-designed heuristic? (proposed − rl < 0 and significant)
        parts, any_better = [], []
        for policy in ("rl_ppo", "rl_cem"):
            row = stats[(stats["baseline"] == policy) & (stats["metric"] == "weighted_utility")]
            if row.empty:
                continue
            r = row.iloc[0]
            any_better.append(bool(r["mean_difference"] < 0 and r["significant_0.05"]))
            parts.append(f"proposed − {policy} = {r['mean_difference']:+.4f} (p = {r['wilcoxon_p']:.4f})")
        if parts:
            verdicts["H3"] = (any(any_better), "; ".join(parts))
        # H9: context awareness vs the same scheduler with the "normal" matrix throughout.
        rows = stats[stats["baseline"] == "context_unaware"]
        if not rows.empty:
            util = rows[rows["metric"] == "weighted_utility"].iloc[0]
            hc = rows[rows["metric"] == "healthcare_sla_satisfied_share"]
            hc_txt = (f"; healthcare SLA share Δ {hc.iloc[0]['mean_difference']:+.4f} "
                      f"(p = {hc.iloc[0]['wilcoxon_p']:.4f})") if not hc.empty else ""
            verdicts["H9"] = (bool(util["mean_difference"] > 0 and util["significant_0.05"]),
                              f"proposed − context_unaware weighted utility {util['mean_difference']:+.4f} "
                              f"(p = {util['wilcoxon_p']:.4f}, n = {util['pairs']}){hc_txt}")


def ablation_section(lines, verdicts):
    df = load("ablation_summary.csv")
    if df is None:
        return
    lines += ["## RQ2 — Ablation", ""]
    show = df[["scenario", "variant", "n", "weighted_utility_mean", "weighted_utility_ci95",
               "healthcare_latency_p95_ms_mean", "healthcare_latency_p95_ms_ci95"]].round(3)
    lines += [md_table(show), "", f"![ablation]({FIG}/ablation.png)", ""]
    effects = []
    for scenario, group in df.groupby("scenario"):
        full = group[group["variant"] == "full"].iloc[0]
        strict = group[group["variant"] == "full_strict"]
        for _, row in group.iterrows():
            ref = strict.iloc[0] if row["variant"] == "no_surplus_strict" and not strict.empty else full
            if row["variant"] in ("full", "full_strict", "oracle_demand"):
                continue
            worse = (row["weighted_utility_mean"] < ref["weighted_utility_mean"] - 1e-3) or (
                row["healthcare_latency_p95_ms_mean"] > ref["healthcare_latency_p95_ms_mean"] * 1.05)
            effects.append((scenario, row["variant"], bool(worse)))
    verdicts["H2"] = (sum(e[2] for e in effects) >= len(effects) / 2 if effects else None,
                      "; ".join(f"{s}/{v}: {'worse' if w else 'no loss'}" for s, v, w in effects))


def sensitivity_section(lines, verdicts):
    out = []
    for study, xcol in (("sensitivity_capacity", "capacity_mbps"), ("sensitivity_load", "load_scale")):
        df = load(f"{study}_summary.csv")
        if df is None:
            continue
        lines += [f"## RQ7 — {study.replace('_', ' ').title()}", ""]
        show = df[["scenario", "scheduler", xcol, "weighted_utility_mean", "weighted_utility_ci95"]].round(3)
        lines += [md_table(show), "", f"![{study}]({FIG}/{study}.png)", ""]
        for (scenario, x), group in df.groupby(["scenario", xcol]):
            p = group[group["scheduler"] == "proposed"]["weighted_utility_mean"]
            s = group[group["scheduler"] == "static_equal"]["weighted_utility_mean"]
            if len(p) and len(s):
                out.append(bool(p.iloc[0] >= s.iloc[0]))
    scal = load("scalability_summary.csv")
    if scal is not None:
        lines += ["## Scalability (UEs per service)", "",
                  md_table(scal[["ues_per_service", "n", "weighted_utility_mean", "weighted_utility_ci95",
                                 "healthcare_latency_p95_ms_mean"]].round(3)), ""]
    if out:
        verdicts["H7"] = (all(out), f"proposed ≥ static_equal in {sum(out)}/{len(out)} capacity/load settings")


def resilience_section(lines, verdicts):
    df = load("resilience_summary.csv")
    if df is None:
        return
    lines += ["## RQ4 — Resilience", ""]
    cols = [c for c in ["scenario", "variant", "n", "res_mttd_s_mean", "res_mttr_control_s_mean",
                        "education_outage_s_mean", "general_outage_s_mean", "general_failover_lost_mean",
                        "weighted_utility_mean"] if c in df.columns]
    lines += [md_table(df[cols].round(3)), "",
              f"![outage]({FIG}/resilience_outage_general.png)", ""]
    runs = load("runs.csv")
    if runs is not None:
        res = runs[runs["study"] == "resilience"]
        cut = res[(res["scenario"] == "fiber_cut") & (res["variant"] == "full")]
        outage = cut[["education_outage_s", "general_outage_s"]].max(axis=1)
        verdicts["H4a"] = (bool((outage < 1.0).all()) if len(outage) else None,
                           f"fiber cut, full healing: max outage per run {outage.round(3).tolist()} s")
        deg = res[res["scenario"] == "backhaul_degradation"]
        full = deg[deg["variant"] == "full"]
        reactive = deg[deg["variant"] == "reactive_only"]
        if len(full) and len(reactive):
            before = full["res_switched_before_cut"].astype(bool).mean()
            f_out = full[["education_outage_s", "general_outage_s"]].max(axis=1).mean()
            r_out = reactive[["education_outage_s", "general_outage_s"]].max(axis=1).mean()
            verdicts["H4b"] = (bool(before >= 0.5 and f_out <= r_out),
                               f"switched before cut in {before:.0%} of runs; mean outage predictive "
                               f"{f_out:.3f} s vs reactive {r_out:.3f} s")
        full_all = res[res["variant"] == "full"]
        if "recovery_verified" in full_all:
            lines += [f"Post-recovery verification (full healing): {int(full_all['recovery_verified'].sum())} "
                      f"recoveries verified, {int(full_all['recovery_unverified'].sum())} unverified, "
                      f"{int(full_all['recovery_escalations'].sum())} escalations across {len(full_all)} runs; "
                      f"median time to verified restore "
                      f"{full_all['time_to_restore_s'].median():.3f} s.", ""]
    stats = load("resilience_stats.csv")
    if stats is not None and not stats.empty:
        nh = stats[stats["baseline"] == "no_healing"]
        lines += ["Paired tests, full healing vs each variant on (scenario, seed) pairs "
                  "(negative difference = full healing lower):", "",
                  md_table(stats[["baseline", "metric", "pairs", "proposed_mean", "baseline_mean",
                                  "mean_difference", "wilcoxon_p"]].rename(columns={"proposed_mean": "full_mean"})), ""]
        out = nh[nh["metric"].isin(["education_outage_s", "general_outage_s"])]
        if not out.empty:
            verdicts["H10"] = (bool((out["mean_difference"] < 0).all() and (out["wilcoxon_p"] < 0.05).all()),
                               "full − no_healing outage: " + "; ".join(
                                   f"{r['metric']} {r['mean_difference']:+.3f} s (p = {r['wilcoxon_p']:.4f})"
                                   for _, r in out.iterrows()))


def slicenet_section(lines, verdicts):
    metrics, transfer = jload("slicenet_mininet_metrics.json"), jload("slicenet_transfer.json")
    if metrics:
        lines += ["## RQ5/RQ6 — SliceNet", ""]
        rows = []
        for key in ("random_forest", "cnn_1d"):
            if key in metrics:
                m = metrics[key]
                rows.append({"model": key, "macro F1": round(m["f1_macro"], 4), "accuracy": round(m["accuracy"], 4),
                             "test windows": m["test_size"],
                             **{c: round(m["report"][c]["f1-score"], 3) for c in ("healthcare", "education", "agriculture", "general")}})
        lines += [f"Measured dataset: {metrics.get('rows')} flow windows from {metrics.get('runs')} runs; "
                  f"evaluation holds out whole run × UE groups.", "", md_table(pd.DataFrame(rows)), "",
                  f"![confusion]({FIG}/slicenet_confusion_random_forest.png)", ""]
        best = max(m["f1_macro"] for k, m in metrics.items() if isinstance(m, dict) and "f1_macro" in m)
        verdicts["H5a"] = (best >= 0.9, f"best held-out macro F1 = {best:.4f}")
    if transfer:
        lines += [md_table(pd.DataFrame(transfer["curve"])), "",
                  f"Measured-only (same shared columns): macro F1 {transfer['mininet_only_f1_macro']}.", "",
                  f"![transfer]({FIG}/slicenet_transfer.png)", ""]
        zero = transfer["curve"][0]["f1_macro"]
        recovered = transfer["curve"][-1]["f1_macro"]
        verdicts["H6"] = (zero < 0.4 and recovered > zero + 0.3,
                          f"zero-shot F1 {zero}, with {transfer['curve'][-1]['mininet_fraction']:.0%} measured groups {recovered}")
    inloop = load("slicenet_inloop_summary.csv")
    if inloop is not None and "mixed_sla_share_mean" in inloop:
        cols = [c for c in ["scenario", "classification", "n", "mixed_sla_share_mean", "mixed_sla_share_ci95",
                            "online_accuracy_mean", "mixed_healthcare_sla_share_mean"] if c in inloop.columns]
        lines += ["### In-loop slicing of a mixed-service UE", "", md_table(inloop[cols].round(3)), "",
                  f"![in-loop]({FIG}/slicenet_inloop.png)", ""]
        wins = []
        for scenario, group in inloop.groupby("scenario"):
            h = group[group["classification"] == "host"]["mixed_sla_share_mean"]
            s = group[group["classification"] == "slicenet"]["mixed_sla_share_mean"]
            if len(h) and len(s):
                wins.append(bool(s.iloc[0] > h.iloc[0]))
        verdicts["H5b"] = (all(wins) if wins else None, f"SliceNet > host-based in {sum(wins)}/{len(wins)} scenarios")


def rl_section(lines, verdicts):
    rl = jload("rl_training.json")
    if not rl:
        return
    comp = rl.get("evaluation") or rl.get("sequential_env_comparison", {})
    rows = [{"policy": k, **{m: v[m] for m in ("mean_reward", "std_reward", "sla_violations_per_episode",
                                                 "mean_satisfaction") if m in v}}
            for k, v in comp.items() if k in ("rule_based", "rl_cem", "rl_ppo")]
    lines += ["## Learning engine on the sequential environment (simulation)", "",
              "Held-out evaluation seeds (disjoint from training and validation seeds), "
              "30 episodes × 120 steps, shared reward:", "", md_table(pd.DataFrame(rows)), ""]
    paired = comp.get("paired_vs_rule_based") or {}
    if paired:
        lines += ["Paired over the same episodes (policy − rule-based):", "",
                  md_table(pd.DataFrame([{"policy": k, **v} for k, v in paired.items()])), ""]
    ppo = rl.get("ppo") or {}
    if ppo:
        lines += [f"PPO seeds {ppo['seeds']}: test reward {ppo['test_reward_mean']} ± {ppo['test_reward_std']} "
                  f"(per seed {ppo['test_reward_per_seed']}); deployed seed {ppo['deployed_seed']} "
                  f"(best validation score).", ""]
    lines += [f"![rl]({FIG}/rl_policies.png)", ""]


def online_rl_section(lines, verdicts):
    runs = load("runs.csv")
    if runs is None:
        return
    online = runs[runs["study"] == "online_rl"].sort_values(["scenario", "seed"])
    if online.empty:
        return
    lines += ["## Mininet online learning (online CEM, consecutive live runs)", "",
              "Exploratory: the policy starts from the simulator-trained CEM policy and updates only from "
              "live transitions whose allocation was verified in the kernel. Runs are sequential, so the "
              "trend mixes learning with seed effects.", "",
              md_table(online[["scenario", "seed", "rl_transitions", "rl_transition_mean_reward",
                               "weighted_utility", "enforcement_failed"]].round(3)), ""]


def g5_section(lines, verdicts):
    path = RESULTS_DIR / "5g"
    if not path.exists():
        return
    rows = []
    for f in sorted(path.glob("5g__*.json")):
        r = json.loads(f.read_text())
        hc = r["slice_kpis"].get("healthcare", {})
        ag = r["slice_kpis"].get("agriculture", {})
        rows.append({"scenario": r["scenario"], "mode": r["mode"], "seed": r["run_id"].split("__s")[-1],
                     "healthcare p95": hc.get("latency_p95_ms"), "healthcare SLA": hc.get("sla_satisfied_share"),
                     "agriculture p95": ag.get("latency_p95_ms"), "weighted utility": r.get("weighted_utility")})
    if not rows:
        return
    df = pd.DataFrame(rows)
    lines += ["## RQ8 — Real 5G core (Open5GS + UERANSIM, 10 Mbps UPF bottleneck)", "", md_table(df), ""]
    agg = df.groupby(["scenario", "mode"])["healthcare p95"].mean().unstack()
    if {"cars_sf", "no_slicing"} <= set(agg.columns):
        ok = bool((agg["cars_sf"] < agg["no_slicing"]).all())
        verdicts["H8"] = (ok, "mean healthcare p95 by scenario: " + "; ".join(
            f"{s}: {row['cars_sf']:.1f} vs {row['no_slicing']:.1f} ms" for s, row in agg.iterrows()))


def main():
    lines = ["# Results", "",
             "Generated by `experiments/report.py` from `results/tables/` (see "
             "[research_design.md](research_design.md) for the hypotheses and method). "
             "Every number is measured on the emulated network unless stated otherwise.", ""]
    verdicts: dict[str, tuple] = {}
    for section in (main_section, ablation_section, sensitivity_section, resilience_section,
                    slicenet_section, rl_section, online_rl_section, g5_section):
        section(lines, verdicts)
    runs = load("runs.csv")
    header = ["## Hypotheses", ""]
    if runs is not None:
        from experiments.aggregate import GROUP_KEYS
        runs = runs[runs["study"].isin(GROUP_KEYS)]      # matrix studies only (not collection or ad-hoc runs)
        per_study = ", ".join(f"{study} {n}" for study, n in runs["study"].value_counts().items())
        header += [f"{len(runs)} runs ({per_study}); {int((runs['data_source'] == 'pcap').sum())} with "
                   f"packet-level measurements; median validation score "
                   f"{runs['validation_score'].median():.0f}/100.", ""]
    header += ["| Hypothesis | Verdict | Evidence |", "|---|---|---|"]
    for key in ("H1a", "H1b", "H2", "H3", "H4a", "H4b", "H5a", "H5b", "H6", "H7", "H8", "H9", "H10"):
        if key in verdicts:
            ok, evidence = verdicts[key]
            header.append(f"| {key} | {verdict(ok)} | {evidence} |")
        else:
            header.append(f"| {key} | **Not evaluated** | data missing |")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines[:4] + header + [""] + lines[4:]) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
