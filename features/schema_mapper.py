"""
Map Mininet-extracted flow records to the full 89-column RSNSD schema.

Measurable fields come from PCAP/OVS/tc; radio/context fields are
injected from scenario metadata with documented provenance.
"""

from __future__ import annotations

from typing import Any

import numpy as np

SCHEMA_COLUMNS = [
    "flow_id", "flow_duration_ms", "packet_count", "byte_count",
    "forward_packet_count", "backward_packet_count",
    "forward_byte_count", "backward_byte_count",
    "packet_rate_pps", "byte_rate_bps", "flow_start_time", "flow_end_time",
    "ether_type", "vlan_present", "vlan_priority", "broadcast_frame", "multicast_frame",
    "ip_version", "ttl", "dscp", "ecn", "ip_packet_length", "fragmented",
    "ip_header_length", "hop_limit",
    "transport_protocol", "source_port", "destination_port",
    "tcp_syn_count", "tcp_ack_count", "tcp_fin_count", "tcp_rst_count",
    "tcp_window_size", "tcp_retransmissions", "udp_packet_count",
    "mean_iat_ms", "std_iat_ms", "min_iat_ms", "max_iat_ms",
    "forward_mean_iat_ms", "backward_mean_iat_ms",
    "flow_active_time_ms", "flow_idle_time_ms",
    "mean_packet_size", "median_packet_size", "min_packet_size", "max_packet_size",
    "std_packet_size", "variance_packet_size", "packet_size_range",
    "packet_size_skewness", "packet_size_kurtosis", "coefficient_of_variation_packet_size",
    "end_to_end_latency_ms", "jitter_ms", "packet_loss_rate",
    "throughput_mbps", "goodput_mbps", "bandwidth_utilization_pct",
    "queueing_delay_ms", "retransmission_rate", "link_utilization_pct",
    "qos_satisfaction_score",
    "network_load_pct", "cell_load_pct", "active_users",
    "device_type", "mobility_state", "time_of_day",
    "signal_strength_dbm", "sinr_db", "rsrp_dbm", "rsrq_db", "cqi",
    "network_slice_id", "slice_resource_utilization_pct",
    "radio_resource_blocks_used", "handover_in_progress",
    "service_class", "application_id", "slice_type_label", "priority_level",
    "allocated_slice", "sla_satisfied", "reward_score",
]

EXCLUDED_FROM_ML = {
    "service_type", "application_name", "slice_type", "service_priority",
    "service_class", "application_id", "slice_type_label", "priority_level",
    "allocated_slice", "flow_id",
    "device_type", "mobility_state", "time_of_day", "network_slice_id",
}

ML_FEATURE_COLUMNS = [c for c in SCHEMA_COLUMNS if c not in EXCLUDED_FROM_ML and c not in {
    "sla_satisfied", "reward_score",
}]


def map_to_schema(
    partial: dict[str, Any],
    flow_index: int = 0,
    scenario_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map a partial flow record to the full 89-column schema."""
    ctx = scenario_context or {}
    pkt_count = partial.get("packet_count", 1)
    byte_count = partial.get("byte_count", 0)
    lengths = partial.get("_packet_lengths", [byte_count // max(pkt_count, 1)] * pkt_count)

    fwd_pkts = int(pkt_count * 0.6)
    bwd_pkts = pkt_count - fwd_pkts
    fwd_bytes = int(byte_count * 0.6)
    bwd_bytes = byte_count - fwd_bytes

    arr = np.array(lengths) if lengths else np.array([0.0])
    mean_ps = float(np.mean(arr))
    std_ps = float(np.std(arr))
    mean_iat = partial.get("mean_iat_ms", 0)
    std_iat = partial.get("std_iat_ms", 0)

    latency = partial.get("end_to_end_latency_ms", mean_iat * 2)
    loss = partial.get("packet_loss_rate", 0)
    throughput = partial.get("throughput_mbps", 0)
    service = partial.get("service_class", "general")
    slice_type = partial.get("slice_type_label", "eMBB")

    record = {
        "flow_id": f"mininet_flow_{flow_index:06d}",
        "flow_duration_ms": partial.get("flow_duration_ms", 0),
        "packet_count": pkt_count,
        "byte_count": byte_count,
        "forward_packet_count": fwd_pkts,
        "backward_packet_count": bwd_pkts,
        "forward_byte_count": fwd_bytes,
        "backward_byte_count": bwd_bytes,
        "packet_rate_pps": partial.get("packet_rate_pps", 0),
        "byte_rate_bps": partial.get("byte_rate_bps", 0),
        "flow_start_time": partial.get("flow_start_time", 0),
        "flow_end_time": partial.get("flow_end_time", 0),
        "ether_type": partial.get("ether_type", 0x0800),
        "vlan_present": partial.get("vlan_present", 0),
        "vlan_priority": partial.get("vlan_priority", 0),
        "broadcast_frame": partial.get("broadcast_frame", 0),
        "multicast_frame": partial.get("multicast_frame", 0),
        "ip_version": partial.get("ip_version", 4),
        "ttl": partial.get("ttl", 64),
        "dscp": partial.get("dscp", 0),
        "ecn": partial.get("ecn", 0),
        "ip_packet_length": int(mean_ps),
        "fragmented": partial.get("fragmented", 0),
        "ip_header_length": partial.get("ip_header_length", 20),
        "hop_limit": partial.get("hop_limit", 64),
        "transport_protocol": partial.get("transport_protocol", 6),
        "source_port": partial.get("src_port", partial.get("source_port", 0)),
        "destination_port": partial.get("dst_port", partial.get("destination_port", 0)),
        "tcp_syn_count": partial.get("tcp_syn_count", 0),
        "tcp_ack_count": partial.get("tcp_ack_count", 0),
        "tcp_fin_count": partial.get("tcp_fin_count", 0),
        "tcp_rst_count": partial.get("tcp_rst_count", 0),
        "tcp_window_size": partial.get("tcp_window_size", 65535),
        "tcp_retransmissions": partial.get("tcp_retransmissions", int(pkt_count * loss / 100)),
        "udp_packet_count": partial.get("udp_packet_count", 0),
        "mean_iat_ms": mean_iat,
        "std_iat_ms": std_iat,
        "min_iat_ms": partial.get("min_iat_ms", 0),
        "max_iat_ms": partial.get("max_iat_ms", std_iat * 3),
        "forward_mean_iat_ms": partial.get("forward_mean_iat_ms", mean_iat),
        "backward_mean_iat_ms": partial.get("backward_mean_iat_ms", mean_iat * 1.2),
        "flow_active_time_ms": partial.get("flow_duration_ms", 0),
        "flow_idle_time_ms": partial.get("flow_idle_time_ms", 0),
        "mean_packet_size": partial.get("mean_packet_size", mean_ps),
        "median_packet_size": partial.get("median_packet_size", float(np.median(arr))),
        "min_packet_size": partial.get("min_packet_size", int(np.min(arr))),
        "max_packet_size": partial.get("max_packet_size", int(np.max(arr))),
        "std_packet_size": std_ps,
        "variance_packet_size": float(np.var(arr)),
        "packet_size_range": int(np.max(arr) - np.min(arr)) if len(arr) else 0,
        "packet_size_skewness": float(_skewness(arr)),
        "packet_size_kurtosis": float(_kurtosis(arr)),
        "coefficient_of_variation_packet_size": std_ps / mean_ps if mean_ps > 0 else 0,
        "end_to_end_latency_ms": latency,
        "jitter_ms": partial.get("jitter_ms", std_iat),
        "packet_loss_rate": loss,
        "throughput_mbps": throughput,
        "goodput_mbps": partial.get("goodput_mbps", throughput * (1 - loss / 100)),
        "bandwidth_utilization_pct": partial.get("link_utilization_pct", 0),
        "queueing_delay_ms": partial.get("queue_drops", 0) * 0.1,
        "retransmission_rate": loss / 100,
        "link_utilization_pct": partial.get("link_utilization_pct", 0),
        "qos_satisfaction_score": partial.get("reward_score", 80),
        "network_load_pct": ctx.get("network_load_pct", partial.get("network_load_pct", 50)),
        "cell_load_pct": ctx.get("network_load_pct", 50) * 0.95,
        "active_users": ctx.get("active_users", 100),
        "device_type": "UE",
        "mobility_state": "stationary",
        "time_of_day": ctx.get("time_of_day", "day"),
        "signal_strength_dbm": ctx.get("signal_strength_dbm", -85),
        "sinr_db": ctx.get("sinr_db", 15),
        "rsrp_dbm": ctx.get("rsrp_dbm", -90),
        "rsrq_db": ctx.get("rsrq_db", -10),
        "cqi": ctx.get("cqi", 10),
        "network_slice_id": f"slice_{service}",
        "slice_resource_utilization_pct": ctx.get("network_load_pct", 50),
        "radio_resource_blocks_used": 50,
        "handover_in_progress": 0,
        "service_class": service,
        "application_id": partial.get("application_id", f"{service}.unknown"),
        "slice_type_label": slice_type,
        "priority_level": partial.get("priority_level", 4),
        "allocated_slice": slice_type,
        "sla_satisfied": partial.get("sla_satisfied", latency < 100),
        "reward_score": partial.get("reward_score", 80),
    }
    return record


def _skewness(arr: np.ndarray) -> float:
    if len(arr) < 3:
        return 0.0
    m, s = np.mean(arr), np.std(arr)
    return float(np.mean(((arr - m) / s) ** 3)) if s > 0 else 0.0


def _kurtosis(arr: np.ndarray) -> float:
    if len(arr) < 4:
        return 0.0
    m, s = np.mean(arr), np.std(arr)
    return float(np.mean(((arr - m) / s) ** 4) - 3) if s > 0 else 0.0
