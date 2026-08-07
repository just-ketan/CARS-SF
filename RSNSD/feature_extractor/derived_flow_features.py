"""
Derived Flow Feature Extractor

Computes additional flow-level features from the simulated
traffic record. These features approximate what tools such as
CICFlowMeter would derive from captured traffic while keeping
the simulation lightweight.

Author: RSNSD
"""

from __future__ import annotations

from RSNSD.domain.dataset import DatasetRecord


class DerivedFlowFeatureExtractor:
    """
    Computes deterministic flow statistics from the generated
    FlowRecord.
    """

    LINK_CAPACITY_MBPS = 100.0

    def extract(self, record: DatasetRecord) -> dict:

        flow = record.flow
        qos = record.qos

        duration_s = max(flow.session_duration_s, 0.001)

        packet_size_bytes = max(flow.packet_size, 1)

        bitrate_bps = flow.bitrate_mbps * 1_000_000

        packet_count = max(
            1,
            int(
                (bitrate_bps * duration_s)
                / (packet_size_bytes * 8)
            ),
        )

        byte_count = packet_count * packet_size_bytes

        packet_rate = packet_count / duration_s

        byte_rate = byte_count / duration_s

        goodput = qos.throughput_mbps

        bandwidth_utilization = (
            goodput
            / self.LINK_CAPACITY_MBPS
        ) * 100

        link_utilization = bandwidth_utilization
        
        # Temporal & Statistical basics
        forward_packet_count = int(packet_count * 0.6)
        backward_packet_count = packet_count - forward_packet_count
        forward_byte_count = int(byte_count * 0.7)
        backward_byte_count = byte_count - forward_byte_count
        
        # Ports based on application
        is_web = "Web" in flow.application_id or "Cloud" in flow.application_id
        is_stream = "Stream" in flow.application_id or "Video" in flow.application_id
        src_port = 443 if is_web else (554 if is_stream else 8080)
        dst_port = int(10000 + (hash(flow.application_id) % 50000))
        
        # IAT logic
        mean_iat_ms = (duration_s * 1000) / max(1, packet_count)
        
        return {
            "flow_duration_ms": duration_s * 1000,
            "packet_count": packet_count,
            "byte_count": int(byte_count),
            "packet_rate_pps": packet_rate,
            "byte_rate_bps": byte_rate,
            "goodput_mbps": goodput,
            "bandwidth_utilization_pct": min(100.0, bandwidth_utilization),
            "link_utilization_pct": min(100.0, link_utilization),
            
            # Additional features mapped to fix missing values:
            "forward_packet_count": forward_packet_count,
            "backward_packet_count": backward_packet_count,
            "forward_byte_count": forward_byte_count,
            "backward_byte_count": backward_byte_count,
            
            "flow_start_time": 1700000000.0,
            "flow_end_time": 1700000000.0 + duration_s,
            
            "ether_type": 2048, # IPv4
            "vlan_present": False,
            "vlan_priority": 0,
            "broadcast_frame": False,
            "multicast_frame": False,
            
            "ip_version": 4,
            "ttl": 64,
            "dscp": 0,
            "ecn": 0,
            "ip_packet_length": packet_size_bytes,
            "fragmented": False,
            "ip_header_length": 20,
            "hop_limit": 64,
            
            "transport_protocol": 6 if is_web else 17, # TCP vs UDP
            "source_port": src_port,
            "destination_port": dst_port,
            
            "tcp_syn_count": 1 if is_web else 0,
            "tcp_ack_count": packet_count if is_web else 0,
            "tcp_fin_count": 1 if is_web else 0,
            "tcp_rst_count": 0,
            "tcp_window_size": 65535,
            "tcp_retransmissions": int(packet_count * qos.packet_loss_rate),
            "udp_packet_count": packet_count if not is_web else 0,
            
            "mean_iat_ms": mean_iat_ms,
            "std_iat_ms": mean_iat_ms * 0.2,
            "min_iat_ms": mean_iat_ms * 0.5,
            "max_iat_ms": mean_iat_ms * 2.0,
            "forward_mean_iat_ms": mean_iat_ms * 1.1,
            "backward_mean_iat_ms": mean_iat_ms * 0.9,
            "flow_active_time_ms": duration_s * 1000,
            "flow_idle_time_ms": 0.0,
            
            "mean_packet_size": packet_size_bytes,
            "median_packet_size": packet_size_bytes,
            "min_packet_size": max(64, packet_size_bytes - 100),
            "max_packet_size": min(1500, packet_size_bytes + 100),
            "std_packet_size": 20.0,
            "variance_packet_size": 400.0,
            "packet_size_range": 200,
            "packet_size_skewness": 0.0,
            "packet_size_kurtosis": 0.0,
            "coefficient_of_variation_packet_size": 0.1,
            
            "slice_type_label": record.context.slice_type,
            "priority_level": record.context.service_priority,
            "allocated_slice": record.context.network_slice_id,
            "reward_score": qos.qos_satisfaction_score,
        }