import os
import time
from mininet.log import info

class MininetTrafficGenerator:
    """
    Generates realistic empirical traffic over a Mininet Topology.
    Maps to RSNSD Service Classes using standard Linux networking tools (iperf3, ping, etc).
    """
    def __init__(self, topo):
        self.topo = topo

    def start_servers(self):
        info("*** Starting Servers on Edge and Core\n")
        # Start iperf3 servers
        self.topo.srv_edge.cmd("iperf3 -s -p 5001 -D") # Healthcare (URLLC/eMBB to Edge)
        self.topo.srv_edge.cmd("iperf3 -s -p 5002 -D") # Agriculture (mMTC to Edge)
        
        self.topo.srv_core.cmd("iperf3 -s -p 5001 -D") # Education (eMBB to Core)
        self.topo.srv_core.cmd("iperf3 -s -p 5002 -D") # General (Best Effort to Core)

    def generate_healthcare_traffic(self, duration=60):
        # URLLC / eMBB: High bandwidth, reliable connection to Edge Server
        info(f"*** Generating Healthcare Traffic (Remote Surgery/Imaging) for {duration}s\n")
        # UDP stream to emulate video/haptic, target 50Mbps
        cmd = f"iperf3 -c 10.0.2.10 -p 5001 -u -b 50M -t {duration} &"
        self.topo.h_health.cmd(cmd)

    def generate_education_traffic(self, duration=60):
        # eMBB: High bandwidth, bulk transfer to Core Server
        info(f"*** Generating Education Traffic (Video Streaming/Downloads) for {duration}s\n")
        # TCP stream to emulate bulk download/video stream
        cmd = f"iperf3 -c 10.0.3.10 -p 5001 -t {duration} &"
        self.topo.h_edu.cmd(cmd)

    def generate_agriculture_traffic(self, duration=60):
        # mMTC: Periodic small packets to Edge Server
        info(f"*** Generating Agriculture Traffic (Sensor Data) for {duration}s\n")
        # Ping with small payload and interval to emulate IoT periodic telemetry
        cmd = f"ping 10.0.2.10 -i 1 -s 64 -w {duration} > /dev/null 2>&1 &"
        self.topo.h_agri.cmd(cmd)

    def generate_general_traffic(self, duration=60):
        # Best Effort: Bursty TCP to Core Server
        info(f"*** Generating General Traffic (Web Browsing/Social) for {duration}s\n")
        # Bursty TCP traffic via iperf3 (short bursts every few seconds)
        # We can simulate this using a bash loop
        burst_script = f"""
        for i in {{1..{int(duration/5)}}}; do
            iperf3 -c 10.0.3.10 -p 5002 -t 2 -O 1 > /dev/null 2>&1
            sleep 3
        done &
        """
        self.topo.h_gen.cmd(burst_script)

    def run_all(self, duration=60):
        self.start_servers()
        time.sleep(2) # Give servers time to start
        
        self.generate_healthcare_traffic(duration)
        self.generate_education_traffic(duration)
        self.generate_agriculture_traffic(duration)
        self.generate_general_traffic(duration)
        
        info(f"*** Waiting {duration} seconds for traffic generation to complete...\n")
        time.sleep(duration + 2)
        
        info("*** Cleaning up traffic generators\n")
        self.topo.srv_edge.cmd("pkill iperf3")
        self.topo.srv_core.cmd("pkill iperf3")
