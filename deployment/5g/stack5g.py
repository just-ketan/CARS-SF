"""
Adapter that lets the CARS-SF control stack drive the Open5GS + UERANSIM deployment.

The closed loop itself (SliceController, SelfHealingEngine, FailureDetector,
OnlineSliceClassifier, the RL policies) is the code the emulated testbed uses. This
module supplies the network-facing objects those classes expect, backed by the
containers of docker-compose.yml:

  Node              a long-lived shell inside one container (``cmd`` like a Mininet node)
  Net5G             ``get(name)`` for Mininet names (s_rural → cell_site, s_edge → upf_tap, …)
  Topology5G        backhaul control and quality, the interface SelfHealingEngine uses
  Transport5GQoS    QoSEnforcer with uplink at the cell site and downlink at the UPF
  Telemetry5G       the snapshot TelemetryCollector produces, from the real user plane
  FaultInjector5G   registry failure specs applied to the fiber / backup / core cloud
  LinkWatcher5G     50 ms carrier polling of the primary backhaul

Enforcement points (see docs/DEPLOYMENT_ARCHITECTURE.md):

  uplink    HTB + fq_codel on the cell site's N3 egress. Packets there are already
            GTP-U encapsulated, so filters match the inner header at a fixed offset.
  downlink  HTB + fq_codel on the UPF's ogstun: inner IP, before GTP encapsulation.

Rates are enforced on the transport path. Nothing here schedules radio resources:
UERANSIM does not simulate them.
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from self_healing.injector import FaultInjector
from slicing.qos_enforcer import _RC_RE, DOWNLINK, FLOW_PRIO, UPLINK, QoSEnforcer  # noqa: F401
from telemetry.collector import TelemetryCollector
from topology.rural_topology import BACKHAUL_INTF

COMPOSE_FILE = Path(__file__).resolve().parent / "docker-compose.yml"
COMPOSE = ["docker", "compose", "-f", str(COMPOSE_FILE)]
SERVICES = ("healthcare", "education", "agriculture", "general")
UE_IP = {"healthcare": "10.60.0.2", "education": "10.61.0.2", "agriculture": "10.62.0.2", "general": "10.63.0.2"}
SLICE_POOL = {s: ip.rsplit(".", 1)[0] + ".0/24" for s, ip in UE_IP.items()}
EDGE_DN_IP, CORE_DN_IP = "10.81.0.100", "10.85.0.100"     # edge data network, core-cloud service address
UPF_ADDR = {"n3": "10.80.0.10", "n6": "10.81.0.10", "fiber": "10.83.0.10", "backup": "10.84.0.10"}
CORE_ADDR = {"fiber": "10.83.0.100", "backup": "10.84.0.100"}
CELL_ROUTER_N3_ADDR = "10.80.0.2"
FIBER_DELAY_MS, BACKUP_DELAY_MS, BACKUP_SHARE = 20, 40, 0.5    # backup carries half the rural link

# Measured on this deployment: outer IPv4 20 + UDP 8 + GTP-U 8 + PDU session container 8.
GTP_INNER_OFFSET = 44
INNER_PROTO_AT, INNER_SRC_AT, INNER_DST_AT = GTP_INNER_OFFSET + 9, GTP_INNER_OFFSET + 12, GTP_INNER_OFFSET + 16
INNER_SPORT_AT, INNER_DPORT_AT = GTP_INNER_OFFSET + 20, GTP_INNER_OFFSET + 22
ICMP_PRIO, SLICE_PRIO, FLOW_PRIO_BASE = 50, 60, 100


def ip_to_hex(address: str) -> str:
    return "0x" + "".join(f"{int(octet):02x}" for octet in address.split("."))


class Node:
    """A persistent shell in one compose service; ``cmd`` runs a command and returns its output."""

    def __init__(self, service: str):
        self.name = service
        self._lock = threading.Lock()
        self._proc = subprocess.Popen(
            COMPOSE + ["exec", "-T", service, "sh"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        self._count = 0

    def cmd(self, command: str) -> str:
        with self._lock:
            self._count += 1
            marker = f"__END_{self._count}__"
            self._proc.stdin.write(f"{{ {command}\n}} 2>&1; echo {marker}\n")
            self._proc.stdin.flush()
            lines = []
            for line in self._proc.stdout:
                if line.strip() == marker:
                    break
                if marker in line:                     # output without a trailing newline
                    lines.append(line.split(marker)[0])
                    break
                lines.append(line)
            return "".join(lines)

    def close(self):
        try:
            self._proc.stdin.close()
            self._proc.terminate()
            self._proc.wait(timeout=3)
        except Exception:
            self._proc.kill()


class Net5G:
    ALIASES = {"s_rural": "cell_site", "s_edge": "upf_tap", "s_core": "dn_core"}

    def __init__(self):
        self.nodes: dict[str, Node] = {}

    def get(self, name: str) -> Node:
        service = self.ALIASES.get(name, name)
        if service not in self.nodes:
            self.nodes[service] = Node(service)
        return self.nodes[service]

    def close(self):
        for node in self.nodes.values():
            node.close()
        self.nodes = {}


def iface_with_address(node: Node, address: str) -> str:
    output = node.cmd("ip -o -4 addr show")
    match = re.search(rf"^\d+:\s+(\S+)\s+inet {re.escape(address)}/", output, re.M)
    if match is None:
        raise RuntimeError(f"no interface with {address} in {node.name}: is the 5G stack up?\n{output}")
    return match.group(1)


class _NoFdb:
    """SelfHealingEngine flushes L2 tables after a path change; routed paths have none."""

    name = "routed"

    @staticmethod
    def cmd(_command: str) -> str:
        return ""


class _UE:
    def __init__(self, address: str):
        self.address = address

    def IP(self) -> str:
        return self.address


class Topology5G:
    """Path control between the UPF and the core cloud: two routed backhauls, primary or backup."""

    BOTTLENECK_BW_MBPS = 100.0
    nominal_backhaul_delay_ms = FIBER_DELAY_MS
    mixed_ue = False
    switch_type = "Open5GS+UERANSIM"
    s_rural = s_edge = s_core = _NoFdb()

    def __init__(self, net: Net5G, capacity: float = 100.0):
        self.net = net
        self.BOTTLENECK_BW_MBPS = capacity
        self.upf, self.core = net.get("upf_tap"), net.get("dn_core")
        self.n3_cell = iface_with_address(net.get("cell_site"), CELL_ROUTER_N3_ADDR)
        self.fiber_upf = iface_with_address(self.upf, UPF_ADDR["fiber"])
        self.backup_upf = iface_with_address(self.upf, UPF_ADDR["backup"])
        self.fiber_core = iface_with_address(self.core, CORE_ADDR["fiber"])
        self.backup_core = iface_with_address(self.core, CORE_ADDR["backup"])
        self.active = "primary"
        self.ue_hosts = [_UE(ip) for ip in UE_IP.values()]
        self.services = list(SERVICES)

    # ------------------------------------------------------------------- setup

    def _disable_offload(self):
        """Packet capture must see wire-size packets: with GSO/GRO a capture holds merged
        segments that cannot be matched across capture points (Mininet disables them too)."""
        for name, addresses in (("dn", [EDGE_DN_IP]), ("dn_core", CORE_ADDR.values()),
                                ("cell_site", [CELL_ROUTER_N3_ADDR, "10.78.0.2"]),
                                ("upf_tap", [UPF_ADDR[k] for k in ("n3", "n6", "fiber", "backup")])):
            node = self.net.get(name)
            for address in addresses:
                iface = iface_with_address(node, address)
                node.cmd(f"ethtool -K {iface} tso off gso off gro off lro off 2>/dev/null")

    def reset(self):
        """Known state at the start of a run: both links up, nominal impairment, primary path."""
        self._disable_offload()
        for iface in (self.fiber_upf, self.backup_upf):
            self.upf.cmd(f"ip link set {iface} up")
        for iface in (self.fiber_core, self.backup_core):
            self.core.cmd(f"ip link set {iface} up")
        for node, fiber, backup in ((self.upf, self.fiber_upf, self.backup_upf),
                                    (self.core, self.fiber_core, self.backup_core)):
            node.cmd(f"tc qdisc del dev {fiber} root 2>/dev/null; tc qdisc del dev {backup} root 2>/dev/null")
            node.cmd(f"tc qdisc add dev {fiber} root netem delay {FIBER_DELAY_MS}ms limit 100000")
            node.cmd(f"tc qdisc add dev {backup} root netem delay {BACKUP_DELAY_MS}ms "
                     f"rate {self.BOTTLENECK_BW_MBPS * BACKUP_SHARE:.0f}mbit limit 100000")
        self.core.cmd(f"ip addr replace {CORE_DN_IP}/32 dev lo")
        self.upf.cmd(f"ip route replace blackhole {CORE_DN_IP}/32 metric 200")
        self.core.cmd("ip route replace blackhole 10.60.0.0/14 metric 200")
        self.net.get("dn").cmd(f"ip route replace 10.60.0.0/14 via {UPF_ADDR['n6']}")
        self._route("primary")
        for service in SERVICES:
            # The simulated radio must not be the bottleneck: the default 500-packet fq_codel on
            # the UE's TUN device would drop video bursts before any slice sees them.
            self.net.get(f"tg_{service}").cmd(
                f"ip route replace 10.81.0.0/24 dev uesimtun0; ip route replace {CORE_DN_IP}/32 dev uesimtun0; "
                "ip link set uesimtun0 txqueuelen 20000; tc qdisc replace dev uesimtun0 root pfifo limit 20000")

    def _route(self, path: str):
        self.active = path
        name = "fiber" if path == "primary" else "backup"
        iface_upf, iface_core = (self.fiber_upf, self.fiber_core) if path == "primary" \
            else (self.backup_upf, self.backup_core)
        self.upf.cmd(f"ip route replace {CORE_DN_IP}/32 via {CORE_ADDR[name]} dev {iface_upf}")
        self.core.cmd(f"ip route replace 10.60.0.0/14 via {UPF_ADDR[name]} dev {iface_core}")

    def relink(self):
        """Links came back: their routes vanished with them, so restore the active path."""
        self._route(self.active)

    # --------------------------------------------- SelfHealingEngine's interface

    def set_primary_backhaul(self, up: bool):
        if up:
            self._route("primary")

    def set_backup_backhaul(self, up: bool):
        if up:
            self._route("backup")

    def primary_repaired(self) -> bool:
        return self.upf.cmd(f"cat /sys/class/net/{self.fiber_upf}/operstate").strip() != "down"

    def primary_link_quality(self) -> tuple[float, float]:
        output = self.upf.cmd(f"tc qdisc show dev {self.fiber_upf}")
        delay = re.search(r"delay ([\d.]+)(us|ms|s)", output)
        loss = re.search(r"loss ([\d.]+)%", output)
        scale = {"us": 1e-3, "ms": 1.0, "s": 1e3}
        delay_ms = float(delay.group(1)) * scale[delay.group(2)] if delay else 0.0
        return delay_ms, float(loss.group(1)) if loss else 0.0


class Transport5GQoS(QoSEnforcer):
    """QoSEnforcer on the 5G transport path; slices are identified by their PDU address pool
    (host mode, the UE's S-NSSAI decides) or per flow by SliceNet (slicenet_all)."""

    def __init__(self, net: Net5G, topo: Topology5G, **kwargs):
        super().__init__(net=net, bottleneck_intf=topo.n3_cell, downlink_intf="ogstun", **kwargs)
        self._flow_prio: dict[tuple, int] = {}

    def _directions(self):
        return ((UPLINK, self.net.get("cell_site"), self.bottleneck_intf),
                (DOWNLINK, self.net.get("upf_tap"), self.downlink_intf))

    def _root_prefix(self, iface: str) -> str:
        # Account the uplink in user-plane bytes: "C Mb/s" means the same payload capacity as
        # on the downlink (ogstun, inner packets) and on the emulated testbed.
        return f"stab overhead -{GTP_INNER_OFFSET} linklayer ethernet " if iface == self.bottleneck_intf else ""

    def _install_filters(self, spawns: list[dict]):
        cell = self.net.get("cell_site")
        upf = self.net.get("upf_tap")
        for service, pool in SLICE_POOL.items():
            classid = self.class_ids[service]
            address = pool.split("/")[0]
            # QoS probes (ICMP) stay in their PDU session's slice in every classification mode.
            cell.cmd(f"tc filter add dev {self.bottleneck_intf} protocol ip parent 1: prio {ICMP_PRIO} u32 "
                     f"match ip dport 2152 0xffff match u8 1 0xff at {INNER_PROTO_AT} "
                     f"match u32 {ip_to_hex(address)} 0xffffff00 at {INNER_SRC_AT} flowid {classid}")
            upf.cmd(f"tc filter add dev {self.downlink_intf} protocol ip parent 1: prio {ICMP_PRIO} u32 "
                    f"match ip protocol 1 0xff match ip dst {pool} flowid {classid}")
            if self.classification == "slicenet_all":
                continue                     # data flows wait in best effort until SliceNet decides
            cell.cmd(f"tc filter add dev {self.bottleneck_intf} protocol ip parent 1: prio {SLICE_PRIO} u32 "
                     f"match ip dport 2152 0xffff match u32 {ip_to_hex(address)} 0xffffff00 at {INNER_SRC_AT} "
                     f"flowid {classid}")
            upf.cmd(f"tc filter add dev {self.downlink_intf} protocol ip parent 1: prio {SLICE_PRIO} u32 "
                    f"match ip dst {pool} flowid {classid}")

    def classify_flow(self, flow: tuple, class_name: str, replace: bool = False) -> bool:
        """One flow → one class at both enforcement points (fresh rule, or replaced on reclassification)."""
        if class_name not in self.class_ids or self.flow_rules.get(flow) == class_name:
            return False
        if flow in self.flow_rules and not replace:
            return False
        ue, peer, proto, ue_port, peer_port = flow
        proto_name = {6: "tcp", 17: "udp"}.get(int(proto))
        if proto_name is None:
            return False
        classid = self.class_ids[class_name]
        known = flow in self._flow_prio
        prio = self._flow_prio.setdefault(flow, FLOW_PRIO_BASE + len(self._flow_prio))
        cell, upf = self.net.get("cell_site"), self.net.get("upf_tap")
        ports = f"0x{int(ue_port):04x}{int(peer_port):04x}"
        steps = [f"tc filter del dev {self.bottleneck_intf} parent 1: prio {prio}"] if known else []
        steps.append(
            f"tc filter add dev {self.bottleneck_intf} protocol ip parent 1: prio {prio} u32 "
            f"match ip dport 2152 0xffff match u8 {int(proto)} 0xff at {INNER_PROTO_AT} "
            f"match u32 {ip_to_hex(ue)} 0xffffffff at {INNER_SRC_AT} "
            f"match u32 {ip_to_hex(peer)} 0xffffffff at {INNER_DST_AT} "
            f"match u32 {ports} 0xffffffff at {INNER_SPORT_AT} flowid {classid}")
        rc = self._run(cell, "; ".join(steps))
        down = self._run(upf, f"tc filter {'replace' if known else 'add'} dev {self.downlink_intf} protocol ip "
                              f"parent 1: prio 1 handle {prio} flower src_ip {peer} dst_ip {ue} "
                              f"ip_proto {proto_name} src_port {peer_port} dst_port {ue_port} classid {classid}")
        if rc in (0, None) and down in (0, None):
            self.flow_rules[flow] = class_name
            return True
        return False


class Telemetry5G(TelemetryCollector):
    """Real measurements of the 5G user plane, in the snapshot format of TelemetryCollector.

    Per-class counters come from the two HTB enforcement points; delay, jitter and probe
    loss from continuous per-slice ICMP probes through each UE's PDU session; capture
    files for SliceNet from the UPF. Inherits the counter parsing and per-slice QoS."""

    def __init__(self, net: Net5G, topo: Topology5G, qos: Transport5GQoS, run_dir: Path, probe_targets: dict[str, str]):
        self.net, self.topo, self.qos, self.run_dir = net, topo, qos, Path(run_dir)
        self.class_ids = dict(qos.class_ids)
        self.snapshots: list[dict[str, Any]] = []
        self.bottleneck_bw_mbps = topo.BOTTLENECK_BW_MBPS
        self.probe_targets_5g = probe_targets
        self._captures: list[tuple[str, str, str]] = []
        self._tc_ok = True
        self._ping_pos: dict[str, int] = {}
        self._rtt_last: dict[str, float | None] = {s: None for s in SERVICES}
        self.link_events: list[dict[str, Any]] = []

    def probe_path(self, service: str) -> Path:
        return self.run_dir / f"ping_{service}.log"

    def start(self):
        container_dir = f"/cars-sf/{self.run_dir.relative_to(Path(__file__).resolve().parents[2])}"
        self._container_dir = container_dir
        for service, target in self.probe_targets_5g.items():
            self.net.get(f"tg_{service}").cmd(
                f"ping -n -O -i 0.2 -W 1 {target} > {container_dir}/ping_{service}.log 2>&1 &")
        self.last_time = time.time()

    def start_flow_capture(self):
        """SliceNet's vantage point: the UPF sees every UE's packets without GTP."""
        upf = self.net.get("upf_tap")
        for service, ip in UE_IP.items():
            name = f"upf_{service}.pcap"
            upf.cmd(f"rm -f {self._container_dir}/{name}; tcpdump -i ogstun -s 128 -U -n -w "
                    f"{self._container_dir}/{name} host {ip} > /dev/null 2>&1 &")
            self._captures.append((service, str(self.run_dir / name), ip))

    def _read_probes(self) -> tuple[dict[str, float | None], dict[str, float | None], dict[str, float]]:
        rtt, jitter, loss = {}, {}, {}
        for service in self.probe_targets_5g:
            path = self.probe_path(service)
            samples, sent = [], 0
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    handle.seek(self._ping_pos.get(service, 0))
                    text = handle.read()
                    # keep a partial last line for the next tick
                    cut = text.rfind("\n") + 1
                    self._ping_pos[service] = self._ping_pos.get(service, 0) + len(text[:cut].encode())
                    for line in text[:cut].splitlines():
                        match = re.search(r"time=([\d.]+) ms", line)
                        if match:
                            samples.append(float(match.group(1)))
                            sent += 1
                        elif "no answer yet" in line:
                            sent += 1
            except OSError:
                pass
            rtt[service] = float(np.median(samples)) if samples else None
            jitter[service] = float(np.mean(np.abs(np.diff(samples)))) if len(samples) >= 2 else None
            loss[service] = 100.0 * (sent - len(samples)) / sent if sent else 0.0
        return rtt, jitter, loss

    def poll(self, tick: int) -> dict[str, Any]:
        now = time.time()
        dt = max(now - self.last_time, 1e-3)
        self.last_time = now
        up = self._poll_tc_classes("cell_site", self.topo.n3_cell)
        down = self._poll_tc_classes("upf_tap", "ogstun")
        prev = self.snapshots[-1] if self.snapshots else None

        def mbps(stats, key, service):
            cur = (stats.get(service) or {}).get("sent_bytes")
            before = (((prev or {}).get(key) or {}).get(service) or {}).get("sent_bytes")
            return 0.0 if cur is None or before is None else max(cur - before, 0) * 8 / dt / 1e6

        service_up = {s: mbps(up, "tc_class_stats", s) for s in self.class_ids}
        service_down = {s: mbps(down, "tc_downlink_class_stats", s) for s in self.class_ids}
        total_up, total_down = sum(service_up.values()), sum(service_down.values())
        rtt, jitter, probe_loss = self._read_probes()
        drops = sum(s.get("dropped", 0) for stats in (up, down) for s in stats.values())
        previous_drops = (prev or {}).get("tc_drops_total", 0)
        fiber_up = self.topo.upf.cmd(f"cat /sys/class/net/{self.topo.fiber_upf}/operstate").strip() != "down"
        backup_iface_up = self.topo.upf.cmd(f"cat /sys/class/net/{self.topo.backup_upf}/operstate").strip() != "down"
        events, self.link_events = self.link_events, []
        snapshot = {
            "tick": tick, "timestamp": now, "interval_s": round(dt, 3),
            "telemetry_health": {
                "missing_interfaces": [], "services_without_counters": [s for s in self.class_ids if s not in up],
                "tc_ok": self._tc_ok, "ovs_stats_ok": None, "probe_age_s": None,
                "probes_stale": all(v is None for v in rtt.values()) and bool(rtt) and tick <= 2,
            },
            "tc_class_stats": up, "tc_downlink_class_stats": down,
            "tc_drops": max(drops - previous_drops, 0), "tc_drops_total": drops,
            "link_events": events,
            "queue_bytes": {s: max(v.get("backlog_bytes", 0), v.get("leaf_backlog_bytes", 0)) for s, v in up.items()},
            "service_throughput_mbps": service_up, "service_downlink_mbps": service_down,
            "bottleneck_throughput_mbps": total_up,
            "backhaul_throughput_mbps": None,
            "backhaul_up": fiber_up, "backup_backhaul_up": backup_iface_up and self.topo.active == "backup",
            "service_rtt_ms": rtt, "service_jitter_ms": jitter, "probe_loss_pct": probe_loss,
            "slice_qos": self._slice_qos(up, down, service_up, service_down, dt),
            "uplink_utilization_pct": round(min(100.0, total_up / self.bottleneck_bw_mbps * 100), 2),
            "downlink_utilization_pct": round(min(100.0, total_down / self.bottleneck_bw_mbps * 100), 2),
            "link_utilization_pct": round(min(100.0, max(total_up, total_down) / self.bottleneck_bw_mbps * 100), 2),
        }
        self.snapshots.append(snapshot)
        return snapshot

    def stop(self):
        for service in self.probe_targets_5g:
            self.net.get(f"tg_{service}").cmd("pkill ping")
        self.net.get("upf_tap").cmd("pkill tcpdump")


class FaultInjector5G(FaultInjector):
    """Faults on the routed backhaul: fiber, backup and the core cloud's links."""

    def __init__(self, net: Net5G, topo: Topology5G, spec: dict | None = None, duration: int = 30):
        super().__init__(net, spec=spec, duration=duration)
        self.topo = topo

    def inject_link_down(self, switch_name: str, intf: str):
        self.topo.upf.cmd(f"ip link set {intf} down")
        if intf not in self.active_faults:
            self.active_faults.append(intf)

    def restore_link(self, switch_name: str, intf: str):
        target = self.topo.fiber_upf if intf not in (self.topo.fiber_upf, self.topo.backup_upf) else intf
        self.topo.upf.cmd(f"ip link set {target} up")
        self.active_faults = [f for f in self.active_faults if f != target]
        self.topo.relink()

    def inject_fiber_cut(self):
        self.inject_link_down("upf_tap", self.topo.fiber_upf)

    def set_backhaul_impairment(self, extra_delay_ms: float, loss_pct: float):
        self.topo.upf.cmd(f"tc qdisc change dev {self.topo.fiber_upf} root netem "
                          f"delay {FIBER_DELAY_MS + extra_delay_ms:.0f}ms loss {loss_pct:.2f}% limit 100000")
        self.topo.core.cmd(f"tc qdisc change dev {self.topo.fiber_core} root netem "
                           f"delay {FIBER_DELAY_MS + extra_delay_ms:.0f}ms loss {loss_pct:.2f}% limit 100000")

    def _core_ports(self) -> list[str]:
        return [self.topo.fiber_upf, self.topo.backup_upf]


class LinkWatcher5G(threading.Thread):
    """Carrier state of the primary backhaul every 50 ms, reported like the Mininet link watcher."""

    def __init__(self, telemetry: Telemetry5G, topo: Topology5G, node: Node):
        super().__init__(daemon=True)
        self.telemetry, self.topo, self.node = telemetry, topo, node
        self._stop_event = threading.Event()

    def run(self):
        state = None
        while not self._stop_event.is_set():
            up = self.node.cmd(f"cat /sys/class/net/{self.topo.fiber_upf}/operstate").strip() != "down"
            if state is not None and up != state:
                self.telemetry.link_events.append({"intf": BACKHAUL_INTF, "up": up, "timestamp": time.time()})
            state = up
            time.sleep(0.05)

    def stop(self):
        self._stop_event.set()
        self.join(timeout=2)


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(COMPOSE + list(args), capture_output=True, text=True, check=check)


def stack_ready() -> bool:
    """All four slices attached with their PDU session addresses."""
    for service, ip in UE_IP.items():
        proc = compose("exec", "-T", f"tg_{service}", "ip", "-o", "-4", "addr", "show", "uesimtun0", check=False)
        if proc.returncode != 0 or ip not in proc.stdout:
            return False
    return True


def ensure_stack(timeout_s: int = 120):
    if stack_ready():
        return
    compose("up", "-d", "--remove-orphans")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if stack_ready():
            return
        time.sleep(3)
    raise RuntimeError("5G stack did not reach four attached slices; see `docker compose logs`")


os.environ.setdefault("COMPOSE_PROGRESS", "quiet")
