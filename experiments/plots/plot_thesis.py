#!/usr/bin/env python3
"""
Thesis figures from results/tables (experiments/aggregate.py) and run artefacts.

    python experiments/plots/plot_thesis.py

Every figure is backed by a CSV in results/tables (the table view), names its
series in a legend and on the axes, uses the validated categorical palette in
fixed order (entity → colour, never rank) and a single y-axis.
"""

from __future__ import annotations

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from core.config import RESULTS_DIR  # noqa: E402

TABLES = RESULTS_DIR / "tables"
FIGURES = os.path.join(REPO_ROOT, "docs", "figures", "thesis")

# Validated categorical palette (light surface), fixed order.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SEQUENTIAL = "Blues"

SCHEDULER_ORDER = ["proposed", "rl_cem", "rl_ppo", "proportional", "static_equal", "tgpp", "no_slicing"]
SCHEDULER_LABEL = {
    "proposed": "Proposed (demand-aware)", "rl_cem": "RL (CEM)", "rl_ppo": "RL (PPO)",
    "proportional": "Proportional", "static_equal": "Static equal", "tgpp": "3GPP slices",
    "no_slicing": "No slicing",
}
SERVICE_ORDER = ["healthcare", "education", "agriculture", "general"]
COLOR = {name: PALETTE[i] for i, name in enumerate(SCHEDULER_ORDER)}
SERVICE_COLOR = {name: PALETTE[i] for i, name in enumerate(SERVICE_ORDER)}


def style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
        "text.color": INK, "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID,
        "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
        "axes.titlesize": 11, "axes.titleweight": "bold", "axes.labelsize": 9,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8, "legend.frameon": False,
        "lines.linewidth": 2, "font.family": "DejaVu Sans",
    })


def save(fig, name: str):
    os.makedirs(FIGURES, exist_ok=True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, f"{name}.png"), dpi=200)
    fig.savefig(os.path.join(FIGURES, f"{name}.pdf"))
    plt.close(fig)
    print(f"  {name}")


def _load(name: str) -> pd.DataFrame | None:
    path = TABLES / name
    return pd.read_csv(path) if path.exists() else None


def grouped_bars(ax, df, group_col, series_col, metric, series_order, colors, labels=None):
    groups = list(dict.fromkeys(df[group_col]))
    series = [s for s in series_order if s in set(df[series_col])]
    width = 0.8 / max(len(series), 1)
    x = np.arange(len(groups))
    for i, s in enumerate(series):
        part = df[df[series_col] == s].set_index(group_col).reindex(groups)
        mean = part.get(f"{metric}_mean")
        if mean is None:
            continue
        ci = part.get(f"{metric}_ci95", pd.Series(0, index=part.index)).fillna(0)
        ax.bar(x + (i - (len(series) - 1) / 2) * width, mean, width * 0.92, yerr=ci,
               color=colors[s], edgecolor=SURFACE, linewidth=1,
               error_kw={"elinewidth": 1, "capsize": 2, "ecolor": INK_2},
               label=(labels or {}).get(s, s))
    ax.set_xticks(x)
    ax.set_xticklabels([g.replace("_", " ") if isinstance(g, str) else g for g in groups])


def fig_main():
    df = _load("main_summary.csv")
    if df is None:
        return
    for metric, ylabel, name in (
        ("weighted_utility", "Priority-weighted demand satisfaction", "main_weighted_utility"),
        ("healthcare_latency_p95_ms", "Healthcare p95 one-way delay (ms)", "main_healthcare_p95"),
        ("healthcare_demand_satisfaction", "Healthcare demand satisfaction", "main_healthcare_satisfaction"),
        ("fairness_satisfaction", "Jain fairness of satisfaction", "main_fairness"),
    ):
        if f"{metric}_mean" not in df:
            continue
        fig, ax = plt.subplots(figsize=(10, 4))
        grouped_bars(ax, df, "scenario", "scheduler", metric, SCHEDULER_ORDER, COLOR, SCHEDULER_LABEL)
        ax.set_ylabel(ylabel)
        ax.set_title(ylabel + " by scenario (mean ± 95 % CI, 5 seeds)")
        ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
        save(fig, name)


def fig_ablation():
    df = _load("ablation_summary.csv")
    if df is None:
        return
    variants = list(dict.fromkeys(df["variant"]))
    colors = {v: PALETTE[i] for i, v in enumerate(variants)}
    fig, ax = plt.subplots(figsize=(8, 3.8))
    grouped_bars(ax, df, "scenario", "variant", "weighted_utility", variants, colors)
    ax.set_ylabel("Priority-weighted demand satisfaction")
    ax.set_title("Ablation of the proposed scheduler (mean ± 95 % CI, 3 seeds)")
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    save(fig, "ablation")


def fig_sensitivity():
    for study, xcol, xlabel in (
        ("sensitivity_capacity", "capacity_mbps", "Rural uplink capacity (Mbps)"),
        ("sensitivity_load", "load_scale", "Offered load (× design demand)"),
    ):
        df = _load(f"{study}_summary.csv")
        if df is None:
            continue
        scenarios = list(dict.fromkeys(df["scenario"]))
        fig, axes = plt.subplots(1, len(scenarios), figsize=(4.2 * len(scenarios), 3.4), sharey=True)
        for ax, scenario in zip(np.atleast_1d(axes), scenarios):
            for scheduler in [s for s in SCHEDULER_ORDER if s in set(df["scheduler"])]:
                part = df[(df["scenario"] == scenario) & (df["scheduler"] == scheduler)].sort_values(xcol)
                ax.errorbar(part[xcol], part["weighted_utility_mean"], yerr=part["weighted_utility_ci95"],
                            color=COLOR[scheduler], marker="o", markersize=5, capsize=2,
                            label=SCHEDULER_LABEL[scheduler])
            ax.set_title(scenario.replace("_", " "))
            ax.set_xlabel(xlabel)
        np.atleast_1d(axes)[0].set_ylabel("Weighted demand satisfaction")
        np.atleast_1d(axes)[-1].legend()
        save(fig, study)


def fig_resilience():
    df = _load("resilience_summary.csv")
    if df is None:
        return
    variants = list(dict.fromkeys(df["variant"]))
    colors = {v: PALETTE[i] for i, v in enumerate(variants)}
    for metric, ylabel, name in (
        ("general_outage_s", "General-internet service outage (s)", "resilience_outage_general"),
        ("education_outage_s", "Education service outage (s)", "resilience_outage_education"),
        ("weighted_utility", "Weighted demand satisfaction", "resilience_utility"),
    ):
        if f"{metric}_mean" not in df:
            continue
        fig, ax = plt.subplots(figsize=(8, 3.6))
        grouped_bars(ax, df, "scenario", "variant", metric, variants, colors)
        ax.set_ylabel(ylabel)
        ax.set_title(ylabel + " under failures (mean ± 95 % CI)")
        ax.legend(ncol=3)
        save(fig, name)


def fig_timeline():
    path = RESULTS_DIR / "runs" / "timeline__proposed__s0" / "feedback.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    fig, ax = plt.subplots(figsize=(10, 3.8))
    for service in SERVICE_ORDER:
        ax.plot(df["tick"], df[f"{service}_tput_mbps"], color=SERVICE_COLOR[service], label=service)
        ax.annotate(service, (df["tick"].iloc[-1], df[f"{service}_tput_mbps"].iloc[-1]),
                    xytext=(4, 0), textcoords="offset points", fontsize=8, color=INK_2, va="center")
    changes = df[df["context"] != df["context"].shift()]
    for _, row in changes.iterrows():
        ax.axvline(row["tick"], color=INK_2, linewidth=0.8, linestyle=":")
        ax.text(row["tick"] + 0.3, ax.get_ylim()[1] * 0.95, row["context"].replace("_", " "),
                fontsize=8, color=INK_2, va="top")
    ax.set_xlabel("Tick (1 s; 10 simulated minutes)")
    ax.set_ylabel("Delivered throughput (Mbps)")
    ax.set_title("Rural-day timeline: per-slice throughput as the context changes (proposed)")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    save(fig, "timeline_throughput")


def fig_slicenet_inloop():
    df = _load("slicenet_inloop_summary.csv")
    if df is None or "mixed_sla_share_mean" not in df:
        return
    colors = {"host": PALETTE[4], "slicenet": PALETTE[0]}
    fig, ax = plt.subplots(figsize=(6, 3.4))
    grouped_bars(ax, df, "scenario", "classification", "mixed_sla_share", ["host", "slicenet"], colors,
                 {"host": "Address-based (host rules)", "slicenet": "In-loop SliceNet"})
    ax.set_ylabel("Mixed-UE flow windows meeting SLA")
    ax.set_title("Slicing a multi-service UE")
    ax.legend()
    save(fig, "slicenet_inloop")


def fig_slicenet_models():
    path = RESULTS_DIR / "slicenet_mininet_metrics.json"
    if not path.exists():
        return
    metrics = json.loads(path.read_text())
    for key, label in (("cnn_1d", "SliceNet 1D-CNN"), ("random_forest", "SliceNet RF")):
        if key not in metrics:
            continue
        cm = np.array(metrics[key]["confusion_matrix"], dtype=float)
        cm = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
        fig, ax = plt.subplots(figsize=(4.4, 3.8))
        ax.grid(False)
        im = ax.imshow(cm, cmap=SEQUENTIAL, vmin=0, vmax=1)
        ax.set_xticks(range(4), SERVICE_ORDER, rotation=30)
        ax.set_yticks(range(4), SERVICE_ORDER)
        for i in range(4):
            for j in range(4):
                ax.text(j, i, f"{cm[i, j]:.2f}", ha="center", va="center", fontsize=8,
                        color=SURFACE if cm[i, j] > 0.6 else INK)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ax.set_title(f"{label} (held-out runs × UEs)\nmacro F1 {metrics[key]['f1_macro']:.3f}")
        fig.colorbar(im, ax=ax, fraction=0.046)
        save(fig, f"slicenet_confusion_{key}")
    cnn = metrics.get("cnn_1d")
    if cnn and cnn.get("loss_history"):
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot(range(1, len(cnn["loss_history"]) + 1), cnn["loss_history"], color=PALETTE[0])
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Training cross-entropy")
        ax.set_title("SliceNet 1D-CNN training loss (measured)")
        save(fig, "slicenet_cnn_loss")
    transfer = RESULTS_DIR / "slicenet_transfer.json"
    if transfer.exists():
        t = json.loads(transfer.read_text())
        curve = pd.DataFrame(t["curve"])
        fig, ax = plt.subplots(figsize=(5, 3.2))
        ax.plot(curve["mininet_fraction"] * 100, curve["f1_macro"], color=PALETTE[0], marker="o",
                markersize=5, label="Synthetic + Mininet groups")
        ax.axhline(t["mininet_only_f1_macro"], color=PALETTE[1], linestyle="--", linewidth=1.5,
                   label="Mininet groups only")
        ax.set_xlabel("Share of training Mininet groups added (%)")
        ax.set_ylabel("Macro F1 on held-out Mininet groups")
        ax.set_title("Synthetic → measured transfer")
        ax.legend()
        save(fig, "slicenet_transfer")


def fig_rl():
    path = RESULTS_DIR / "rl_training.json"
    if not path.exists():
        return
    comparison = json.loads(path.read_text()).get("sequential_env_comparison", {})
    names = [n for n in ("rule_based", "rl_cem", "rl_ppo") if n in comparison]
    if not names:
        return
    colors = [COLOR.get({"rule_based": "proposed"}.get(n, n), PALETTE[0]) for n in names]
    fig, ax = plt.subplots(figsize=(5, 3.2))
    values = [comparison[n]["mean_reward"] / 120 for n in names]
    errors = [comparison[n]["std_reward"] / 120 for n in names]
    # Dot + error bar (not bars): the differences are small, and a zoomed axis
    # is only honest for position encodings, never for bar lengths.
    for i, (v, e, c) in enumerate(zip(values, errors, colors)):
        ax.errorbar(i, v, yerr=e, color=c, marker="o", markersize=8, capsize=3, elinewidth=1)
    ax.set_xticks(range(len(names)), ["Rule-based", "RL (CEM)", "RL (PPO)"][: len(names)])
    ax.set_xlim(-0.5, len(names) - 0.5)
    ax.set_ylabel("Mean reward per step (± 1 sd over episodes)")
    ax.set_title("Policies on the sequential environment")
    save(fig, "rl_policies")


def main():
    style()
    for fn in (fig_main, fig_ablation, fig_sensitivity, fig_resilience, fig_timeline,
               fig_slicenet_inloop, fig_slicenet_models, fig_rl):
        fn()


if __name__ == "__main__":
    main()
