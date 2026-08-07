import os
import sys

# Ensure MininetSims is in path if needed, though running from project root is standard
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mininet.log import setLogLevel, info
from topology.rural_topology import RuralNetworkTopology
from traffic.traffic_generator import MininetTrafficGenerator
from telemetry.pcap_capture import TelemetryCollector

def run_simulation(duration=60):
    setLogLevel("info")
    
    # 1. Build and start topology
    topo = RuralNetworkTopology()
    
    try:
        topo.start()
        
        # 2. Setup Telemetry
        telemetry = TelemetryCollector(topo)
        telemetry.start_capture(duration)
        
        # 3. Start Traffic Generation
        generator = MininetTrafficGenerator(topo)
        generator.run_all(duration)
        
        # 4. Cleanup
        telemetry.stop_capture()
        
        info("\n*** Simulation Complete! PCAPs generated in MininetSims/dataset/raw\n")
        
    except Exception as e:
        info(f"*** Error during simulation: {e}\n")
    finally:
        topo.stop()

if __name__ == "__main__":
    # Ensure run as root, mininet requires root
    if os.geteuid() != 0:
        print("Please run this script as root (sudo python3 run_experiment.py)")
        sys.exit(1)
        
    # Default simulation duration 30 seconds
    run_simulation(duration=30)
