from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.link import TCLink
from mininet.log import info

class TopologyManager:
    """
    Phase 1: Simulation Architecture
    Provides the L2/L3 foundational network testbed acting as a digital twin.
    """
    def __init__(self):
        self.net = Mininet(
            switch=OVSBridge,
            link=TCLink,
            autoSetMacs=True,
            build=False
        )

    def _build_topology(self):
        info("*** Building Digital Twin Topology\n")

        # Switches
        # Rural Aggregation
        self.s_rural_1 = self.net.addSwitch("s_rural_1", dpid="0000000000000001")
        self.s_rural_2 = self.net.addSwitch("s_rural_2", dpid="0000000000000002")
        # Edge Cloud
        self.s_edge = self.net.addSwitch("s_edge", dpid="0000000000000003")
        # 5G Core / Internet Gateway
        self.s_core = self.net.addSwitch("s_core", dpid="0000000000000004")

        # Hosts (UEs)
        self.h_home = self.net.addHost("h_home")       # General Internet
        self.h_school = self.net.addHost("h_school")   # Education
        self.h_hospital = self.net.addHost("h_hospital") # Healthcare
        self.h_farm = self.net.addHost("h_farm")       # Agriculture

        # Servers (MEC and Core)
        self.mec_hlt = self.net.addHost("mec_hlt")
        self.mec_ctv = self.net.addHost("mec_ctv")
        self.inet = self.net.addHost("inet")

        # Links (with bandwidth in Mbps and delay)
        # Village Edge to Rural Aggregation (1 Gbps, 2ms)
        self.net.addLink(self.h_home, self.s_rural_1, bw=1000, delay="2ms")
        self.net.addLink(self.h_school, self.s_rural_1, bw=1000, delay="2ms")
        self.net.addLink(self.h_hospital, self.s_rural_2, bw=1000, delay="2ms")
        self.net.addLink(self.h_farm, self.s_rural_2, bw=1000, delay="2ms")

        # Rural Aggregation to Edge Cloud (10 Gbps, 1ms)
        # Note: Mininet's TCIntf max bw is officially 1000 (1Gbps) though it sometimes allows more.
        # We will clamp these to 1000 to prevent 'Bandwidth limit outside supported range' warnings.
        self.net.addLink(self.s_rural_1, self.s_edge, bw=1000, delay="1ms")
        self.net.addLink(self.s_rural_2, self.s_edge, bw=1000, delay="1ms")
        
        # MEC Servers to Edge Switch
        self.net.addLink(self.mec_hlt, self.s_edge, bw=1000, delay="1ms")
        self.net.addLink(self.mec_ctv, self.s_edge, bw=1000, delay="1ms")
        
        # Edge Cloud to 5G Core (40 Gbps, 10ms)
        self.net.addLink(self.s_edge, self.s_core, bw=1000, delay="10ms")
        self.net.addLink(self.inet, self.s_core, bw=1000, delay="1ms")

    def start_network(self):
        self._build_topology()
        self.net.start()
        # Mininet automatically sets up routes for hosts in the same subnet
        # In a real SDN scenario, OpenFlow rules would be pushed here.
        info("*** Network Started Successfully\n")

    def stop_network(self):
        self.net.stop()
