"""
In-loop SliceNet: classify live flows and steer them into slices.

Two modes (``classification`` option of a run):

  slicenet       address rules for single-service UEs; SliceNet classifies the
                 flows of the mixed-service UE only (a device running every
                 service cannot be sliced by address)
  slicenet_all   no address rules: every UE flow is classified by SliceNet

Every tick the classifier reads only the packets appended to each watched UE
capture since the previous tick (``IncrementalCaptureReader``). A new flow is
decided as soon as it has been seen for ``EARLY_S`` seconds and ``MIN_PACKETS``
packets: features over the observed span are expressed as a full 5 s window
(``early_shape_features``). Decided flows are re-checked every
``RECHECK_TICKS`` with real full-window features; a different class predicted
with confidence ≥ ``RECLASS_CONFIDENCE`` on ``RECLASS_CONFIRM`` consecutive
checks replaces the flow's rule, so an early mistake does not stick.

Fallback policy: a flow SliceNet abstains on (low confidence or invalid
features) keeps the UE's default class and is retried; after ``MAX_DEFERRALS``
abstentions it is pinned to ``FALLBACK_CLASS`` (best effort). Decisions are
scored against generator ground truth for evaluation only.
"""

from __future__ import annotations

import os
from collections import deque
from typing import Any

import numpy as np
import pandas as pd

from classification.slicenet import (
    CNN_MODEL_PATH, FALLBACK_CLASS, MODEL_DIR, SliceNetClassifier, SliceNetCNN,
)
from features.packet_capture import CapturePoint, IncrementalCaptureReader, parse_capture  # noqa: F401
from features.shape import early_shape_features, packet_sequence, shape_features
from topology.rural_topology import MIXED_IP

MIN_PACKETS = 5
MAX_DEFERRALS = 3
EARLY_S = 1.0
RECHECK_TICKS = 5
RECLASS_CONFIDENCE = 0.8
RECLASS_CONFIRM = 2
FLOW_BUFFER = 600


def _held_out_scores() -> dict[str, float]:
    import json

    from core.config import RESULTS_DIR

    path = RESULTS_DIR / "slicenet_mininet_metrics.json"
    if not path.exists():
        return {}
    metrics = json.loads(path.read_text())
    return {k: v["f1_macro"] for k, v in metrics.items() if isinstance(v, dict) and "f1_macro" in v}


class OnlineSliceClassifier:
    COLUMNS = ["ts", "flow", "direction", "ip_len", "proto", "tcp_flags", "payload_len"]

    def __init__(self, telemetry, qos, topo, traffic=None, window_s: float = 5.0, all_ues: bool = False):
        self.telemetry = telemetry
        self.qos = qos
        self.topo = topo
        self.traffic = traffic
        self.window_s = window_s
        self.all_ues = all_ues
        self.cnn = SliceNetCNN() if os.path.exists(CNN_MODEL_PATH) else None
        # CARS_SF_SLICENET_MODEL selects a deployment-specific model (the 5G runner's).
        rf_path = os.environ.get("CARS_SF_SLICENET_MODEL") or MODEL_DIR / "slicenet_mininet.pkl"
        self.rf = SliceNetClassifier(str(rf_path)) if os.path.exists(rf_path) else None
        # Use whichever model scored better on held-out runs × UEs.
        if os.environ.get("CARS_SF_SLICENET_MODEL"):
            self.cnn = None
        if self.cnn is not None and self.rf is not None:
            scores = _held_out_scores()
            if scores.get("random_forest", 0) >= scores.get("cnn_1d", 0):
                self.cnn = None
        self.decisions: list[dict[str, Any]] = []
        self.reclassifications: list[dict[str, Any]] = []
        self.deferrals: dict[tuple, int] = {}
        self.abstentions = 0
        self.flows: dict[tuple, dict[str, Any]] = {}
        self.readers: dict[str, IncrementalCaptureReader] = {}
        watching = all_ues or bool(getattr(topo, "mixed_ue", False))
        self.enabled = watching and (self.cnn or self.rf) is not None

    # ------------------------------------------------------------ packets

    def _ue_ips(self) -> set[str]:
        if not self.all_ues:
            return {MIXED_IP}
        return {h.IP() for h in getattr(self.topo, "ue_hosts", [])} | (
            {MIXED_IP} if getattr(self.topo, "mixed_ue", False) else set())

    def _ensure_readers(self):
        wanted = self._ue_ips()
        for _, path, ip in getattr(self.telemetry, "_captures", []):
            if ip in wanted and ip not in self.readers:
                self.readers[ip] = IncrementalCaptureReader(CapturePoint(path, ip))

    def _ingest(self):
        self._ensure_readers()
        for reader in self.readers.values():
            for ts, direction, _, fields in reader.read_new():
                src, dst, proto, sport, dport, ip_len, _, _, flags, _, _, payload_len = fields
                if proto not in (6, 17):
                    continue
                if direction == "tx":
                    flow, d = (src, dst, proto, sport, dport), 1
                else:
                    flow, d = (dst, src, proto, dport, sport), -1
                state = self.flows.setdefault(flow, {"first_ts": ts, "packets": deque(maxlen=FLOW_BUFFER),
                                                     "class": None, "alt": None, "alt_count": 0, "checked": 0})
                state["packets"].append((ts, flow, d, ip_len, proto, flags, payload_len))
                state["last_ts"] = ts

    def _frame(self, packets) -> pd.DataFrame:
        return pd.DataFrame(list(packets), columns=self.COLUMNS)

    # ------------------------------------------------------------ decisions

    def _predict(self, frames: list[pd.DataFrame], spans: list[float], early: bool) -> tuple[list[dict], str]:
        rows = []
        for g, span in zip(frames, spans):
            feats = early_shape_features(g, span, self.window_s) if early else shape_features(g, max(span, self.window_s))
            rows.append({f"shape_{k}": v for k, v in feats.items()})
        features = pd.DataFrame(rows)
        if self.cnn is not None:
            return self.cnn.predict_with_confidence(features, np.stack([packet_sequence(g) for g in frames])), "cnn_1d"
        return self.rf.predict_with_confidence(features), "random_forest"

    def step(self, tick: int):
        if not self.enabled:
            return
        self._ingest()
        now = max((s.get("last_ts", 0.0) for s in self.flows.values()), default=0.0)
        self._decide_new(tick, now)
        if tick % RECHECK_TICKS == 0:
            self._recheck(tick)

    def _decide_new(self, tick: int, now: float):
        pending = []
        for flow, state in self.flows.items():
            if state["class"] is not None or flow in self.qos.flow_rules:
                continue
            span = now - state["first_ts"]
            if len(state["packets"]) >= MIN_PACKETS and span >= EARLY_S:
                pending.append((flow, state, span))
        if not pending:
            return
        frames = [self._frame(state["packets"]) for _, state, _ in pending]
        outcomes, model = self._predict(frames, [span for *_, span in pending], early=True)
        for (flow, state, span), outcome in zip(pending, outcomes):
            predicted, fallback = outcome["predicted"], False
            if outcome["abstained"]:
                self.abstentions += 1
                self.deferrals[flow] = self.deferrals.get(flow, 0) + 1
                if self.deferrals[flow] < MAX_DEFERRALS:
                    continue
                predicted, fallback = FALLBACK_CLASS, True
            installed = self.qos.classify_flow(flow, predicted)
            state["class"], state["checked"] = predicted, tick
            self.decisions.append({
                "tick": tick, "flow": list(flow), "predicted": predicted,
                "model_prediction": outcome["predicted"], "confidence": outcome["confidence"],
                "fallback": fallback, "fallback_reason": outcome["reason"] if fallback else None,
                "observed_s": round(span, 3), "packets": len(state["packets"]),
                "truth": self._truth(flow), "model": model, "installed": installed,
            })

    def _recheck(self, tick: int):
        due = []
        for flow, state in self.flows.items():
            if state["class"] is None or tick - state["checked"] < RECHECK_TICKS:
                continue
            packets = [p for p in state["packets"] if p[0] >= state["last_ts"] - self.window_s]
            if len(packets) >= MIN_PACKETS:
                due.append((flow, state, packets))
        if not due:
            return
        frames = [self._frame(p) for *_, p in due]
        outcomes, _ = self._predict(frames, [self.window_s] * len(due), early=False)
        for (flow, state, _), outcome in zip(due, outcomes):
            state["checked"] = tick
            better = outcome["predicted"]
            if outcome["abstained"] or outcome["confidence"] < RECLASS_CONFIDENCE or better == state["class"]:
                state["alt"], state["alt_count"] = None, 0
                continue
            state["alt_count"] = state["alt_count"] + 1 if state["alt"] == better else 1
            state["alt"] = better
            if state["alt_count"] >= RECLASS_CONFIRM and self.qos.classify_flow(flow, better, replace=True):
                self.reclassifications.append({"tick": tick, "flow": list(flow), "from": state["class"],
                                               "to": better, "confidence": outcome["confidence"],
                                               "truth": self._truth(flow)})
                state["class"], state["alt"], state["alt_count"] = better, None, 0

    # ------------------------------------------------------------ scoring

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
        final = {tuple(d["flow"]): d["predicted"] for d in self.decisions}
        for r in self.reclassifications:
            final[tuple(r["flow"])] = r["to"]
        truth = {tuple(d["flow"]): d["truth"] for d in scored}
        latencies = [d["observed_s"] for d in self.decisions]
        return {
            "enabled": self.enabled,
            "mode": "slicenet_all" if self.all_ues else "slicenet",
            "flows_classified": len(self.decisions),
            "fallback_decisions": sum(d["fallback"] for d in self.decisions),
            "abstentions": self.abstentions,
            "accuracy": round(sum(d["predicted"] == d["truth"] for d in scored) / len(scored), 4) if scored else None,
            "final_accuracy": round(sum(final[f] == t for f, t in truth.items()) / len(truth), 4) if truth else None,
            "reclassified": len(self.reclassifications),
            "reclassified_correct": sum(r["to"] == r["truth"] for r in self.reclassifications if r["truth"]),
            "median_time_to_decision_s": round(float(np.median(latencies)), 3) if latencies else None,
            "mean_confidence": round(float(np.mean([d["confidence"] for d in self.decisions])), 4)
            if self.decisions else None,
            "decisions": self.decisions,
            "reclassifications": self.reclassifications,
        }
