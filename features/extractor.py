"""
Extract windowed application-flow features from endpoint packet captures.

A record is one application flow of one UE over one time window (default
5 s). QoS fields are measured, not estimated:

  end_to_end_latency_ms   mean one-way delay of delivered data-direction packets
  jitter_ms               mean |Δ one-way delay| of consecutive packets (RFC 3550 style)
  packet_loss_rate        % of data-direction packets sent but never received
  queueing_delay_ms       mean one-way delay above the flow's minimum (propagation)
  throughput/goodput      delivered bytes / window (goodput excludes retransmissions)

The *data direction* is whichever direction carried more bytes in the window
(e.g. UE→server for telemetry uploads, server→UE for video or downloads).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from core.config import load_features
from features.packet_capture import CapturePoint, match_packets
from features.schema_mapper import map_to_schema
from features.shape import SHAPE_FEATURES, frame_from_matched, packet_sequence, shape_features

TCP_FIN, TCP_SYN, TCP_RST, TCP_ACK = 0x01, 0x02, 0x04, 0x10
IDLE_GAP_S = 0.5
MIN_PACKETS = 2


class FlowFeatureExtractor:
    """Builds schema-aligned flow-window records from matched endpoint captures."""

    def __init__(
        self,
        capture_points: list[CapturePoint] | None = None,
        telemetry_snapshots: list[dict[str, Any]] | None = None,
        spawn_metadata: list[dict[str, Any]] | None = None,
        scenario_context: dict[str, Any] | None = None,
        ue_ips: set[str] | None = None,
        window_s: float = 5.0,
    ):
        self.capture_points = capture_points or []
        self.telemetry = telemetry_snapshots or []
        self.spawn_metadata = spawn_metadata or []
        self.scenario_context = scenario_context or {}
        self.ue_ips = ue_ips or {s["host_ip"] for s in self.spawn_metadata if "host_ip" in s}
        self.window_s = window_s
        self.feature_config = load_features()
        self.sequences: list[np.ndarray] = []   # aligned with returned records

    # ------------------------------------------------------------------ public

    def extract(self) -> list[dict[str, Any]]:
        packets = self.matched_packets()
        if packets.empty:
            return []
        return self.records_from_packets(packets)

    def matched_packets(self) -> pd.DataFrame:
        return match_packets(self.capture_points, self.ue_ips)

    def records_from_packets(self, packets: pd.DataFrame) -> list[dict[str, Any]]:
        packets = packets[packets["proto"].isin([6, 17])].copy()  # ICMP = probes, not apps
        if packets.empty:
            return []
        spawns = [self._match_flow(flow) for flow in packets["flow"]]
        packets["spawn_idx"] = [s if s is not None else -1 for s in spawns]
        packets = packets[packets["spawn_idx"] >= 0]
        if packets.empty:
            return []

        t0 = packets["tx_ts"].min()
        packets["window"] = ((packets["tx_ts"] - t0) // self.window_s).astype(int)
        # Propagation floor per (spawn, direction) over the whole run.
        base_owd = packets.groupby(["spawn_idx", "direction"])["owd_ms"].min()

        records = []
        for (spawn_idx, window), group in packets.groupby(["spawn_idx", "window"], sort=True):
            if len(group) < MIN_PACKETS:
                continue
            spawn = self.spawn_metadata[spawn_idx]
            window_start = t0 + window * self.window_s
            partial = self._window_features(group, spawn, base_owd, spawn_idx)
            partial.update(self._telemetry_features(window_start, window_start + self.window_s))
            partial["window_index"] = int(window)
            partial["ue_host"] = spawn["host"]
            shape_frame = frame_from_matched(group)
            shape = shape_features(shape_frame, self.window_s)
            partial.update({f"shape_{k}": round(v, 6) for k, v in shape.items()})
            self.sequences.append(packet_sequence(shape_frame))
            partial["active_flows"] = int(
                packets.loc[packets["window"] == window, "spawn_idx"].nunique()
            )
            records.append(map_to_schema(
                partial, flow_index=len(records), scenario_context=self.scenario_context
            ))
        return records

    # -------------------------------------------------------------- matching

    def _match_flow(self, flow: tuple) -> int | None:
        """Map a canonical (ue_ip, peer_ip, proto, ue_port, peer_port) flow to a spawn."""
        ue_ip, peer_ip, proto, ue_port, peer_port = flow
        proto_name = {6: "tcp", 17: "udp"}.get(proto)
        for idx, spawn in enumerate(self.spawn_metadata):
            if (
                spawn.get("host_ip") == ue_ip
                and spawn.get("server_ip") == peer_ip
                and spawn.get("protocol", proto_name) == proto_name
                and spawn.get("port") in (ue_port, peer_port)
            ):
                return idx
        return None

    def _match_spawn_metadata(
        self, src_ip: str, dst_ip: str, src_port: int, dst_port: int, proto: int
    ) -> dict[str, Any]:
        """Spawn record for a packet in either direction ({} if not an application)."""
        if src_ip in self.ue_ips:
            flow = (src_ip, dst_ip, proto, src_port, dst_port)
        else:
            flow = (dst_ip, src_ip, proto, dst_port, src_port)
        idx = self._match_flow(flow)
        return self.spawn_metadata[idx] if idx is not None else {}

    # -------------------------------------------------------------- features

    def _window_features(self, group: pd.DataFrame, spawn, base_owd, spawn_idx) -> dict[str, Any]:
        group = group.sort_values("tx_ts")
        fwd, bwd = group[group["direction"] == 1], group[group["direction"] == -1]
        data_dir = 1 if fwd["ip_len"].sum() >= bwd["ip_len"].sum() else -1
        data = group[(group["direction"] == data_dir) & ~group["in_flight"]]
        delivered = data[data["rx_ts"].notna()].sort_values("rx_ts")

        ts = group["tx_ts"].to_numpy()
        iats = np.diff(ts) * 1000 if len(ts) > 1 else np.array([0.0])
        sizes = group["ip_len"].to_numpy()

        owd = delivered["owd_ms"].to_numpy()
        latency = float(np.mean(owd)) if len(owd) else np.nan
        jitter = float(np.mean(np.abs(np.diff(owd)))) if len(owd) > 1 else 0.0
        floor = base_owd.get((spawn_idx, data_dir), np.nan)
        queueing = float(np.mean(owd - floor)) if len(owd) and not np.isnan(floor) else 0.0
        loss = (1 - len(delivered) / len(data)) * 100 if len(data) else 0.0

        retrans = delivered["retransmission"].to_numpy(dtype=bool)
        throughput = delivered["ip_len"].sum() * 8 / self.window_s / 1e6
        goodput = delivered.loc[~retrans, "payload_len"].sum() * 8 / self.window_s / 1e6
        tcp_data = group[(group["proto"] == 6) & (group["payload_len"] > 0)]

        idle_ms = float(iats[iats > IDLE_GAP_S * 1000].sum()) if len(iats) else 0.0
        duration_ms = float((ts[-1] - ts[0]) * 1000) if len(ts) > 1 else 0.0
        sla = spawn.get("sla", {})
        reward = self._sla_score(latency, jitter, loss, sla, spawn)
        flags = group["tcp_flags"].to_numpy()

        return {
            "flow_duration_ms": round(duration_ms, 3),
            "packet_count": int(len(group)),
            "byte_count": int(sizes.sum()),
            "forward_packet_count": int(len(fwd)),
            "backward_packet_count": int(len(bwd)),
            "forward_byte_count": int(fwd["ip_len"].sum()),
            "backward_byte_count": int(bwd["ip_len"].sum()),
            "packet_rate_pps": round(len(group) / self.window_s, 3),
            "byte_rate_bps": round(sizes.sum() * 8 / self.window_s, 3),
            "flow_start_time": float(ts[0]),
            "flow_end_time": float(ts[-1]),
            "ttl": int(group["ttl"].iloc[0]),
            "dscp": int(group["dscp"].mode().iloc[0]),
            "transport_protocol": int(group["proto"].iloc[0]),
            "src_port": int(group["flow"].iloc[0][3]),
            "dst_port": int(group["flow"].iloc[0][4]),
            "tcp_syn_count": int(((flags & TCP_SYN) > 0).sum()),
            "tcp_ack_count": int(((flags & TCP_ACK) > 0).sum()),
            "tcp_fin_count": int(((flags & TCP_FIN) > 0).sum()),
            "tcp_rst_count": int(((flags & TCP_RST) > 0).sum()),
            "tcp_window_size": int(group["tcp_win"].mean()) if (group["proto"] == 6).any() else 0,
            "tcp_retransmissions": int(group["retransmission"].sum()),
            "retransmission_rate": round(
                float(tcp_data["retransmission"].mean()) if len(tcp_data) else 0.0, 4
            ),
            "udp_packet_count": int((group["proto"] == 17).sum()),
            "mean_iat_ms": round(float(np.mean(iats)), 3),
            "std_iat_ms": round(float(np.std(iats)), 3),
            "min_iat_ms": round(float(np.min(iats)), 3),
            "max_iat_ms": round(float(np.max(iats)), 3),
            "forward_mean_iat_ms": _mean_iat(fwd["tx_ts"].to_numpy()),
            "backward_mean_iat_ms": _mean_iat(bwd["tx_ts"].to_numpy()),
            "flow_active_time_ms": round(max(duration_ms - idle_ms, 0.0), 3),
            "flow_idle_time_ms": round(idle_ms, 3),
            "mean_packet_size": round(float(np.mean(sizes)), 3),
            "median_packet_size": round(float(np.median(sizes)), 3),
            "min_packet_size": int(sizes.min()),
            "max_packet_size": int(sizes.max()),
            "_packet_lengths": sizes.tolist(),
            "end_to_end_latency_ms": round(latency, 3) if not np.isnan(latency) else np.nan,
            "p95_latency_ms": round(float(np.percentile(owd, 95)), 3) if len(owd) else np.nan,
            "jitter_ms": round(jitter, 3),
            "packet_loss_rate": round(loss, 3),
            "queueing_delay_ms": round(queueing, 3),
            "throughput_mbps": round(float(throughput), 4),
            "goodput_mbps": round(float(min(goodput, throughput)), 4),
            "service_class": spawn["service_class"],
            "application_id": spawn["application_id"],
            "slice_type_label": spawn.get("slice_type", "eMBB"),
            "priority_level": spawn.get("priority", 4),
            "sla_satisfied": bool(reward >= 100.0 - 1e-9),
            "reward_score": reward,
            "qos_satisfaction_score": reward,
        }

    @staticmethod
    def _sla_score(latency: float, jitter: float, loss: float, sla: dict, spawn: dict) -> float:
        """100 × mean of per-target satisfaction (latency, jitter, loss), each capped at 1."""
        lat_target = sla.get("latency_ms", spawn.get("latency_requirement_ms", 100))
        parts = []
        if not np.isnan(latency):
            parts.append(min(1.0, lat_target / max(latency, 1e-6)))
        parts.append(min(1.0, sla.get("jitter_ms", 50) / max(jitter, 1e-6)))
        parts.append(min(1.0, sla.get("loss_pct", 5) / max(loss, 1e-6)))
        return round(100 * float(np.mean(parts)), 2)

    def _telemetry_features(self, start: float, end: float) -> dict[str, Any]:
        snaps = [s for s in self.telemetry if start <= s.get("timestamp", -1) < end]
        if not snaps:
            snaps = self.telemetry[-1:] if self.telemetry else []
        if not snaps:
            return {}
        return {
            "link_utilization_pct": round(float(np.mean([s.get("link_utilization_pct", 0) for s in snaps])), 3),
            "queue_drops": int(sum(s.get("tc_drops", 0) for s in snaps)),
            "ovs_bytes": int(np.mean([s.get("ovs_bytes", 0) for s in snaps])),
            "host_cpu_pct": round(float(np.mean([s.get("host_cpu_pct", 0) for s in snaps])), 2),
            "host_mem_pct": round(float(np.mean([s.get("host_mem_pct", 0) for s in snaps])), 2),
        }

    # ------------------------------------------------------- telemetry-only path

    def _extract_from_telemetry(self) -> list[dict[str, Any]]:
        """Fallback when no captures exist: one record per (tick, spawn), clearly marked."""
        records = []
        for snap in self.telemetry:
            for spawn in self.spawn_metadata:
                service = spawn.get("service_class", "unknown")
                tput = snap.get("service_throughput_mbps", {}).get(service, 0.0)
                rtt = snap.get("service_rtt_ms", {}).get(service)
                partial = {
                    "flow_duration_ms": 1000.0,
                    "throughput_mbps": tput,
                    "end_to_end_latency_ms": rtt / 2 if rtt else np.nan,
                    "queue_drops": snap.get("tc_drops", 0),
                    "link_utilization_pct": snap.get("link_utilization_pct", 0),
                    "service_class": service,
                    "application_id": spawn.get("application_id", "unknown"),
                    "slice_type_label": spawn.get("slice_type", "eMBB"),
                    "priority_level": spawn.get("priority", 4),
                    "data_source": "telemetry_fallback",
                }
                records.append(map_to_schema(
                    partial, flow_index=len(records), scenario_context=self.scenario_context
                ))
        return records

    def _service_qos(self, service: str) -> tuple[float | None, float, float]:
        """Probe-based RTT mean/jitter and loss for a service (online monitoring view)."""
        rtts = [s.get("service_rtt_ms", {}).get(service, "missing") for s in self.telemetry]
        rtts = [r for r in rtts if r != "missing"]
        answered = [r for r in rtts if r is not None]
        probe_loss = (len(rtts) - len(answered)) / len(rtts) * 100 if rtts else 0.0

        queue_loss = 0.0
        if self.telemetry:
            stats = self.telemetry[-1].get("tc_class_stats", {}).get(service)
            if stats:
                attempted = stats["sent_packets"] + stats["dropped"]
                queue_loss = stats["dropped"] / attempted * 100 if attempted else 0.0

        if not answered:
            return None, 0.0, max(probe_loss, queue_loss)
        return (
            float(np.mean(answered)),
            float(np.mean(np.abs(np.diff(answered)))) if len(answered) > 1 else 0.0,
            max(probe_loss, queue_loss),
        )

    def _average_telemetry(self) -> dict[str, Any]:
        if not self.telemetry:
            return {}
        keys = [
            k for k, v in self.telemetry[0].items()
            if k != "tick" and isinstance(v, (int, float)) and not isinstance(v, bool)
        ]
        return {
            k: sum(s.get(k, 0) for s in self.telemetry) / len(self.telemetry)
            for k in keys
        }


def _mean_iat(ts: np.ndarray) -> float:
    return round(float(np.mean(np.diff(ts)) * 1000), 3) if len(ts) > 1 else 0.0
