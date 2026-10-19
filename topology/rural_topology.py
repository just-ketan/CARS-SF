"""
Canonical Rural 5G Private Network Topology.

Three-tier architecture: Rural Aggregation → Edge Cloud → Core Network.

    UEs (N per service) ──┐
                          s_rural ══ rural uplink (bottleneck) ══ s_edge ── srv_edge, mec_*
                                                                   ║  ┆ standby backup
                                                                   s_core ── srv_core

Access links are provisioned above the bottleneck so that the shared rural
uplink is the only contention point: slicing decisions, not access-link
artefacts, determine per-service performance.

Propagation delay placement. The QoS enforcer owns the qdiscs of both ends of
the rural uplink (HTB + fq_codel), which would silently discard a netem delay
configured there, and tcpdump on a sender only sees packets after its egress
qdisc. Each path's one-way propagation delay is therefore emulated on the
switch egress port facing the *destination* endpoint:

    access 2 ms + rural uplink 5 ms + server link 1 ms  = 8 ms  (UE ↔ edge)
    + backhaul 20 ms (fiber) or 40 ms (backup)          = 28/48 ms (UE ↔ core)
"""

from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.link import TCLink
from mininet.log import info

SERVICE_CLASSES = ("healthcare", "education", "agriculture", "general")

SERVICE_HOSTS = {
    "healthcare": "h_health",
    "education": "h_edu",
    "agriculture": "h_agri",
    "general": "h_gen",
}
# UE i (1-based) of a service gets 10.0.1.<base + i - 1>.
SERVICE_IP_BASE = {"healthcare": 10, "education": 20, "agriculture": 30, "general": 40}
MIXED_HOST, MIXED_IP = "h_mixed", "10.0.1.60"

HOST_SERVICE_MAP = {v: k for k, v in SERVICE_HOSTS.items()}

BOTTLENECK_INTF = "s_rural-up"          # s_rural side of the rural uplink
EDGE_DOWNLINK_INTF = "s_edge-down"      # s_edge side of the rural uplink
BACKHAUL_INTF = "s_edge-bh"             # primary edge→core backhaul (fiber)
BACKUP_BACKHAUL_INTFS = ("s_edge-bkp", "s_core-bkp")

# Switch-side port names must contain the switch name (Mininet's LinuxBridge
# only attaches such interfaces) and fit the 15-character kernel limit.
SERVERS = {
    "srv_edge": ("10.0.2.10", "s_edge", "s_edge-srv"),
    "mec_hlt": ("10.0.2.20", "s_edge", "s_edge-mhlt"),
    "mec_ctv": ("10.0.2.30", "s_edge", "s_edge-mctv"),
    "srv_core": ("10.0.3.10", "s_core", "s_core-srv"),
}


def ue_name(service: str, index: int) -> str:
    base = SERVICE_HOSTS[service]
    return base if index == 1 else f"{base}{index}"


def ue_ip(service: str, index: int) -> str:
    return f"10.0.1.{SERVICE_IP_BASE[service] + index - 1}"


ACCESS_DELAY_MS, RURAL_UPLINK_DELAY_MS, SERVER_LINK_DELAY_MS = 2, 5, 1
EDGE_PATH_DELAY_MS = ACCESS_DELAY_MS + RURAL_UPLINK_DELAY_MS + SERVER_LINK_DELAY_MS
BACKHAUL_DELAY_MS, BACKUP_BACKHAUL_DELAY_MS = 20, 40


class RuralNetworkTopology:
    """Mininet topology for rural private 5G service slicing experiments."""

    BOTTLENECK_BW_MBPS = 100
    BACKUP_BACKHAUL_BW_MBPS = 50

    # TCLink can shape at most 1000 Mbit; core links are left unshaped.
    def __init__(
        self,
        switch_cls=OVSBridge,
        controller_cls=None,
        ues_per_service: int = 2,
        mixed_ue: bool = False,
        bottleneck_mbps: float | None = None,
        backup_mbps: float | None = None,
    ):
        # OVSBridge runs in standalone (L2 learning) mode and needs no
        # OpenFlow controller; the reference `controller` binary is not
        # installed by the distro Mininet package.
        self.net = Mininet(
            controller=controller_cls,
            switch=switch_cls,
            link=TCLink,
            autoSetMacs=True,
            build=False,
        )
        self.ues_per_service = max(1, min(int(ues_per_service), 9))
        self.mixed_ue = mixed_ue
        if bottleneck_mbps:
            self.BOTTLENECK_BW_MBPS = bottleneck_mbps
        if backup_mbps:
            self.BACKUP_BACKHAUL_BW_MBPS = backup_mbps
        self.hosts_by_service: dict = {}
        self.ues_by_service: dict[str, list] = {}
        self.service_intfs: dict[str, list[str]] = {}
        self.ue_ips: dict[str, list[str]] = {}
        self.access_ports: dict[str, str] = {}

    def build(self):
        info("\n*** Building Rural 5G Architecture Topology\n")

        if self.net.controller:
            self.net.addController("c0")

        self.s_rural = self.net.addSwitch("s_rural", dpid="1")
        self.s_edge = self.net.addSwitch("s_edge", dpid="2")
        self.s_core = self.net.addSwitch("s_core", dpid="3")

        for service in SERVICE_CLASSES:
            self.ues_by_service[service] = []
            self.service_intfs[service] = []
            self.ue_ips[service] = []
            for i in range(1, self.ues_per_service + 1):
                name, ip = ue_name(service, i), ue_ip(service, i)
                host = self.net.addHost(name, ip=f"{ip}/24")
                self.ues_by_service[service].append(host)
                self.service_intfs[service].append(self._add_access_link(host))
                self.ue_ips[service].append(ip)
            self.hosts_by_service[service] = self.ues_by_service[service][0]

        if self.mixed_ue:
            self.h_mixed = self.net.addHost(MIXED_HOST, ip=f"{MIXED_IP}/24")
            self._add_access_link(self.h_mixed)
        self.h_health, self.h_edu, self.h_agri, self.h_gen = (
            self.hosts_by_service[s] for s in SERVICE_CLASSES
        )

        self.servers = {}
        for name, (ip, _, _) in SERVERS.items():
            self.servers[name] = self.net.addHost(name, ip=f"{ip}/24")
        self.srv_edge, self.srv_core = self.servers["srv_edge"], self.servers["srv_core"]
        self.mec_hlt, self.mec_ctv = self.servers["mec_hlt"], self.servers["mec_ctv"]

        # Rate-limited, delay-free: the QoS enforcer replaces these qdiscs.
        self.net.addLink(
            self.s_rural, self.s_edge,
            bw=self.BOTTLENECK_BW_MBPS,
            intfName1=BOTTLENECK_INTF, intfName2=EDGE_DOWNLINK_INTF,
        )
        self.net.addLink(
            self.s_edge, self.s_core, delay=f"{BACKHAUL_DELAY_MS}ms",
            intfName1=BACKHAUL_INTF, intfName2="s_core-bh",
        )
        # Standby backhaul: kept down so the L2 domain stays loop-free; the
        # self-healing engine brings it up when the primary backhaul fails.
        self.net.addLink(
            self.s_edge, self.s_core,
            bw=self.BACKUP_BACKHAUL_BW_MBPS, delay=f"{BACKUP_BACKHAUL_DELAY_MS}ms",
            intfName1=BACKUP_BACKHAUL_INTFS[0], intfName2=BACKUP_BACKHAUL_INTFS[1],
        )
        for name, (_, switch_name, port_name) in SERVERS.items():
            switch = self.s_edge if switch_name == "s_edge" else self.s_core
            self.net.addLink(
                self.servers[name], switch, intfName2=port_name,
                params1={}, params2={"delay": f"{EDGE_PATH_DELAY_MS}ms"},
            )

        self.bottleneck_intf = BOTTLENECK_INTF
        self.edge_downlink_intf = EDGE_DOWNLINK_INTF
        self.backhaul_intf = BACKHAUL_INTF
        self.backup_intfs = BACKUP_BACKHAUL_INTFS
        self.nominal_backhaul_delay_ms = BACKHAUL_DELAY_MS

    def _add_access_link(self, host) -> str:
        port_name = f"s_rural-a{len(self.access_ports) + 1}"
        self.net.addLink(
            host, self.s_rural, intfName2=port_name,
            params1={}, params2={"delay": f"{EDGE_PATH_DELAY_MS}ms"},
        )
        self.access_ports[host.name] = port_name
        return port_name

    @property
    def ue_hosts(self) -> list:
        hosts = [h for service in SERVICE_CLASSES for h in self.ues_by_service[service]]
        if self.mixed_ue:
            hosts.append(self.h_mixed)
        return hosts

    @property
    def server_hosts(self) -> list:
        return list(self.servers.values())

    def start(self):
        self.build()
        info("\n*** Starting Network\n")
        self.net.start()
        self.set_backup_backhaul(False)
        self._configure_routes()
        info("*** Testing Connectivity (Health to Edge)\n")
        self.net.ping([self.h_health, self.srv_edge], timeout="1")

    def _configure_routes(self):
        info("*** Configuring Static Routes\n")
        # Flat L2 domain with per-tier /24s: every subnet is on-link.
        for host in self.ue_hosts + self.server_hosts:
            for subnet in ("10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"):
                host.cmd(f"ip route add {subnet} dev {host.defaultIntf()} 2>/dev/null")

    # Self-healing only drives s_edge-side ports (the far ends stay passive),
    # and never enables the backup while the primary is admin-up, so the L2
    # domain is loop-free at every instant (no STP in the emulated switches).

    def set_backup_backhaul(self, up: bool):
        self.s_edge.cmd(f"ip link set {self.backup_intfs[0]} {'up' if up else 'down'}")

    def set_primary_backhaul(self, up: bool):
        self.s_edge.cmd(f"ip link set {self.backhaul_intf} {'up' if up else 'down'}")

    def primary_repaired(self) -> bool:
        """Loss-of-light check on the quarantined fiber: is the far end back?"""
        try:
            with open("/sys/class/net/s_core-bh/flags", encoding="utf-8") as handle:
                return bool(int(handle.read().strip(), 16) & 0x1)
        except OSError:
            return False

    def primary_link_quality(self) -> tuple[float, float]:
        """(one-way delay ms, loss %) of the quarantined primary backhaul.

        Stands in for OAM measurement (ITU-T Y.1731 delay/loss, BFD) on a
        standby path; in emulation the link's configured netem impairment is
        the ground truth such a measurement would report.
        """
        import re

        output = self.s_edge.cmd(f"tc qdisc show dev {self.backhaul_intf}")
        delay = re.search(r"delay ([\d.]+)(us|ms|s)", output)
        loss = re.search(r"loss ([\d.]+)%", output)
        scale = {"us": 1e-3, "ms": 1.0, "s": 1e3}
        delay_ms = float(delay.group(1)) * scale[delay.group(2)] if delay else 0.0
        return delay_ms, float(loss.group(1)) if loss else 0.0

    def get_host(self, name: str):
        return self.net.get(name)

    def stop(self):
        info("\n*** Stopping Network\n")
        self.net.stop()
