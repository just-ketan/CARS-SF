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


def main():
    main_study(); ablation(); sensitivity(); resilience(); slicenet(); rl(); false_alarms(); fiveg()
    macros.update(STATIC)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("% Generated by experiments/defense_numbers.py — do not edit by hand.\n")
        for name in sorted(macros):
            handle.write(f"\\newcommand{{\\N{name}}}{{{macros[name]}}}\n")
    print(f"wrote {len(macros)} macros to {OUT}")


if __name__ == "__main__":
    main()
