"""
In-loop SliceNet: classify live flows and steer them into slices.

A *mixed* UE (one device running healthcare, education, agriculture and
general applications) cannot be sliced by address — host rules would put all
of its traffic into one class. Every control interval this classifier reads the
UE's live capture, builds traffic-shape features and packet sequences for each
active flow over the last window, predicts its service class and installs a
per-flow QoS rule. Decisions are scored against ground truth for evaluation.

Fallback policy: a flow SliceNet abstains on (low confidence or invalid
features) is not given a sticky rule; it stays in the UE's default class and
is re-classified on the next tick with more packets. After
``MAX_DEFERRALS`` abstentions it is pinned to ``FALLBACK_CLASS`` (best
effort) and recorded as a fallback decision.
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

from classification.slicenet import (
    CNN_MODEL_PATH, FALLBACK_CLASS, MODEL_DIR, SliceNetClassifier, SliceNetCNN,
)
from features.packet_capture import CapturePoint, parse_capture
from features.shape import packet_sequence, shape_features
from topology.rural_topology import MIXED_IP

MIN_PACKETS = 5
MAX_DEFERRALS = 3


def _held_out_scores() -> dict[str, float]:
    import json

    from core.config import RESULTS_DIR

    path = RESULTS_DIR / "slicenet_mininet_metrics.json"
    if not path.exists():
        return {}
    metrics = json.loads(path.read_text())
    return {k: v["f1_macro"] for k, v in metrics.items() if isinstance(v, dict) and "f1_macro" in v}


class OnlineSliceClassifier:
    def __init__(self, telemetry, qos, topo, traffic=None, window_s: float = 5.0):
        self.telemetry = telemetry
        self.qos = qos
        self.topo = topo
        self.traffic = traffic
        self.window_s = window_s
        self.cnn = SliceNetCNN() if os.path.exists(CNN_MODEL_PATH) else None
        rf_path = MODEL_DIR / "slicenet_mininet.pkl"
        self.rf = SliceNetClassifier(str(rf_path)) if os.path.exists(rf_path) else None
        # Use whichever model scored better on held-out runs × UEs.
        if self.cnn is not None and self.rf is not None:
            scores = _held_out_scores()
            if scores.get("random_forest", 0) >= scores.get("cnn_1d", 0):
                self.cnn = None
        self.decisions: list[dict[str, Any]] = []
        self.deferrals: dict[tuple, int] = {}
        self.abstentions = 0
        self.enabled = bool(getattr(topo, "mixed_ue", False)) and (self.cnn or self.rf) is not None

    def _capture_path(self) -> str | None:
        for _, path, ip in getattr(self.telemetry, "_captures", []):
            if ip == MIXED_IP:
                return path
        return None

    def _packets(self) -> pd.DataFrame:
        path = self._capture_path()
        if not path or not os.path.exists(path):
            return pd.DataFrame()
        rows = []
        for ts, direction, _, fields in parse_capture(CapturePoint(path, MIXED_IP)):
            src, dst, proto, sport, dport, ip_len, _, _, flags, _, _, payload_len = fields
            if proto not in (6, 17):
                continue
            if direction == "tx":
                flow, d = (src, dst, proto, sport, dport), 1
            else:
                flow, d = (dst, src, proto, dport, sport), -1
            rows.append((ts, flow, d, ip_len, proto, flags, payload_len))
        return pd.DataFrame(rows, columns=["ts", "flow", "direction", "ip_len", "proto", "tcp_flags", "payload_len"])

    def step(self, tick: int):
        if not self.enabled:
            return
        packets = self._packets()
        if packets.empty:
            return
        # Unclassified flows are judged on everything seen since they started,
        # so low-rate flows (IoT reports every few seconds) eventually qualify.
        pending = [
            (flow, group) for flow, group in packets.groupby("flow")
            if len(group) >= MIN_PACKETS and flow not in self.qos.flow_rules
        ]
        if not pending:
            return
        features = pd.DataFrame([
            {f"shape_{k}": v for k, v in shape_features(g, self._span(g)).items()} for _, g in pending
        ])
        if self.cnn is not None:
            import numpy as np
            outcomes = self.cnn.predict_with_confidence(features, np.stack([packet_sequence(g) for _, g in pending]))
            model = "cnn_1d"
        else:
            outcomes = self.rf.predict_with_confidence(features)
            model = "random_forest"
        for (flow, _), outcome in zip(pending, outcomes):
            predicted, fallback = outcome["predicted"], False
            if outcome["abstained"]:
                self.abstentions += 1
                self.deferrals[flow] = self.deferrals.get(flow, 0) + 1
                if self.deferrals[flow] < MAX_DEFERRALS:
                    continue
                predicted, fallback = FALLBACK_CLASS, True
            installed = self.qos.classify_flow(flow, predicted)
            self.decisions.append({
                "tick": tick,
                "flow": list(flow),
                "predicted": predicted,
                "model_prediction": outcome["predicted"],
                "confidence": outcome["confidence"],
                "fallback": fallback,
                "fallback_reason": outcome["reason"] if fallback else None,
                "truth": self._truth(flow),
                "model": model,
                "installed": installed,
            })

    def _span(self, group: pd.DataFrame) -> float:
        """Rates are normalised over the observed span (≥ one window), like the dataset."""
        return max(self.window_s, float(group["ts"].max() - group["ts"].min()))

    def _truth(self, flow: tuple) -> str | None:
        if self.traffic is None:
            return None
        ue, peer, proto, ue_port, peer_port = flow
        for spawn in self.traffic.get_spawn_metadata():
            if spawn["host_ip"] == ue and spawn["server_ip"] == peer and spawn["port"] in (ue_port, peer_port):
                return spawn["service_class"]
        return None

    def summary(self) -> dict[str, Any]:
        scored = [d for d in self.decisions if d["truth"] is not None]
        return {
            "enabled": self.enabled,
            "flows_classified": len(self.decisions),
            "fallback_decisions": sum(d["fallback"] for d in self.decisions),
            "abstentions": self.abstentions,
            "accuracy": round(sum(d["predicted"] == d["truth"] for d in scored) / len(scored), 4) if scored else None,
            "decisions": self.decisions,
        }
