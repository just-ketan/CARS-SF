"""
Extract flow features from PCAP files aligned to the CARS-SF feature schema.
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

import numpy as np

from core.config import load_features
from features.schema_mapper import map_to_schema


class FlowFeatureExtractor:
    """Extract per-flow features from PCAP captures using Scapy."""

    def __init__(
        self,
        pcap_paths: list[str],
        telemetry_snapshots: list[dict[str, Any]] | None = None,
        spawn_metadata: list[dict[str, Any]] | None = None,
        scenario_context: dict[str, Any] | None = None,
    ):
        self.pcap_paths = pcap_paths
        self.telemetry = telemetry_snapshots or []
        self.spawn_metadata = spawn_metadata or []
        self.scenario_context = scenario_context or {}
        self.feature_config = load_features()

    def extract(self) -> list[dict[str, Any]]:
        all_records: list[dict[str, Any]] = []
        for pcap_path in self.pcap_paths:
            records = self._extract_from_pcap(pcap_path)
            all_records.extend(records)

        if not all_records and self.telemetry:
            all_records = self._extract_from_telemetry()

        return all_records

    def _extract_from_pcap(self, pcap_path: str) -> list[dict[str, Any]]:
        if not os.path.exists(pcap_path):
            return []

        try:
            from scapy.all import IP, TCP, UDP, rdpcap
        except ImportError:
            return []

        try:
            packets = rdpcap(pcap_path)
        except Exception:
            return []

        flows: dict[tuple, list] = defaultdict(list)
        for pkt in packets:
            if IP not in pkt:
                continue
            src_ip = pkt[IP].src
            dst_ip = pkt[IP].dst
            proto = pkt[IP].proto
            src_port, dst_port = 0, 0
            tcp_syn = tcp_ack = tcp_fin = tcp_rst = 0
            tcp_window = 65535
            ttl = int(pkt[IP].ttl)
            dscp = (int(pkt[IP].tos) >> 2) & 0x3F

            if TCP in pkt:
                src_port, dst_port = int(pkt[TCP].sport), int(pkt[TCP].dport)
                flags = int(pkt[TCP].flags)
                tcp_syn = 1 if flags & 0x02 else 0
                tcp_ack = 1 if flags & 0x10 else 0
                tcp_fin = 1 if flags & 0x01 else 0
                tcp_rst = 1 if flags & 0x04 else 0
                tcp_window = int(pkt[TCP].window)
            elif UDP in pkt:
                src_port, dst_port = int(pkt[UDP].sport), int(pkt[UDP].dport)

            key = (src_ip, dst_ip, src_port, dst_port, proto)
            flows[key].append({
                "pkt": pkt, "time": float(pkt.time), "len": len(pkt),
                "ttl": ttl, "dscp": dscp,
                "tcp_syn": tcp_syn, "tcp_ack": tcp_ack,
                "tcp_fin": tcp_fin, "tcp_rst": tcp_rst,
                "tcp_window": tcp_window,
            })

        records = []
        avg_telemetry = self._average_telemetry()
        flow_idx = 0

        for flow_key, entries in flows.items():
            src_ip, dst_ip, src_port, dst_port, proto = flow_key
            timestamps = [e["time"] for e in entries]
            lengths = [e["len"] for e in entries]

            duration_ms = (max(timestamps) - min(timestamps)) * 1000 if len(timestamps) > 1 else 0
            packet_count = len(entries)
            byte_count = sum(lengths)

            duration_s = max(duration_ms / 1000, 0.001)
            packet_rate = packet_count / duration_s
            byte_rate = byte_count / duration_s
            throughput_mbps = (byte_count * 8) / (duration_s * 1_000_000)

            iats = np.diff(timestamps) * 1000 if len(timestamps) > 1 else np.array([0.0])
            mean_iat = float(np.mean(iats))
            std_iat = float(np.std(iats))

            spawn = self._match_spawn_metadata(dst_ip, dst_port)
            latency_ms = mean_iat * 2 if mean_iat > 0 else 1.0
            jitter_ms = std_iat
            loss_rate = avg_telemetry.get("tc_drops", 0) / max(packet_count, 1) * 100

            partial = {
                "src_ip": src_ip, "dst_ip": dst_ip,
                "src_port": src_port, "dst_port": dst_port,
                "transport_protocol": proto,
                "flow_duration_ms": round(duration_ms, 3),
                "packet_count": packet_count, "byte_count": byte_count,
                "packet_rate_pps": round(packet_rate, 3),
                "byte_rate_bps": round(byte_rate * 8, 3),
                "mean_iat_ms": round(mean_iat, 3), "std_iat_ms": round(std_iat, 3),
                "min_iat_ms": round(float(np.min(iats)), 3),
                "max_iat_ms": round(float(np.max(iats)), 3),
                "mean_packet_size": round(float(np.mean(lengths)), 3),
                "median_packet_size": round(float(np.median(lengths)), 3),
                "min_packet_size": int(min(lengths)), "max_packet_size": int(max(lengths)),
                "throughput_mbps": round(throughput_mbps, 3),
                "goodput_mbps": round(throughput_mbps * (1 - loss_rate / 100), 3),
                "end_to_end_latency_ms": round(latency_ms, 3),
                "jitter_ms": round(jitter_ms, 3),
                "packet_loss_rate": round(min(loss_rate, 100.0), 3),
                "queue_drops": avg_telemetry.get("tc_drops", 0),
                "ovs_bytes": avg_telemetry.get("ovs_bytes", 0),
                "link_utilization_pct": avg_telemetry.get("link_utilization_pct", 0),
                "network_load_pct": self.scenario_context.get(
                    "network_load_pct", avg_telemetry.get("link_utilization_pct", 0)
                ),
                "ttl": entries[0]["ttl"], "dscp": entries[0]["dscp"],
                "tcp_syn_count": sum(e["tcp_syn"] for e in entries),
                "tcp_ack_count": sum(e["tcp_ack"] for e in entries),
                "tcp_fin_count": sum(e["tcp_fin"] for e in entries),
                "tcp_rst_count": sum(e["tcp_rst"] for e in entries),
                "tcp_window_size": entries[0]["tcp_window"],
                "udp_packet_count": packet_count if proto == 17 else 0,
                "flow_start_time": min(timestamps), "flow_end_time": max(timestamps),
                "_packet_lengths": lengths,
                "service_class": spawn.get("service_class", "unknown"),
                "application_id": spawn.get("application_id", "unknown"),
                "slice_type_label": spawn.get("slice_type", "eMBB"),
                "priority_level": spawn.get("priority", 4),
                "sla_satisfied": latency_ms <= spawn.get("latency_requirement_ms", 100),
                "reward_score": self._compute_reward(throughput_mbps, latency_ms, spawn),
            }
            records.append(map_to_schema(
                partial, flow_index=flow_idx, scenario_context=self.scenario_context
            ))
            flow_idx += 1

        return records

    def _extract_from_telemetry(self) -> list[dict[str, Any]]:
        """Fallback: create schema-aligned records from telemetry when PCAP is empty."""
        records = []
        flow_idx = 0
        for snap in self.telemetry:
            for spawn in self.spawn_metadata:
                partial = {
                    "tick": snap.get("tick", 0),
                    "flow_duration_ms": 1000.0,
                    "packet_count": max(int(snap.get("ovs_bytes", 0) // 1500), 1),
                    "byte_count": snap.get("ovs_bytes", 0),
                    "throughput_mbps": snap.get("ovs_bytes", 0) / 1_000_000,
                    "end_to_end_latency_ms": 5.0,
                    "jitter_ms": 1.0,
                    "packet_loss_rate": snap.get("tc_drops", 0),
                    "queue_drops": snap.get("tc_drops", 0),
                    "ovs_bytes": snap.get("ovs_bytes", 0),
                    "link_utilization_pct": snap.get("link_utilization_pct", 0),
                    "network_load_pct": self.scenario_context.get(
                        "network_load_pct", snap.get("link_utilization_pct", 0)
                    ),
                    "service_class": spawn.get("service_class", "unknown"),
                    "application_id": spawn.get("application_id", "unknown"),
                    "slice_type_label": spawn.get("slice_type", "eMBB"),
                    "priority_level": spawn.get("priority", 4),
                    "sla_satisfied": True,
                    "reward_score": 80.0,
                    "_packet_lengths": [1500] * 10,
                }
                records.append(map_to_schema(
                    partial, flow_index=flow_idx, scenario_context=self.scenario_context
                ))
                flow_idx += 1
        return records

    def _match_spawn_metadata(self, dst_ip: str, dst_port: int) -> dict[str, Any]:
        for spawn in self.spawn_metadata:
            if spawn.get("server_ip") == dst_ip and spawn.get("port") == dst_port:
                return spawn
        for spawn in self.spawn_metadata:
            if spawn.get("server_ip") == dst_ip:
                return spawn
        return {}

    def _average_telemetry(self) -> dict[str, Any]:
        if not self.telemetry:
            return {}
        keys = self.telemetry[0].keys()
        return {
            k: sum(s.get(k, 0) for s in self.telemetry) / len(self.telemetry)
            for k in keys if k != "tick"
        }

    def _compute_reward(
        self, throughput: float, latency: float, spawn: dict[str, Any]
    ) -> float:
        latency_req = spawn.get("latency_requirement_ms", 100)
        latency_score = max(0, 100 - (latency / latency_req) * 50)
        throughput_score = min(100, throughput * 10)
        return round((latency_score + throughput_score) / 2, 2)
