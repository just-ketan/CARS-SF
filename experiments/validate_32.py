#!/usr/bin/env python3
"""
Validate the integrated closed loop across all 32 class × scenario combinations on the 5G
deployment; implements docs/thesis/validation_32_plan.md.

    python experiments/validate_32.py                # run what is missing, then analyse
    python experiments/validate_32.py --analyse      # analyse existing runs only

Writes results/tables/v32_cells.csv (per arm × scenario × class), v32_claims.csv, v32_chain.csv.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "deployment" / "5g"))

from core.config import RESULTS_DIR  # noqa: E402
from experiments.final_analysis import holm, paired  # noqa: E402
from scheduler.env_dir import EVALUATED_SCENARIOS  # noqa: E402

ARMS = {"no_slicing": ("no_slicing", "host"), "rules": ("qos_adaptive", "host"),
        "slicenet": ("qos_adaptive", "slicenet_all"), "full": ("closed_loop", "slicenet_all")}
CLASSES = ("healthcare", "education", "agriculture", "general")
SEEDS, DURATION, CAPACITY, PREFIX, PASS_SHARE = (40, 41, 42, 43, 44), 60, 100.0, "v32", 0.95
OUT, TABLES = RESULTS_DIR / "5g", RESULTS_DIR / "tables"
ONLINE_CHECKPOINT = RESULTS_DIR / "5g" / "v32_online_checkpoint.json"


def result_path(arm: str, scenario: str, seed: int) -> Path:
    scheduler, classification = ARMS[arm]
    return OUT / f"{PREFIX}__{scenario}__{scheduler}__{classification}__s{seed}.json"


def execute():
    from run_5g import run_loop

    os.environ["CARS_SF_CEM_ONLINE_PATH"] = str(ONLINE_CHECKPOINT)
    os.environ["CARS_SF_SLICENET_MODEL"] = str(REPO_ROOT / "classification" / "models" / "slicenet_5g.pkl")
    rng = np.random.default_rng(2026)
    for seed in SEEDS:
        for scenario in rng.permutation(EVALUATED_SCENARIOS):
            for arm in ARMS:
                if result_path(arm, str(scenario), seed).exists():
                    continue
                scheduler, classification = ARMS[arm]
                r = run_loop(str(scenario), scheduler, classification, DURATION, CAPACITY, seed, run_prefix=PREFIX,
                             self_healing=arm != "no_slicing")
                print(json.dumps({"run": r["run_id"], "records": r["records"], "enforcement": r["enforcement"]}), flush=True)


def load_runs() -> pd.DataFrame:
    rows = []
    for arm in ARMS:
        for scenario in EVALUATED_SCENARIOS:
            for seed in SEEDS:
                path = result_path(arm, scenario, seed)
                if not path.exists():
                    continue
                r = json.loads(path.read_text())
                shares = {c: (r["slice_kpis"].get(c) or {}).get("sla_satisfied_share") for c in CLASSES}
                known = [v for v in shares.values() if v is not None]
                monitor = r["qos_monitor"]
                row = {"arm": arm, "scenario": scenario, "seed": seed, "condition": scenario,
                       **{f"{c}_sla": shares[c] for c in CLASSES},
                       "mean_class_sla": float(np.mean(known)) if known else None,
                       "min_class_sla": min(known) if known else None,
                       "persistent_ticks": sum(monitor["per_class_persistent_ticks"].values()),
                       "persistent_episodes": monitor["persistent_episodes"],
                       "transient_episodes": monitor["transient_episodes"],
                       "failed_verifications": r["enforcement"]["failed"], "applied": r["enforcement"]["decisions_applied"],
                       "verified": r["enforcement"]["verified"], "safety_rejections": r["safety_rejections"],
                       "rl_adaptations": len(r["adaptations"]), "rl_accepted": r["hybrid"]["accepted"],
                       "rl_rejected": r["hybrid"]["rejected"],
                       "improved": sum(bool(a.get("improved")) for a in r["adaptations"]),
                       "restored": sum(bool(a.get("restored")) for a in r["adaptations"]),
                       "feedback_ticks": r.get("duration"), "records": r["records"]}
                sn = r.get("slicenet")
                if sn:
                    row.update({"sn_decisions": sn["flows_classified"], "sn_accuracy": sn["accuracy"],
                                "sn_final_accuracy": sn["final_accuracy"],
                                "sn_time_to_decision_s": sn["median_time_to_decision_s"]})
                    final = {tuple(d["flow"]): d["predicted"] for d in sn["decisions"]}
                    final |= {tuple(x["flow"]): x["to"] for x in sn["reclassifications"]}
                    truth = {tuple(d["flow"]): d["truth"] for d in sn["decisions"] if d["truth"]}
                    for c in CLASSES:
                        flows = [f for f, t in truth.items() if t == c]
                        row[f"{c}_sn_flows"] = len(flows)
                        row[f"{c}_sn_correct"] = sum(final[f] == c for f in flows)
                rows.append(row)
    return pd.DataFrame(rows)


def cells(runs: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (arm, scenario), group in runs.groupby(["arm", "scenario"]):
        for c in CLASSES:
            values = group[f"{c}_sla"].dropna().astype(float)
            half = stats.t.ppf(0.975, len(values) - 1) * values.std(ddof=1) / np.sqrt(len(values)) if len(values) > 1 else None
            row = {"arm": arm, "scenario": scenario, "class": c, "n": len(values), "sla_share": round(values.mean(), 3),
                   "ci95": None if half is None else round(half, 3), "pass": bool(values.mean() >= PASS_SHARE)}
            if f"{c}_sn_flows" in group and group[f"{c}_sn_flows"].sum():
                row["slicenet_flow_accuracy"] = round(group[f"{c}_sn_correct"].sum() / group[f"{c}_sn_flows"].sum(), 3)
            out.append(row)
    return pd.DataFrame(out)


def claims(runs: pd.DataFrame) -> pd.DataFrame:
    spec = [("V1", "rules", "no_slicing", "healthcare_sla", "gt0"), ("V2", "full", "no_slicing", "min_class_sla", "gt0"),
            ("V3", "slicenet", "rules", "mean_class_sla", "noninferior"), ("V4", "full", "slicenet", "mean_class_sla", "gt0"),
            ("V5", "full", "slicenet", "persistent_ticks", "lt0")]
    rows = [{"claim": c, "comparison": f"{a} vs {b}", "metric": m, "rule": rule, **paired(runs, "arm", a, b, m)}
            for c, a, b, m, rule in spec]
    df = pd.DataFrame(rows)
    df["p_holm"] = None
    primary = df["p"].notna()
    if primary.any():
        df.loc[primary, "p_holm"] = [round(v, 6) for v in holm(df.loc[primary, "p"].astype(float).tolist())]

    def verdict(r):
        if r["mean_diff"] is None or pd.isna(r["mean_diff"]):
            return "not evaluated"
        if r["rule"] == "noninferior":
            return "supported" if r["ci_low"] >= -0.02 else "unsupported"
        good = r["mean_diff"] > 0 if r["rule"] == "gt0" else r["mean_diff"] < 0
        return "supported" if good and r["p_holm"] is not None and r["p_holm"] < 0.05 else "unsupported"

    df["verdict"] = [verdict(r) for _, r in df.iterrows()]
    return df


def chain(runs: pd.DataFrame) -> pd.DataFrame:
    full = runs[runs["arm"] == "full"]
    triggered = full[full["persistent_episodes"] > 0]
    rows = [
        ("1 monitored", len(full), int((full["feedback_ticks"] == DURATION).sum())),
        ("2 identified", len(full), int((full["sn_decisions"] > 0).sum())),
        ("3 mapped", len(full), int((full["sn_final_accuracy"].notna()).sum())),
        ("4 evaluated", len(full), int((full["persistent_episodes"] + full["transient_episodes"] >= 0).sum())),
        ("5 triggered", len(triggered), int((triggered["rl_adaptations"] > 0).sum())),
        ("6 decided", len(triggered), int((triggered["rl_accepted"] + triggered["rl_rejected"] > 0).sum())),
        ("7 applied+verified", len(full), int(((full["verified"] == full["applied"]) & (full["applied"] > 0)).sum())),
        ("8 outcome measured", len(triggered), int((triggered["rl_adaptations"] > 0).sum())),
        ("9 autonomous", len(full), int((full["records"] > 0).sum())),
    ]
    return pd.DataFrame(rows, columns=["step", "runs_required", "runs_with_evidence"])


def analyse():
    runs = load_runs()
    if runs.empty:
        raise SystemExit("no validation runs yet")
    TABLES.mkdir(parents=True, exist_ok=True)
    runs.to_csv(TABLES / "v32_runs.csv", index=False)
    table, verdicts, steps = cells(runs), claims(runs), chain(runs)
    table.to_csv(TABLES / "v32_cells.csv", index=False)
    verdicts.to_csv(TABLES / "v32_claims.csv", index=False)
    steps.to_csv(TABLES / "v32_chain.csv", index=False)
    pd.set_option("display.width", 200)
    for arm in ARMS:
        part = table[table["arm"] == arm]
        if len(part):
            print(f"\n{arm}: {int(part['pass'].sum())}/{len(part)} cells ≥ {PASS_SHARE}")
            print(part.pivot(index="scenario", columns="class", values="sla_share").reindex(EVALUATED_SCENARIOS)[list(CLASSES)].to_string())
    print(verdicts[["claim", "comparison", "metric", "n", "mean_diff", "ci_low", "ci_high", "rank_biserial", "p", "p_holm", "verdict"]].to_string(index=False))
    print(steps.to_string(index=False))
    print("safety: failed", int(runs["failed_verifications"].sum()), "rejections", int(runs["safety_rejections"].sum()), "runs", len(runs))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--analyse", action="store_true")
    args = parser.parse_args()
    if not args.analyse:
        execute()
    analyse()


if __name__ == "__main__":
    main()
