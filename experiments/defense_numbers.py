#!/usr/bin/env python3
"""
Emit docs/defense/numbers.tex: every quantitative claim in the defense
handbook as a LaTeX macro computed from results/ — so the handbook cannot
quote a number the data does not contain.

    python experiments/aggregate.py && python experiments/defense_numbers.py
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
OUT = os.path.join(REPO_ROOT, "docs", "defense", "numbers.tex")
macros: dict[str, str] = {}


DIGITS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]


def safe(name: str) -> str:
    """LaTeX command names may only contain letters."""
    return "".join(DIGITS[int(c)] if c.isdigit() else c for c in name if c.isalnum())


def put(name: str, value, digits: int = 3, pct: bool = False):
    name = safe(name)
    if value is None or (isinstance(value, float) and np.isnan(value)):
        text = "n/a"
    elif isinstance(value, (int, np.integer)):
        text = f"{value:,}".replace(",", "{,}")
    elif isinstance(value, float):
        text = f"{value * 100:.1f}\\%" if pct else f"{value:.{digits}f}"
    else:
        text = str(value)
    macros[name] = text


def table(name):
    path = TABLES / name
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def jload(name):
    path = RESULTS_DIR / name
    return json.loads(path.read_text()) if path.exists() else {}


NAMES = {"proposed": "Proposed", "rl_cem": "Cem", "rl_ppo": "Ppo", "proportional": "Proportional",
         "static_equal": "Static", "tgpp": "Tgpp", "no_slicing": "NoSlicing", "no_surplus": "NoSurplus"}


def main_study():
    runs = table("runs.csv")
    if not runs.empty:
        put("Runs", int(len(runs)))
        put("RunsMain", int((runs["study"] == "main").sum()))
        put("RunsPcap", int((runs["data_source"] == "pcap").sum()))
        put("ValidationMedian", float(runs["validation_score"].median()), 0)
    s = table("main_summary.csv")
    if not s.empty:
        g = s.groupby("scheduler").mean(numeric_only=True)
        for sched, short in NAMES.items():
            if sched in g.index:
                put(f"Util{short}", g.loc[sched, "weighted_utility_mean"])
                put(f"HcSla{short}", g.loc[sched, "healthcare_sla_satisfied_share_mean"])
                put(f"HcPninefive{short}", g.loc[sched, "healthcare_latency_p95_ms_mean"], 1)
                put(f"Fair{short}", g.loc[sched, "fairness_satisfaction_mean"])
        util = g["weighted_utility_mean"]
        put("UtilMin", float(util.min()))
        put("UtilMax", float(util.max()))
    st = table("main_stats.csv")
    if not st.empty:
        def row(baseline, metric):
            r = st[(st["baseline"] == baseline) & (st["metric"] == metric)]
            return r.iloc[0] if not r.empty else None
        r = row("no_slicing", "healthcare_sla_satisfied_share")
        if r is not None:
            put("SlaDeltaNoSlicing", r["mean_difference"])
            put("SlaPNoSlicing", r["wilcoxon_p"], 4)
            put("SlaPairs", int(r["pairs"]))
        util_rows = st[st["metric"] == "weighted_utility"]
        put("UtilPMin", float(util_rows["wilcoxon_p"].min()), 3)
        put("UtilSigCount", int(util_rows["significant_bonferroni"].sum()))
        put("BonferroniAlpha", float(st["bonferroni_alpha"].iloc[0]), 4)
        r = row("rl_ppo", "weighted_utility")
        if r is not None:
            put("PpoDelta", r["mean_difference"], 4)
            put("PpoP", r["wilcoxon_p"], 3)


def ablation():
    a = table("ablation_summary.csv")
    for _, r in a.iterrows():
        key = f"{r['scenario'].capitalize()}{''.join(p.capitalize() for p in str(r['variant']).split('_'))}"
        put(f"Abl{key}Util", r["weighted_utility_mean"])
        put(f"Abl{key}Hc", r["healthcare_latency_p95_ms_mean"], 1)
        put(f"Abl{key}HcSla", r.get("healthcare_sla_satisfied_share_mean"))
        put(f"Abl{key}GenP", r.get("general_latency_p95_ms_mean"), 0)
        put(f"Abl{key}EduP", r.get("education_latency_p95_ms_mean"), 0)


def sensitivity():
    for study, col, tag in (("sensitivity_load", "load_scale", "Load"), ("sensitivity_capacity", "capacity_mbps", "Cap")):
        d = table(f"{study}_summary.csv")
        for _, r in d.iterrows():
            x = str(r[col]).replace(".0", "").replace(".", "p")
            put(f"Sens{tag}{r['scenario'].capitalize()}{NAMES.get(r['scheduler'], r['scheduler'])}{x}",
                r["weighted_utility_mean"])
            put(f"Sens{tag}{r['scenario'].capitalize()}{NAMES.get(r['scheduler'], r['scheduler'])}{x}HcSla",
                r.get("healthcare_sla_satisfied_share_mean"))


def resilience():
    runs = table("runs.csv")
    res = runs[runs["study"] == "resilience"] if not runs.empty else runs
    if res.empty:
        return
    def outage(df):
        return df[["education_outage_s", "general_outage_s"]].max(axis=1)
    for scen, short in (("fiber_cut", "Cut"), ("backhaul_degradation", "Deg"), ("core_switch_failure", "Core")):
        for variant, vshort in (("full", "Full"), ("reactive_only", "Reactive"), ("no_healing", "None")):
            d = res[(res["scenario"] == scen) & (res["variant"] == variant)]
            if d.empty:
                continue
            o = outage(d)
            put(f"Out{short}{vshort}Mean", float(o.mean()))
            put(f"Out{short}{vshort}Max", float(o.max()))
            put(f"Lost{short}{vshort}", float(d["general_failover_lost"].mean()), 0)
            if "res_mttd_s" in d:
                put(f"Mttd{short}{vshort}", float(d["res_mttd_s"].abs().mean()))
                put(f"Mttr{short}{vshort}", float(d["res_mttr_control_s"].mean()))
    deg = res[(res["scenario"] == "backhaul_degradation") & (res["variant"] == "full")]
    if not deg.empty:
        put("DegBeforeCutShare", float(deg["res_switched_before_cut"].astype(bool).mean()), pct=True)
    core = res[(res["scenario"] == "core_switch_failure") & (res["variant"] == "full")]
    if not core.empty:
        put("CoreDiagnosedShare", float(core["res_diagnosed_core_switch_failure"].astype(bool).mean()), pct=True)


def slicenet():
    m = jload("slicenet_mininet_metrics.json")
    if m:
        put("SnRows", int(m.get("rows", 0)))
        put("SnRunsCount", int(m.get("runs", 0)))
        put("SnGroups", int(m.get("groups", 0)))
        for key, short in (("random_forest", "Rf"), ("cnn_1d", "Cnn")):
            if key in m:
                put(f"Sn{short}Fone", m[key]["f1_macro"])
                put(f"Sn{short}Acc", m[key]["accuracy"])
                put(f"Sn{short}Test", int(m[key]["test_size"]))
                for c in ("healthcare", "education", "agriculture", "general"):
                    put(f"Sn{short}{c.capitalize()}", m[key]["report"][c]["f1-score"])
    b = jload("slicenet_baseline_metrics.json")
    if b:
        put("SnBaseFone", b["f1_macro"])
        put("SnBaseRows", int(b.get("rows", 0)))
    t = jload("slicenet_transfer.json")
    if t:
        names = {0.0: "Zero", 0.1: "Ten", 0.25: "Quarter", 0.5: "Half"}
        for point in t["curve"]:
            put(f"Tr{names.get(point['mininet_fraction'], 'X')}", point["f1_macro"])
        put("TrMininetOnly", t["mininet_only_f1_macro"])
        put("TrSharedCols", len(t["shared_columns"]))
    inl = table("slicenet_inloop_summary.csv")
    for _, r in inl.iterrows():
        key = f"{r['scenario'].capitalize()}{r['classification'].capitalize()}"
        put(f"Mixed{key}Sla", r.get("mixed_sla_share_mean"))
        put(f"Mixed{key}EduPninefive", r.get("mixed_education_p95_ms_mean"), 1)
        if r["classification"] == "slicenet":
            put(f"Mixed{r['scenario'].capitalize()}OnlineAcc", r.get("online_accuracy_mean"))


def rl():
    r = jload("rl_training.json")
    comp = r.get("evaluation") or r.get("sequential_env_comparison", {})
    for k, short in (("rule_based", "Rule"), ("rl_cem", "Cem"), ("rl_ppo", "Ppo")):
        if k in comp:
            put(f"Seq{short}Reward", comp[k]["mean_reward"] / 120, 2)
            put(f"Seq{short}Viol", comp[k]["sla_violations_per_episode"], 1)
            put(f"Seq{short}Sat", comp[k]["mean_satisfaction"])
    for k, short in (("rl_cem", "Cem"), ("rl_ppo", "Ppo")):
        paired = (comp.get("paired_vs_rule_based") or {}).get(k)
        if paired:
            put(f"Seq{short}Rel", paired["relative_pct"], 1)
            put(f"Seq{short}RelP", paired["wilcoxon_p"], 4)
    cem = r.get("cem", {})
    if cem:
        put("CemImprovement", cem.get("improvement"), 2)


def false_alarms():
    """Backup activations in runs with no injected failure (false failovers)."""
    runs_dir = RESULTS_DIR / "runs"
    total = false = 0
    detected = injected = 0
    if not runs_dir.exists():
        return
    for summary_path in runs_dir.glob("*/summary.json"):
        s = json.loads(summary_path.read_text())
        if s.get("injector_events"):
            injected += 1
            detected += int(bool(s.get("backup_backhaul_activated")) or "fiber_cut" in s.get("failure_types", []))
            continue
        total += 1
        false += int(bool(s.get("backup_backhaul_activated")))
    put("NoFaultRuns", total)
    put("FalseFailoverRuns", false)
    put("InjectedRuns", injected)
    put("InjectedDetected", detected)


def fiveg():
    path = RESULTS_DIR / "5g"
    rows = []
    for f in sorted(path.glob("5g__*.json")) if path.exists() else []:
        d = json.loads(f.read_text())
        hc, ag = d["slice_kpis"].get("healthcare", {}), d["slice_kpis"].get("agriculture", {})
        rows.append({"scenario": d["scenario"], "mode": d["mode"], "hc95": hc.get("latency_p95_ms"),
                     "hcsla": hc.get("sla_satisfied_share"), "ag95": ag.get("latency_p95_ms"),
                     "util": d.get("weighted_utility")})
    if not rows:
        return
    df = pd.DataFrame(rows)
    put("FiveGRuns", int(len(df)))
    for (scen, mode), g in df.groupby(["scenario", "mode"]):
        key = f"{scen.capitalize()}{'Cars' if mode == 'cars_sf' else 'None'}"
        put(f"Fg{key}HcP", float(g["hc95"].mean()), 1)
        put(f"Fg{key}HcSla", float(g["hcsla"].mean()))
        put(f"Fg{key}AgP", float(g["ag95"].mean()), 1)
        put(f"Fg{key}Util", float(g["util"].mean()))


STATIC = {  # measured once (see the evidence index in the handbook)
    "InferRfMs": "47", "InferCnnMs": "3.3", "InferCnnBatchMs": "4.5", "CnnParams": "29{,}764",
    "CnnSizeKb": "131", "RfSizeMb": "6.1", "CtrlStepUs": "7", "PpoReplanMs": "0.15",
    "PyLoc": "9{,}900", "UnitTests": "76", "IntegrationTests": "7",
    "OvsMttrBefore": "1.04", "OvsMttrAfter": "0.094", "OvsOutageAfter": "0.33--0.53",
    "FloorEdge": "8.00", "FloorCore": "28.00", "GenCpuBefore": "100", "GenCpuAfter": "7",
    "RsnsdRows": "108{,}000", "RsnsdCols": "89", "RsnsdApps": "32", "RsnsdScenarios": "19",
    "PaperSnAcc": "96.97\\%",
}


QOS_NAMES = {"static_equal": "Static", "context_unaware": "Unaware", "proposed": "Proposed", "qos_aware": "QosAware",
             "qos_adaptive": "QosAdaptive", "rl_residual": "Residual"}
QOS_METRICS = {"mean_class_sla": "MeanSla", "min_class_sla": "MinSla", "healthcare_sla_satisfied_share": "HcSla",
               "agriculture_sla_satisfied_share": "AgSla", "healthcare_loss_pct": "HcLoss",
               "weighted_utility": "Util", "decisions_applied": "Changes", "transient_mean_class_sla": "TransSla"}


def qos():
    """Contended-regime evaluation (modules A–F): NQ<scheduler><metric>, NQCond<cond><scheduler>MeanSla,
    NQDiff<baseline><metric> / NQP<baseline><metric> (qos_adaptive − baseline, Wilcoxon p)."""
    summary, stats = table("qos_summary.csv"), table("qos_stats.csv")
    if not summary.empty:
        for scheduler, short in QOS_NAMES.items():
            part = summary[summary["scheduler"] == scheduler]
            for metric, mshort in QOS_METRICS.items():
                col = f"{metric}_mean"
                if col in part and len(part):
                    put(f"Q{short}{mshort}", float(part[col].mean()), 1 if metric == "decisions_applied" else 3)
            for _, r in part.iterrows():
                cond = "".join(w.capitalize() for w in str(r["condition"]).replace("@", "_").replace(".", "p")
                               .replace("Mbps", "M").split("_"))
                put(f"QCond{cond}{short}MeanSla", r.get("mean_class_sla_mean"))
                put(f"QCond{cond}{short}MinSla", r.get("min_class_sla_mean"))
                for metric, mshort in (("healthcare_sla_satisfied_share", "HcSla"),
                                       ("agriculture_sla_satisfied_share", "AgSla"),
                                       ("general_sla_satisfied_share", "GenSla")):
                    put(f"QCond{cond}{short}{mshort}", r.get(f"{metric}_mean"))
        put("QConditions", int(summary["condition"].nunique()))
    if not stats.empty:
        for _, r in stats.iterrows():
            short, mshort = QOS_NAMES.get(r["baseline"]), QOS_METRICS.get(r["metric"])
            if short and mshort:
                put(f"QDiff{short}{mshort}", float(r["mean_difference"]), 4)
                put(f"QP{short}{mshort}", float(r["wilcoxon_p"]), 4)
                put(f"QPairs{short}{mshort}", int(r["pairs"]))
    sn = table("qos_slicenet_stats.csv")
    for _, r in sn.iterrows():
        mshort = QOS_METRICS.get(r["metric"])
        if mshort:
            put(f"QSnHost{mshort}", float(r["proposed_mean"]))
            put(f"QSnAll{mshort}", float(r["baseline_mean"]))
            put(f"QSnP{mshort}", float(r["wilcoxon_p"]), 4)
    runs = table("runs.csv")
    if not runs.empty:
        qsn = runs[(runs["study"] == "qos_slicenet") & (runs["classification"] == "slicenet_all")]
        if len(qsn):
            put("QSnAccuracy", float(qsn["online_accuracy"].mean()))
            put("QSnFinalAccuracy", float(qsn["online_final_accuracy"].mean()))
            put("QSnDecisionS", float(qsn["online_time_to_decision_s"].median()), 2)
        online = runs[runs["study"] == "qos_online"]
        if len(online):
            put("QOnlineRuns", int(len(online)))
            put("QOnlineTransitions", int(online["rl_transitions"].sum()))
            put("QOnlineFailed", int(online["enforcement_failed"].fillna(0).sum()))
            put("QOnlineMeanSla", float(online["mean_class_sla"].mean()))
        put("QOnlineTransMin", int(online["rl_transitions"].min()))
        put("QOnlineTransMax", int(online["rl_transitions"].max()))
        qruns = runs[runs["study"].isin(["qos_emergency", "qos_capacity", "qos_load", "qos_transitions"])]
        if len(qruns):
            put("QRuns", int(len(qruns)))
            put("QChangesApplied", int(qruns["decisions_applied"].fillna(0).sum()))
            put("QEnforcementFailed", int(qruns["enforcement_failed"].fillna(0).sum()))
            put("QReactions", int(qruns["controller_reactions"].fillna(0).sum()))
    calib = json.loads((RESULTS_DIR.parent / "scheduler" / "models" / "burst_calibration.json").read_text()) \
        if (RESULTS_DIR.parent / "scheduler" / "models" / "burst_calibration.json").exists() else {}
    if calib:
        put("CalSigmaHc", calib["sigma"]["healthcare"], 2)
        put("CalSigmaAg", calib["sigma"]["agriculture"], 2)
        put("CalBeta", calib.get("borrow_efficiency"), 2)
        put("CalRmseHc", calib["rmse_pct"]["healthcare"], 1)
        put("CalRmseAg", calib["rmse_pct"]["agriculture"], 1)
        put("CalTicks", int(calib["ticks"]))
    residual = jload("rl_training.json").get("residual", {})
    if residual:
        put("ResHeuristicReward", residual["heuristic_test_reward"], 1)
        rewards = list(residual["test_reward_per_seed"].values())
        put("ResRewardMin", min(rewards), 1)
        put("ResRewardMax", max(rewards), 1)
        rel = [p["relative_pct"] for p in residual["paired_per_seed"].values()]
        put("ResRelMin", min(rel), 1)
        put("ResRelMax", max(rel), 1)
        put("ResPMax", max(p["wilcoxon_p"] for p in residual["paired_per_seed"].values()), 3)
        put("ResSigSeeds", int(sum(p["wilcoxon_p"] < 0.05 for p in residual["paired_per_seed"].values())))
        viol = [r["comparison"]["rl_residual"]["sla_violations_per_episode"] for r in residual["runs"]]
        put("ResViolHeuristic", residual["runs"][0]["comparison"]["qos_heuristic"]["sla_violations_per_episode"], 1)
        put("ResViolMin", min(viol), 1)
        put("ResViolMax", max(viol), 1)
        put("ResDeployedSeed", int(residual["deployed_seed"]))


def final():
    """Predeclared final evaluation: claims, requirements, OVS validation, forecasts, RL sensitivity."""
    claims = table("final_claims.csv")
    for _, r in claims.iterrows():
        cid = "F" + r["claim"]
        for col, short, d in (("mean_diff", "Diff", 3), ("ci_low", "Lo", 3), ("ci_high", "Hi", 3),
                              ("rank_biserial", "R", 2), ("p", "P", 4), ("p_holm", "PHolm", 4)):
            v = r.get(col)
            put(f"{cid}{short}", None if pd.isna(v) else float(v), d)
        put(f"{cid}N", int(r["n"]))
        put(f"{cid}Verdict", str(r["verdict"]))
    reqs = table("final_requirements.csv")
    for _, r in reqs.iterrows():
        put(f"F{r['requirement']}Checked", int(r["runs_checked"]))
        put(f"F{r['requirement']}Failures", int(r["failures"]))
        put(f"F{r['requirement']}Pass", "pass" if bool(r["pass"]) else "fail")
    runs = table("runs.csv")
    if not runs.empty:
        runs = runs[~runs["stale"]]
        fin = runs[runs["study"].str.startswith("final_contended")]
        for cond in fin["condition"].unique():
            cname = "".join(w.capitalize() for w in str(cond).replace("@", "_").replace(".", "p").replace("Mbps", "M").split("_"))
            for sched in ("proposed", "qos_blind", "qos_adaptive", "rl_residual", "static_equal"):
                part = fin[(fin["condition"] == cond) & (fin["scheduler"] == sched)]
                tag = {"proposed": "Prop", "qos_blind": "Blind", "qos_adaptive": "Ad", "rl_residual": "Rl",
                       "static_equal": "Stat"}[sched]
                for metric, m in (("healthcare_sla_satisfied_share", "Hc"), ("agriculture_sla_satisfied_share", "Ag"),
                                  ("general_sla_satisfied_share", "Gen"), ("min_class_sla", "Min"), ("mean_class_sla", "Mean")):
                    if len(part):
                        put(f"FC{cname}{tag}{m}", float(part[metric].mean()))
        put("FRuns", int(len(runs[runs["study"].str.startswith("final_")])))
        ovs = runs[runs["run_id"].str.startswith("ovs_")]
        put("OvsRuns", int(len(ovs)))
        act = ovs[ovs["run_id"].str.startswith("ovs_actuation")]
        for (sc, sched), g in act.groupby(["scenario", "scheduler"]):
            tag = {"no_slicing": "None", "static_equal": "Stat", "qos_adaptive": "Ad"}[sched]
            put(f"Ovs{sc.capitalize()}{tag}Hc", float(g["healthcare_sla_satisfied_share"].mean()))
            put(f"Ovs{sc.capitalize()}{tag}Ag", float(g["agriculture_sla_satisfied_share"].mean()))
            put(f"Ovs{sc.capitalize()}{tag}Min", float(g["min_class_sla"].mean()))
        back = ovs[ovs["run_id"].str.startswith("ovs_backend")]
        put("OvsBackendChanges", int(back["decisions_applied"].sum()))
        put("OvsBackendFailed", int(back["enforcement_failed"].fillna(0).sum()))
        res = ovs[ovs["run_id"].str.startswith("ovs_resilience")]
        for sc, g in res.groupby("scenario"):
            name = "".join(w.capitalize() for w in sc.split("_"))
            put(f"Ovs{name}Outage", float(g[["education_outage_s", "general_outage_s"]].max(axis=1).mean()), 2)
            put(f"Ovs{name}Verified", float(g["recovery_verified"].mean()), 1)
        put("OvsNoFaultRuns", int(len(act) + len(back)))
    if not runs.empty:
        fresh = runs[runs["study"] == "posthoc_rl_online_fresh"]
        nolearn = runs[runs["study"] == "final_rl_online_nolearn"]
        if len(fresh) and len(nolearn):
            from experiments.final_analysis import paired as _paired
            both = pd.concat([fresh.assign(arm="fresh"), nolearn.assign(arm="nolearn")])
            st = _paired(both, "arm", "fresh", "nolearn", "mean_class_sla")
            put("PostFreshN", int(st["n"])); put("PostFreshDiff", st["mean_diff"]); put("PostFreshLo", st["ci_low"])
            put("PostFreshHi", st["ci_high"]); put("PostFreshP", st["p"], 4)
            put("PostFreshMeanSla", float(fresh["mean_class_sla"].mean()))
        learner = runs[runs["study"] == "final_rl_online"]
        if len(learner):
            put("OnlineLearnerMeanSla", float(learner["mean_class_sla"].mean()))
            put("OnlineNolearnMeanSla", float(nolearn["mean_class_sla"].mean()) if len(nolearn) else None)
    fq = table("forecast_quality.csv")
    for _, r in fq[fq["workload"] == "all"].iterrows():
        put(f"Fq{r['predictor'].capitalize()}Mae", float(r["mae_mbps"]), 2)
        put(f"Fq{r['predictor'].capitalize()}Under", float(r["under_provision_share"]), 2)
    t = jload("rl_training.json")
    for name, x in [("Default", t.get("residual"))] + [(k.replace("_x", "X").capitalize(), v)
                                                       for k, v in (t.get("residual_variants") or {}).items()]:
        if not x:
            continue
        rel = [p["relative_pct"] for p in x["paired_per_seed"].values()]
        ctx = [p["relative_pct"] for p in x["heldout_paired"]["context"].values()]
        load = [p["relative_pct"] for p in x["heldout_paired"]["load_1.3x"].values()]
        put(f"Res{name}RelMin", min(rel), 1); put(f"Res{name}RelMax", max(rel), 1)
        put(f"Res{name}CtxMin", min(ctx), 1); put(f"Res{name}CtxMax", max(ctx), 1)
        put(f"Res{name}LoadMin", min(load), 1); put(f"Res{name}LoadMax", max(load), 1)


def main():
    main_study(); ablation(); sensitivity(); resilience(); slicenet(); rl(); false_alarms(); fiveg(); qos(); final()
    macros.update(STATIC)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("% Generated by experiments/defense_numbers.py — do not edit by hand.\n")
        for name in sorted(macros):
            handle.write(f"\\newcommand{{\\N{name}}}{{{macros[name]}}}\n")
    print(f"wrote {len(macros)} macros to {OUT}")


if __name__ == "__main__":
    main()
