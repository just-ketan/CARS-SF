import os
import time
import subprocess
from mininet.net import Mininet
from mininet.node import OVSBridge, Controller
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI

class RuralNetworkTopology:
    """
    Mininet Topology modeling a Rural 5G Private Network.
    Contains Rural Aggregation, Edge Cloud, and Core Network tiers.
    """
    def __init__(self):
        self.net = Mininet(
            controller=Controller,
            switch=OVSBridge,
            link=TCLink,
            autoSetMacs=True,
            build=False
        )

    def build(self):
        info("\n*** Building Rural 5G Architecture Topology\n")
        
        # Add Controller
        self.net.addController('c0')

        info("*** Creating Switches (Tiers)\n")
        self.s_rural = self.net.addSwitch("s_rural") # Rural Aggregation
        self.s_edge = self.net.addSwitch("s_edge")   # Edge Cloud
        self.s_core = self.net.addSwitch("s_core")   # Core Network

        info("*** Creating Hosts (UEs)\n")
        # Rural UE nodes
        self.h_health = self.net.addHost("h_health", ip="10.0.1.10/24")
        self.h_edu = self.net.addHost("h_edu", ip="10.0.1.20/24")
        self.h_agri = self.net.addHost("h_agri", ip="10.0.1.30/24")
        self.h_gen = self.net.addHost("h_gen", ip="10.0.1.40/24")

        info("*** Creating Servers\n")
        # Edge and Core Servers
        self.srv_edge = self.net.addHost("srv_edge", ip="10.0.2.10/24")
        self.srv_core = self.net.addHost("srv_core", ip="10.0.3.10/24")

        info("*** Creating Links\n")
        # UE to Rural Switch (Simulating RAN)
        self.net.addLink(self.h_health, self.s_rural, bw=50, delay="2ms") # URLLC prioritized
        self.net.addLink(self.h_edu, self.s_rural, bw=100, delay="5ms")   # eMBB
        self.net.addLink(self.h_agri, self.s_rural, bw=10, delay="10ms")  # mMTC
        self.net.addLink(self.h_gen, self.s_rural, bw=50, delay="10ms")   # Best Effort

        # Transport Links
        # Rural to Edge (Fronthaul/Midhaul)
        self.net.addLink(self.s_rural, self.s_edge, bw=1000, delay="5ms")
        
        # Edge to Core (Backhaul)
        self.net.addLink(self.s_edge, self.s_core, bw=10000, delay="20ms")

        # Servers to Switches
        self.net.addLink(self.srv_edge, self.s_edge, bw=1000, delay="1ms")
        self.net.addLink(self.srv_core, self.s_core, bw=10000, delay="2ms")

    def start(self):
        self.build()
        info("\n*** Starting Network\n")
        self.net.start()
        
        # Setup basic routing (very simplified for flat L2/L3 in mininet)
        # In a real setup, we'd use IP forwarding or SDN flows.
        # Here Mininet auto-sets up routes if in same subnet, but they are in different subnets.
        # For simplicity in this L2 simulation, we let them ping directly (ARP will resolve if netmask is wide enough).
        # Wait, they have /24 and different subnets. We should configure static routes.
        
        info("*** Configuring Static Routes\n")
        hosts = [self.h_health, self.h_edu, self.h_agri, self.h_gen]
        for h in hosts:
            h.cmd("ip route add 10.0.2.0/24 dev %s-eth0" % h.name)
            h.cmd("ip route add 10.0.3.0/24 dev %s-eth0" % h.name)
            
        self.srv_edge.cmd("ip route add 10.0.1.0/24 dev srv_edge-eth0")
        self.srv_edge.cmd("ip route add 10.0.3.0/24 dev srv_edge-eth0")
        
        self.srv_core.cmd("ip route add 10.0.1.0/24 dev srv_core-eth0")
        self.srv_core.cmd("ip route add 10.0.2.0/24 dev srv_core-eth0")

        info("*** Testing Connectivity (Health to Edge)\n")
        self.net.ping([self.h_health, self.srv_edge])

    def stop(self):
        info("\n*** Stopping Network\n")
        self.net.stop()