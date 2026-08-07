import os
import pandas as pd
from scapy.all import rdpcap, IP, TCP, UDP
from collections import defaultdict
import numpy as np

def extract_features_from_pcap(pcap_file, output_csv):
    """
    Extracts flow features from a PCAP file using Scapy.
    Approximates the features found in the RSNSD synthetic dataset.
    """
    print(f"Reading {pcap_file}...")
    try:
        packets = rdpcap(pcap_file)
    except Exception as e:
        print(f"Error reading PCAP: {e}")
        return

    # A flow is identified by (src_ip, dst_ip, src_port, dst_port, protocol)
    flows = defaultdict(list)
    
    for pkt in packets:
        if IP in pkt:
            src_ip = pkt[IP].src
            dst_ip = pkt[IP].dst
            proto = pkt[IP].proto
            
            src_port = 0
            dst_port = 0
            
            if TCP in pkt:
                src_port = pkt[TCP].sport
                dst_port = pkt[TCP].dport
            elif UDP in pkt:
                src_port = pkt[UDP].sport
                dst_port = pkt[UDP].dport
                
            # To make it bidirectional or unidirectional. We'll do unidirectional for simplicity, 
            # or combine if needed. Let's do unidirectional flow.
            flow_key = (src_ip, dst_ip, src_port, dst_port, proto)
            flows[flow_key].append(pkt)

    print(f"Extracted {len(flows)} unique flows. Computing metrics...")
    
    records = []
    
    for flow_key, pkts in flows.items():
        src_ip, dst_ip, src_port, dst_port, proto = flow_key
        
        timestamps = [float(p.time) for p in pkts]
        lengths = [len(p) for p in pkts]
        
        flow_duration_ms = (max(timestamps) - min(timestamps)) * 1000
        packet_count = len(pkts)
        byte_count = sum(lengths)
        
        packet_rate_pps = packet_count / (flow_duration_ms / 1000) if flow_duration_ms > 0 else 0
        byte_rate_bps = (byte_count * 8) / (flow_duration_ms / 1000) if flow_duration_ms > 0 else 0
        
        iats = np.diff(timestamps) * 1000 if len(timestamps) > 1 else [0]
        mean_iat_ms = np.mean(iats)
        std_iat_ms = np.std(iats)
        
        mean_packet_size = np.mean(lengths)
        median_packet_size = np.median(lengths)
        
        # Labeling heuristically based on destination
        service_type = "unknown"
        if dst_ip == "10.0.2.10":
            if dst_port == 5001:
                service_type = "healthcare"
            elif dst_port == 5002:
                service_type = "agriculture"
        elif dst_ip == "10.0.3.10":
            if dst_port == 5001:
                service_type = "education"
            elif dst_port == 5002:
                service_type = "general"
                
        record = {
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port,
            "dst_port": dst_port,
            "transport_protocol": proto,
            "flow_duration_ms": flow_duration_ms,
            "packet_count": packet_count,
            "byte_count": byte_count,
            "packet_rate_pps": packet_rate_pps,
            "byte_rate_bps": byte_rate_bps,
            "mean_iat_ms": mean_iat_ms,
            "std_iat_ms": std_iat_ms,
            "mean_packet_size": mean_packet_size,
            "median_packet_size": median_packet_size,
            "service_type": service_type
        }
        records.append(record)
        
    df = pd.DataFrame(records)
    
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"Extracted {len(df)} flow records to {output_csv}")

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    edge_pcap = os.path.join(base_dir, "dataset", "raw", "edge_traffic.pcap")
    core_pcap = os.path.join(base_dir, "dataset", "raw", "core_traffic.pcap")
    
    out_csv = os.path.join(base_dir, "dataset", "processed", "mininet_empirical_dataset.csv")
    
    # We can process both and combine them
    print("This script requires Scapy. Ensure it is installed: pip install scapy pandas numpy")
    
    if os.path.exists(edge_pcap):
        extract_features_from_pcap(edge_pcap, out_csv.replace(".csv", "_edge.csv"))
    if os.path.exists(core_pcap):
        extract_features_from_pcap(core_pcap, out_csv.replace(".csv", "_core.csv"))
