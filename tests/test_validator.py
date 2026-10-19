"""Dataset validator: achievable maximum and failure detection."""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_features
from validation.validator import DatasetValidator


def _dataset(n=80, seed=0):
    rng = np.random.default_rng(seed)
    cfg = load_features()
    df = pd.DataFrame({c: rng.uniform(1, 10, n) for c in cfg["ml_feature_columns"]})
    df["service_class"] = ["healthcare", "education", "agriculture", "general"] * (n // 4)
    for col in cfg["label_columns"]:
        if col not in df.columns:
            df[col] = 1
    df["link_utilization_pct"] = np.linspace(10, 95, n)
    df["queueing_delay_ms"] = df["link_utilization_pct"] / 10 + rng.uniform(0, 0.1, n)
    df["goodput_mbps"] = df["throughput_mbps"] * 0.9
    return df


def test_clean_dataset_passes_and_can_reach_high_score():
    report = DatasetValidator(_dataset()).validate()
    assert report["passed"] and report["total_score"] >= 90


def test_physical_violations_and_missing_measurements_are_penalised():
    df = _dataset()
    df.loc[:20, "goodput_mbps"] = df.loc[:20, "throughput_mbps"] + 5
    df.loc[:40, "end_to_end_latency_ms"] = np.nan
    df = df[df["service_class"] != "agriculture"]
    report = DatasetValidator(df).validate()
    assert report["qos_score"] < 20 and report["measurement_score"] < 15
    assert report["class_score"] < 15


def test_outage_is_longest_delivery_gap_not_first_delivery():
    from analysis.metrics import outage_metrics

    rows = []
    for i in range(200):            # one packet every 50 ms from t=0 to t=10
        tx = i * 0.05
        lost = 3.0 <= tx < 6.0      # failure at t=3, restored at t=6
        rx = np.nan if lost else tx + 0.01
        if 3.0 <= tx < 3.02:
            rx = tx + 0.01          # one packet already in flight is still delivered
        rows.append({"tx_ts": tx, "rx_ts": rx, "flow": ("10.0.1.20", "10.0.3.10", 17, 1, 2)})
    result = outage_metrics(pd.DataFrame(rows), 3.0, {"10.0.1.20": "education"}, {"10.0.3.10"})
    assert 2.9 <= result["education"]["outage_s"] <= 3.05
    assert result["education"]["lost_packets"] >= 58


def test_delivered_rate_ignores_partial_final_window():
    from analysis.metrics import slice_kpis

    rows = [{"service_class": "healthcare", "window_index": w, "throughput_mbps": 10.0,
             "end_to_end_latency_ms": 5.0, "p95_latency_ms": 6.0, "jitter_ms": 0.1,
             "packet_loss_rate": 0.0, "sla_satisfied": True} for w in range(8)]
    rows.append({**rows[0], "window_index": 8, "throughput_mbps": 0.01})   # stray tail packets
    kpis = slice_kpis(pd.DataFrame(rows), {"healthcare": 10.0})
    assert kpis["healthcare"]["delivered_mbps"] == 10.0
    assert kpis["healthcare"]["demand_satisfaction"] == 1.0
