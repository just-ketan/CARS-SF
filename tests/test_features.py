"""Tests for packet matching, flow-window features and labelling."""

import os
import socket
import struct
import sys

import dpkt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.extractor import FlowFeatureExtractor
from features.packet_capture import CapturePoint, match_packets
from features.schema_mapper import EXCLUDED_FROM_ML, ML_FEATURE_COLUMNS, SCHEMA_COLUMNS, map_to_schema

UE, SRV, CORE = "10.0.1.10", "10.0.2.10", "10.0.3.10"

SPAWNS = [
    {"application_id": "healthcare.telemedicine", "service_class": "healthcare", "protocol": "udp",
     "host": "h_health", "host_ip": UE, "server_ip": SRV, "port": 5001, "slice_type": "URLLC",
     "priority": 1, "sla": {"latency_ms": 50, "jitter_ms": 10, "loss_pct": 1.0}},
    {"application_id": "education.live_classroom", "service_class": "education", "protocol": "udp",
     "host": "h_edu", "host_ip": "10.0.1.20", "server_ip": CORE, "port": 5001, "slice_type": "eMBB",
     "priority": 2, "sla": {}},
]


def _udp_frame(src, dst, sport, dport, seq, size=200):
    payload = b"CS" + struct.pack("!Qd", seq, 0.0) + bytes(size)
    udp = dpkt.udp.UDP(sport=sport, dport=dport, data=payload)
    udp.ulen = len(udp)
    ip = dpkt.ip.IP(src=socket.inet_aton(src), dst=socket.inet_aton(dst), p=17, data=udp, id=0)
    ip.len = len(ip)
    return bytes(dpkt.ethernet.Ethernet(type=dpkt.ethernet.ETH_TYPE_IP, data=ip))


def _write(path, frames):
    with open(path, "wb") as handle:
        writer = dpkt.pcap.Writer(handle)
        for ts, frame in frames:
            writer.writepkt(frame, ts=ts)


def _captures(tmp_path, n=40, delay=0.008, lost=(5, 6)):
    """UE sends n datagrams every 50 ms; the server receives them `delay` later."""
    tx, rx = [], []
    for seq in range(n):
        frame = _udp_frame(UE, SRV, 40000, 5001, seq)
        tx.append((1000.0 + seq * 0.05, frame))
        if seq not in lost:
            rx.append((1000.0 + seq * 0.05 + delay + (0.002 if seq % 2 else 0.0), frame))
    _write(tmp_path / "ue.pcap", tx)
    _write(tmp_path / "srv.pcap", rx)
    return [CapturePoint(str(tmp_path / "ue.pcap"), UE), CapturePoint(str(tmp_path / "srv.pcap"), SRV)]


def test_match_packets_measures_one_way_delay_and_loss(tmp_path):
    packets = match_packets(_captures(tmp_path), {UE})
    assert len(packets) == 40
    assert packets["rx_ts"].isna().sum() == 2
    delivered = packets.dropna(subset=["rx_ts"])
    assert np.allclose(delivered["owd_ms"].min(), 8.0, atol=1e-3)
    assert np.allclose(delivered["owd_ms"].max(), 10.0, atol=1e-3)
    assert (packets["direction"] == 1).all()


def test_flow_window_features_and_labels(tmp_path):
    fx = FlowFeatureExtractor(_captures(tmp_path), spawn_metadata=SPAWNS, window_s=1.0)
    records = fx.extract()
    assert records, "expected flow-window records"
    assert {r["service_class"] for r in records} == {"healthcare"}
    first = records[0]
    assert first["forward_packet_count"] == 20 and first["backward_packet_count"] == 0
    assert 8.0 <= first["end_to_end_latency_ms"] <= 10.0
    assert first["jitter_ms"] == 2.0          # alternating 8 / 10 ms delays
    assert first["queueing_delay_ms"] == 1.0   # mean delay above the 8 ms floor
    assert first["packet_loss_rate"] == 10.0   # 2 of the first 20 packets lost
    assert first["sla_satisfied"] is False     # loss 10 % > 1 % target


def test_match_flow_both_directions_and_same_port_on_different_servers():
    fx = FlowFeatureExtractor(spawn_metadata=SPAWNS)
    assert fx._match_spawn_metadata(UE, SRV, 40000, 5001, 17)["service_class"] == "healthcare"
    assert fx._match_spawn_metadata(SRV, UE, 5001, 40000, 17)["service_class"] == "healthcare"
    assert fx._match_spawn_metadata(CORE, "10.0.1.20", 40000, 5001, 17)["service_class"] == "education"
    assert fx._match_spawn_metadata("10.0.1.99", SRV, 1, 5001, 17) == {}


def test_service_qos_from_probes_and_htb_stats():
    telemetry = [
        {"service_rtt_ms": {"healthcare": 10.0}, "tc_class_stats": {}},
        {"service_rtt_ms": {"healthcare": None}, "tc_class_stats": {}},
        {"service_rtt_ms": {"healthcare": 14.0},
         "tc_class_stats": {"healthcare": {"sent_packets": 90, "dropped": 10, "backlog_bytes": 0}}},
    ]
    fx = FlowFeatureExtractor(telemetry_snapshots=telemetry)
    latency, jitter, loss = fx._service_qos("healthcare")
    assert latency == 12.0 and jitter == 4.0
    assert round(loss, 2) == 33.33


def test_average_telemetry_skips_non_numeric_fields():
    fx = FlowFeatureExtractor(telemetry_snapshots=[
        {"tick": 1, "tc_drops": 2, "queue_bytes": {"healthcare": 1}, "backhaul_up": True},
        {"tick": 2, "tc_drops": 4, "queue_bytes": {"healthcare": 3}, "backhaul_up": True},
    ])
    assert fx._average_telemetry() == {"tc_drops": 3.0}


def test_schema_uses_measured_direction_split_and_extra_columns():
    record = map_to_schema({
        "service_class": "general", "packet_count": 10, "byte_count": 1000,
        "forward_packet_count": 3, "backward_packet_count": 7,
        "forward_byte_count": 100, "backward_byte_count": 900,
        "queue_drops": 3, "p95_latency_ms": 12.5, "ue_host": "h_gen",
    })
    assert set(SCHEMA_COLUMNS) <= set(record)
    assert (record["forward_packet_count"], record["backward_byte_count"]) == (3, 900)
    assert record["queue_drops"] == 3 and record["p95_latency_ms"] == 12.5


def test_ml_features_exclude_labels_injected_context_and_shortcuts():
    for leaky in ("service_class", "application_id", "network_load_pct", "sinr_db",
                  "destination_port", "dscp", "flow_start_time", "ue_host"):
        assert leaky in EXCLUDED_FROM_ML
        assert leaky not in ML_FEATURE_COLUMNS
    assert "end_to_end_latency_ms" in ML_FEATURE_COLUMNS


def test_raw_ip_captures_from_tun_devices(tmp_path):
    """5G UE tunnels (uesimtun0) capture raw IP (LINKTYPE_RAW = 101), not Ethernet."""
    frame = _udp_frame(UE, SRV, 40000, 5001, seq=1)
    raw_ip = bytes(dpkt.ethernet.Ethernet(frame).data)
    path = tmp_path / "tun.pcap"
    with open(path, "wb") as handle:
        writer = dpkt.pcap.Writer(handle, linktype=101)
        writer.writepkt(raw_ip, ts=1.0)
    from features.packet_capture import parse_capture
    rows = parse_capture(CapturePoint(str(path), UE))
    assert len(rows) == 1 and rows[0][1] == "tx"
