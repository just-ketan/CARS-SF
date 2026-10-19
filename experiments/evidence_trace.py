#!/usr/bin/env python3
"""
Execution traces for the two critical paths (written to results/evidence/).

    python experiments/evidence_trace.py synthetic            # runs the synthetic path now and traces it
    python experiments/evidence_trace.py live <run_dir>       # traces a recorded live (Mininet) run

synthetic: seeded RSNSD generation → contract validation → SliceNet baseline
inference with the confidence gate on a held-out scenario → the deployed PPO
policy stepping SequentialSlicingEnv (observation → action → priorities →
allocation → served/delay → reward terms → next observation).

live: one row per controller decision of a recorded run, joined from
rl_transitions.jsonl (state, action, reward, next state), summary.json
(decision reason, enforcement read-back) and feedback.csv (per-tick measured
throughput and reward terms), so every transition can be checked against the
raw per-tick measurements it averages.

Nothing is computed for the trace that the pipeline did not compute itself:
the synthetic trace calls the production functions, the live trace only reads
the run's own artefacts.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
OUT = REPO_ROOT / "results" / "evidence"
SERVICES = ("healthcare", "education", "agriculture", "general")


def _r(values, digits=3):
    return "[" + ", ".join(f"{v:.{digits}f}" for v in values) + "]"


def synthetic(steps: int = 6, seed: int = 7) -> str:
    from classification.slicenet import MODEL_DIR, SliceNetClassifier
    from dataset.rsnsd import SOURCE, generate
    from features.contract import SCHEMA_VERSION, stamp, validate
    from scheduler.agent import PPO_MODEL_PATH
    from scheduler.env_seq import SequentialSlicingEnv

    lines = [f"# Synthetic path trace ({datetime.now().isoformat(timespec='seconds')})", ""]

    df = stamp(generate(30, seed), SOURCE, seed, f"trace-s{seed}")
    again = stamp(generate(30, seed), SOURCE, seed, f"trace-s{seed}")
    report = validate(df, SOURCE)
    lines += ["## 1. Seeded RSNSD generation → contract", "",
              f"* `dataset.rsnsd.generate(30, seed={seed})`: {len(df)} rows × {len(df.columns)} columns, "
              f"{df['rsnsd_scenario'].nunique()} scenarios; regenerated with the same seed → identical: "
              f"**{df.equals(again)}**",
              f"* `features.contract.validate(df, '{SOURCE}')` ({SCHEMA_VERSION}): ok = **{report.ok}**, errors = {report.errors}",
              f"* class counts: {df['service_class'].value_counts().sort_index().to_dict()}", ""]

    model_path = MODEL_DIR / "slicenet_baseline.pkl"
    clf = SliceNetClassifier(str(model_path))
    scenario = sorted(df["rsnsd_scenario"].unique())[0]
    sample = df[df["rsnsd_scenario"] == scenario].groupby("service_class").head(2)
    decisions = clf.predict_with_confidence(sample)
    lines += ["## 2. SliceNet inference (synthetic baseline model, confidence gate 0.5)", "",
              f"Model `{model_path.relative_to(REPO_ROOT)}`, {len(clf.feature_columns)} features in training order; "
              f"rows from scenario `{scenario}` (newly generated with seed {seed}, not the training file).", "",
              "| flow | true class | predicted | confidence | abstained | reason |", "|---|---|---|---|---|---|"]
    for (_, row), d in zip(sample.iterrows(), decisions):
        lines.append(f"| {row['flow_id'][:8]} | {row['service_class']} | {d['predicted']} | {d['confidence']} | "
                     f"{d['abstained']} | {d['reason'] or ''} |")
    lines.append("")

    from stable_baselines3 import PPO
    model = PPO.load(PPO_MODEL_PATH, device="cpu")
    env = SequentialSlicingEnv()
    obs, _ = env.reset(seed=1000, options={"context": "disaster"})
    lines += ["## 3. RL loop in the simulator (deployed PPO, test seed 1000, context disaster)", "",
              f"Observation layout: 8 context one-hot · 4 demand/C · 4 backlog/(C·0.1 s) · 4 allocation/C · on_backup "
              f"({env.observation_space.shape[0]} floats). Action: log10 priority multipliers in [−1, 1].", ""]
    for t in range(steps):
        action, _ = model.predict(obs, deterministic=True)
        next_obs, reward, _, done, info = env.step(action)
        lines += [f"### step {t}",
                  f"* s_t demand/C {_r(obs[8:12])}, backlog {_r(obs[12:16])}, alloc/C {_r(obs[16:20])}, on_backup {obs[20]:.0f}",
                  f"* a_t {_r(action)} → multipliers {_r([10 ** float(np.clip(a, -1, 1)) for a in action], 2)}",
                  f"* allocation (Mb/s) {json.dumps({k: round(v, 1) for k, v in info['allocation'].items()})}",
                  f"* delay (ms) {json.dumps({k: float(v) for k, v in info['delay_ms'].items()})}, "
                  f"satisfaction {json.dumps(info['satisfaction'])}",
                  f"* r_t = {reward:.3f} = " + " + ".join(f"{k} {v:+.3f}" for k, v in info["reward_terms"].items()),
                  f"* s_t+1 demand/C {_r(next_obs[8:12])}, backlog {_r(next_obs[12:16])}, alloc/C {_r(next_obs[16:20])}",
                  ""]
        obs = next_obs
        if done:
            break
    return "\n".join(lines)


def live(run_dir: Path) -> str:
    summary = json.loads((run_dir / "summary.json").read_text())
    records = [json.loads(line) for line in (run_dir / "rl_transitions.jsonl").read_text().splitlines()]
    feedback = pd.read_csv(run_dir / "feedback.csv").set_index("tick")
    history = {h["tick"]: h for h in summary.get("controller_history", [])}
    lines = [f"# Live coupled-loop trace: `{summary['run_id']}`", "",
             f"Scheduler `{summary.get('scheduler')}`, scenario `{summary.get('scenario_id')}`, "
             f"data source `{summary.get('data_source')}`, {summary.get('record_count')} measured flow windows; "
             f"contract: {summary.get('contract', {}).get('ok')}.",
             f"Enforcement: {json.dumps(summary.get('enforcement_summary'))}.",
             f"Transitions: {json.dumps(summary.get('rl_transitions'))}.",
             f"Policy learning: {json.dumps({k: v for k, v in (summary.get('policy_learning') or {}).items() if k != 'per_context'})}.",
             ""]
    lines += ["| decision tick → next | reason | action (log10 mult.) | allocation Mb/s (h/e/a/g) | kernel read-back | "
              "measured Mb/s per tick (h/e/a/g) | per-tick reward | transition reward |",
              "|---|---|---|---|---|---|---|---|"]
    for r in records:
        h = history.get(r["tick"], {})
        enf = h.get("enforcement") or {}
        readback = ("unchanged (< 1 Mb/s)" if not r["allocation_changed"]
                    else f"verified={enf.get('verified')}, mismatches={len(enf.get('mismatches', []))}")
        ticks = range(r["tick"] + 1, r["next_tick"] + 1)
        measured = "; ".join(
            "/".join(f"{feedback.loc[t, f'{s}_tput_mbps']:.1f}" if f"{s}_tput_mbps" in feedback else "–" for s in SERVICES)
            for t in ticks if t in feedback.index)
        per_tick = ", ".join(f"{feedback.loc[t, 'reward']:.1f}" for t in ticks if t in feedback.index)
        alloc = "/".join(f"{r['allocation'].get(s, 0):.1f}" for s in SERVICES)
        lines.append(f"| {r['tick']} → {r['next_tick']} | {h.get('reason', '')} | {_r(r['action'], 2)} | {alloc} | "
                     f"{readback} | {measured} | {per_tick} | {r['reward']:.2f} |")
    first, last = records[0], records[-1]
    lines += ["", "Observation chaining: every transition's `next_obs` equals the next transition's `obs`: "
              f"**{all(a['next_obs'] == b['obs'] for a, b in zip(records, records[1:]))}**. "
              f"First observation (tick 0): {_r(first['obs'], 3)}. Final transition done = {last['done']}.", ""]
    return "\n".join(lines)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "synthetic"
    if mode == "synthetic":
        text, path = synthetic(), OUT / "synthetic_path_trace.md"
    elif mode == "live":
        run_dir = Path(sys.argv[2])
        text, path = live(run_dir), OUT / f"live_loop_trace__{run_dir.name}.md"
    else:
        raise SystemExit(__doc__)
    path.write_text(text + "\n")
    print(text)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
