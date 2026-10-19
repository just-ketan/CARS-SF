"""
Traffic-shape features: what a classifier at the gateway can observe.

Only sender-side packet sizes, timing, direction and TCP flags are used — never
QoS outcomes (delay, loss, delivered throughput), which depend on the slice the
flow was put in and would make classification circular. The same functions
build the offline dataset and the online (in-loop) classifier inputs.

Input frame columns: ts, direction (+1 UE→server, -1 server→UE), ip_len,
proto, tcp_flags, payload_len.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SEQ_LEN = 32
SEQ_CHANNELS = 3   # signed size / 1500, log1p(inter-arrival ms), is_tcp_control

SHAPE_FEATURES = [
    "packet_count", "byte_count", "forward_packet_count", "backward_packet_count",
    "forward_byte_count", "backward_byte_count", "forward_byte_share",
    "packet_rate_pps", "byte_rate_bps",
    "mean_iat_ms", "std_iat_ms", "min_iat_ms", "max_iat_ms", "cv_iat",
    "forward_mean_iat_ms", "backward_mean_iat_ms",
    "mean_packet_size", "median_packet_size", "min_packet_size", "max_packet_size",
    "std_packet_size", "forward_mean_size", "backward_mean_size",
    "flow_active_time_ms", "flow_idle_time_ms", "burst_count", "mean_burst_packets",
    "tcp_syn_count", "tcp_fin_count", "tcp_rst_count", "small_packet_share",
]

IDLE_GAP_S = 0.5
BURST_GAP_S = 0.005


def shape_features(group: pd.DataFrame, window_s: float) -> dict[str, float]:
    g = group.sort_values("ts")
    ts = g["ts"].to_numpy()
    sizes = g["ip_len"].to_numpy(dtype=float)
    direction = g["direction"].to_numpy()
    fwd, bwd = sizes[direction == 1], sizes[direction == -1]
    iats = np.diff(ts) if len(ts) > 1 else np.array([0.0])
    flags = g["tcp_flags"].to_numpy(dtype=int) if "tcp_flags" in g else np.zeros(len(g), int)
    bursts = np.split(np.arange(len(ts)), np.where(iats > BURST_GAP_S)[0] + 1) if len(ts) > 1 else [np.arange(len(ts))]
    idle = float(iats[iats > IDLE_GAP_S].sum()) if len(iats) else 0.0
    duration = float(ts[-1] - ts[0]) if len(ts) > 1 else 0.0
    mean_iat = float(np.mean(iats)) if len(iats) else 0.0
    total = sizes.sum()
    return {
        "packet_count": float(len(sizes)),
        "byte_count": float(total),
        "forward_packet_count": float(len(fwd)),
        "backward_packet_count": float(len(bwd)),
        "forward_byte_count": float(fwd.sum()),
        "backward_byte_count": float(bwd.sum()),
        "forward_byte_share": float(fwd.sum() / total) if total else 0.0,
        "packet_rate_pps": len(sizes) / window_s,
        "byte_rate_bps": total * 8 / window_s,
        "mean_iat_ms": mean_iat * 1000,
        "std_iat_ms": float(np.std(iats)) * 1000,
        "min_iat_ms": float(np.min(iats)) * 1000,
        "max_iat_ms": float(np.max(iats)) * 1000,
        "cv_iat": float(np.std(iats) / mean_iat) if mean_iat > 0 else 0.0,
        "forward_mean_iat_ms": _mean_iat(ts[direction == 1]),
        "backward_mean_iat_ms": _mean_iat(ts[direction == -1]),
        "mean_packet_size": float(np.mean(sizes)),
        "median_packet_size": float(np.median(sizes)),
        "min_packet_size": float(np.min(sizes)),
        "max_packet_size": float(np.max(sizes)),
        "std_packet_size": float(np.std(sizes)),
        "forward_mean_size": float(np.mean(fwd)) if len(fwd) else 0.0,
        "backward_mean_size": float(np.mean(bwd)) if len(bwd) else 0.0,
        "flow_active_time_ms": max(duration - idle, 0.0) * 1000,
        "flow_idle_time_ms": idle * 1000,
        "burst_count": float(len(bursts)),
        "mean_burst_packets": float(np.mean([len(b) for b in bursts])),
        "tcp_syn_count": float(((flags & 0x02) > 0).sum()),
        "tcp_fin_count": float(((flags & 0x01) > 0).sum()),
        "tcp_rst_count": float(((flags & 0x04) > 0).sum()),
        "small_packet_share": float((sizes < 200).mean()),
    }


def packet_sequence(group: pd.DataFrame, length: int = SEQ_LEN) -> np.ndarray:
    """First ``length`` packets as (signed size, log IAT, TCP control) channels."""
    g = group.sort_values("ts")
    ts = g["ts"].to_numpy()
    sizes = g["ip_len"].to_numpy(dtype=float) * g["direction"].to_numpy()
    iats = np.concatenate([[0.0], np.diff(ts)]) * 1000
    control = ((g["payload_len"].to_numpy() == 0) & (g["proto"].to_numpy() == 6)).astype(float)
    seq = np.zeros((SEQ_CHANNELS, length), dtype=np.float32)
    n = min(length, len(g))
    seq[0, :n] = sizes[:n] / 1500.0
    seq[1, :n] = np.log1p(iats[:n])
    seq[2, :n] = control[:n]
    return seq


def frame_from_matched(packets: pd.DataFrame) -> pd.DataFrame:
    """Adapt matched-packet rows (tx_ts, …) to the shape-feature input layout."""
    return packets.rename(columns={"tx_ts": "ts"})[
        ["ts", "direction", "ip_len", "proto", "tcp_flags", "payload_len"]
    ]


def _mean_iat(ts: np.ndarray) -> float:
    return float(np.mean(np.diff(ts)) * 1000) if len(ts) > 1 else 0.0
