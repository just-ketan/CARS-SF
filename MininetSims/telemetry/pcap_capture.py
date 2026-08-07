import os
import time
from mininet.log import info

class TelemetryCollector:
    """
    Captures network traffic (PCAP) from Mininet nodes to generate empirical datasets.
    """
    def __init__(self, topo, output_dir="MininetSims/dataset/raw"):
        self.topo = topo
        self.output_dir = output_dir
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def start_capture(self, duration=60):
        info("*** Starting PCAP capture on Edge and Core Switches\n")
        # Capture on s_edge and s_core
        # We capture on the specific switch interfaces or from the nodes themselves.
        # Capturing from s_edge and s_core captures all aggregated traffic.
        
        self.pcap_edge = os.path.join(self.output_dir, "edge_traffic.pcap")
        self.pcap_core = os.path.join(self.output_dir, "core_traffic.pcap")
        
        # Start tcpdump on the switches (or servers). Mininet switches are just OVS instances in the root namespace.
        # It's safer to capture from the server interfaces.
        
        self.topo.srv_edge.cmd(f"tcpdump -i srv_edge-eth0 -w {os.path.abspath(self.pcap_edge)} > /dev/null 2>&1 &")
        self.topo.srv_core.cmd(f"tcpdump -i srv_core-eth0 -w {os.path.abspath(self.pcap_core)} > /dev/null 2>&1 &")
        
        info(f"*** Capturing to {self.pcap_edge} and {self.pcap_core}\n")

    def stop_capture(self):
        info("*** Stopping PCAP capture\n")
        self.topo.srv_edge.cmd("pkill tcpdump")
        self.topo.srv_core.cmd("pkill tcpdump")
        time.sleep(1) # Let buffers flush
        
        info("*** PCAPs saved successfully\n")
