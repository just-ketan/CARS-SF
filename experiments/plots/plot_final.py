#!/usr/bin/env python3
"""Figures of the final evaluation (docs/figures/final/), generated from results artefacts only.

  rl_learning_curves.png     residual PPO validation reward vs steps (default + reward variants, 3 seeds each)
  online_learning.png        online residual learner vs learning-disabled control, mean transition reward per run
  forecast_quality.png       forecast MAE and under-provisioning share per predictor (oracle = upper bound)
  final_class_sla.png        per-class SLA share by scheduler, contended conditions
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "figures" / "final"
TABLES = REPO / "results" / "tables"


def learning_curves():
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    styles = {"ppo_residual_runs": ("default", "-"), "ppo_residual_sla_x2_runs": ("SLA ×2", "--"),
              "ppo_residual_loss_x4_runs": ("loss ×4", ":")}
    for folder, (label, style) in styles.items():
        for i, path in enumerate(sorted(glob.glob(str(REPO / "scheduler" / "models" / folder / "seed*" / "learning_curve.csv")))):
            df = pd.read_csv(path)
            ax.plot(df["timesteps"], df["mean_reward"], style, lw=1.2, color=f"C{list(styles).index(folder)}",
                    label=label if i == 0 else None)
    ax.set_xlabel("training steps"); ax.set_ylabel("validation reward (5 episodes)")
    ax.set_title("Residual PPO learning curves (simulator; validation seeds)", fontsize=9)
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(OUT / "rl_learning_curves.png", dpi=150); plt.close(fig)


def online():
    runs = pd.read_csv(TABLES / "runs.csv")
    runs = runs[~runs["stale"] & runs["study"].isin(["final_rl_online", "final_rl_online_nolearn"])]
    if runs.empty:
        return
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for study, colour in (("final_rl_online", "C0"), ("final_rl_online_nolearn", "C1")):
        part = runs[runs["study"] == study].sort_values(["condition", "seed"]).reset_index(drop=True)
        ax.plot(range(1, len(part) + 1), part["rl_transition_mean_reward"], "o-", color=colour, label=study, lw=1)
    ax.set_xlabel("consecutive live run"); ax.set_ylabel("mean transition reward")
    ax.set_title("Online residual learning on the live network", fontsize=9)
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(OUT / "online_learning.png", dpi=150); plt.close(fig)


def forecast():
    path = TABLES / "forecast_quality.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    df = df[df["workload"] == "all"]
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.8))
    axes[0].bar(df["predictor"], df["mae_mbps"], color="C0"); axes[0].set_title("MAE (Mb/s)", fontsize=9)
    axes[1].bar(df["predictor"], df["under_provision_share"], color="C3")
    axes[1].set_title("under-prediction > 10 %", fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / "forecast_quality.png", dpi=150); plt.close(fig)


def class_sla():
    path = TABLES / "final_summary.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    df = df[df["study"].str.startswith("final_contended")]
    cols = [f"{s}_sla_satisfied_share_mean" for s in ("healthcare", "education", "agriculture", "general")]
    mean = df.groupby("scheduler")[cols].mean()
    order = [s for s in ("static_equal", "proportional", "proposed", "qos_blind", "qos_aware", "qos_reactive",
                         "qos_adaptive", "rl_residual", "rl_residual_safe") if s in mean.index]
    ax = mean.loc[order].rename(columns=lambda c: c.split("_")[0]).plot.bar(figsize=(7, 3.2), width=0.8)
    ax.set_ylim(0, 1.05); ax.set_ylabel("SLA-met share"); ax.set_xlabel("")
    ax.set_title("Per-class SLA share, mean over the 8 contended conditions", fontsize=9)
    ax.legend(fontsize=7, ncol=4); plt.xticks(rotation=25, ha="right", fontsize=7)
    plt.tight_layout(); plt.savefig(OUT / "final_class_sla.png", dpi=150); plt.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (learning_curves, online, forecast, class_sla):
        try:
            fn()
            print("ok", fn.__name__)
        except Exception as exc:     # a missing artefact must not hide the others; it is reported
            print("skipped", fn.__name__, exc, file=sys.stderr)


if __name__ == "__main__":
    main()
