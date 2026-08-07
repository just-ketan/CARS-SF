"""
Canonical Rural 5G Private Network Topology.

Three-tier architecture: Rural Aggregation → Edge Cloud → Core Network.
Service-class UEs map to dedicated hosts with shaped links.
"""

from mininet.net import Mininet
from mininet.node import OVSBridge, Controller
from mininet.link import TCLink
from mininet.log import info


SERVICE_HOSTS = {
    "healthcare": "h_health",
    "education": "h_edu",
    "agriculture": "h_agri",
    "general": "h_gen",
}

HOST_SERVICE_MAP = {v: k for k, v in SERVICE_HOSTS.items()}


class RuralNetworkTopology:
    """Mininet topology for rural private 5G service slicing experiments."""

    BOTTLENECK_BW_MBPS = 100

    def __init__(self):
        self.net = Mininet(
            controller=Controller,
            switch=OVSBridge,
            link=TCLink,
            autoSetMacs=True,
            build=False,
        )
        self.hosts_by_service = {}

    def build(self):
        info("\n*** Building Rural 5G Architecture Topology\n")

        self.net.addController("c0")

        self.s_rural = self.net.addSwitch("s_rural")
        self.s_edge = self.net.addSwitch("s_edge")
        self.s_core = self.net.addSwitch("s_core")

        self.h_health = self.net.addHost("h_health", ip="10.0.1.10/24")
        self.h_edu = self.net.addHost("h_edu", ip="10.0.1.20/24")
        self.h_agri = self.net.addHost("h_agri", ip="10.0.1.30/24")
        self.h_gen = self.net.addHost("h_gen", ip="10.0.1.40/24")

        self.srv_edge = self.net.addHost("srv_edge", ip="10.0.2.10/24")
        self.srv_core = self.net.addHost("srv_core", ip="10.0.3.10/24")
        self.mec_hlt = self.net.addHost("mec_hlt", ip="10.0.2.20/24")
        self.mec_ctv = self.net.addHost("mec_ctv", ip="10.0.2.30/24")

        self.hosts_by_service = {
            "healthcare": self.h_health,
            "education": self.h_edu,
            "agriculture": self.h_agri,
            "general": self.h_gen,
        }

        self.net.addLink(self.h_health, self.s_rural, bw=50, delay="2ms")
        self.net.addLink(self.h_edu, self.s_rural, bw=100, delay="5ms")
        self.net.addLink(self.h_agri, self.s_rural, bw=10, delay="10ms")
        self.net.addLink(self.h_gen, self.s_rural, bw=50, delay="10ms")

        self.net.addLink(
            self.s_rural, self.s_edge,
            bw=self.BOTTLENECK_BW_MBPS, delay="5ms",
            intfName1="s_rural-eth4", intfName2="s_edge-eth1",
        )
        self.net.addLink(self.s_edge, self.s_core, bw=10000, delay="20ms")

        self.net.addLink(self.srv_edge, self.s_edge, bw=1000, delay="1ms")
        self.net.addLink(self.srv_core, self.s_core, bw=10000, delay="2ms")
        self.net.addLink(self.mec_hlt, self.s_edge, bw=500, delay="1ms")
        self.net.addLink(self.mec_ctv, self.s_edge, bw=500, delay="1ms")

        self.bottleneck_intf = "s_rural-eth4"

    def start(self):
        self.build()
        info("\n*** Starting Network\n")
        self.net.start()
        self._configure_routes()
        info("*** Testing Connectivity (Health to Edge)\n")
        self.net.ping([self.h_health, self.srv_edge], timeout="1000")

    def _configure_routes(self):
        info("*** Configuring Static Routes\n")
        ue_hosts = [self.h_health, self.h_edu, self.h_agri, self.h_gen]
        for host in ue_hosts:
            host.cmd(f"ip route add 10.0.2.0/24 dev {host.name}-eth0")
            host.cmd(f"ip route add 10.0.3.0/24 dev {host.name}-eth0")

        for server in (self.srv_edge, self.mec_hlt, self.mec_ctv):
            server.cmd(f"ip route add 10.0.1.0/24 dev {server.name}-eth0")
            server.cmd(f"ip route add 10.0.3.0/24 dev {server.name}-eth0")

        self.srv_core.cmd("ip route add 10.0.1.0/24 dev srv_core-eth0")
        self.srv_core.cmd("ip route add 10.0.2.0/24 dev srv_core-eth0")

    def get_host(self, name: str):
        return self.net.get(name)

    def stop(self):
        info("\n*** Stopping Network\n")
        self.net.stop()
