"""
QoS Enforcer (architecture.md §4.5): translates allocations into network policy.

Backends
  tc   Linux HTB on both directions of the rural uplink (uplink egress on
       s_rural, downlink egress on s_edge) with fq_codel leaves to bound
       per-slice queueing delay. Works on any Mininet switch type.
  ovs  Open vSwitch linux-htb QoS + queues with OpenFlow set_queue rules
       (needs real OVS, i.e. a sudo run).

Classification (which traffic belongs to which class)
  host     UE address → its service (realistic: a UE belongs to one institution);
           unknown/mixed UEs fall into the default class
  app      registry knowledge of each application's server/port (oracle; also
           how 3GPP slices map applications by slice type)
  slicenet host rules plus per-flow rules installed at runtime from SliceNet
           predictions (``classify_flow``)
"""

from __future__ import annotations

import re
from typing import Any

from mininet.log import info

from core.config import load_yaml
from topology.rural_topology import BOTTLENECK_INTF, EDGE_DOWNLINK_INTF, SERVICE_IP_BASE, ue_ip

UPLINK, DOWNLINK = "uplink", "downlink"
_RC_RE = re.compile(r"__rc=(\d+)")
_CLASS_RATE_RE = re.compile(r"class htb (\d+:\d+) .*?rate (\d+(?:\.\d+)?)([KMG]?)bit ceil (\d+(?:\.\d+)?)([KMG]?)bit")
_UNIT = {"": 1e-6, "K": 1e-3, "M": 1.0, "G": 1e3}
FLOW_PRIO, APP_PRIO, HOST_PRIO = 1, 10, 20


def _class_table(mode: str) -> dict[str, dict[str, Any]]:
    slices = load_yaml("slices.yaml")
    return slices["tgpp_slices"] if mode == "tgpp" else slices["service_slices"]


class QoSEnforcer:
    """Enforces bandwidth allocation using Linux HTB traffic control."""

    SERVICE_CLASS_IDS = {
        "healthcare": "1:10",
        "education": "1:20",
        "agriculture": "1:30",
        "general": "1:40",
    }

    def __init__(
        self,
        net=None,
        bottleneck_intf: str = BOTTLENECK_INTF,
        downlink_intf: str = EDGE_DOWNLINK_INTF,
        class_mode: str = "service",
        classification: str = "host",
        work_conserving: bool = True,
        backend: str = "tc",
        aqm: bool = True,
    ):
        self.net = net
        self.aqm = aqm
        self.bottleneck_intf = bottleneck_intf
        self.downlink_intf = downlink_intf
        self.class_mode = class_mode            # service | tgpp | none
        self.classification = classification    # host | app | slicenet
        self.work_conserving = work_conserving
        self.backend = backend
        self.classes = {} if class_mode == "none" else _class_table(class_mode)
        self.class_ids = {name: cfg["class_id"] for name, cfg in self.classes.items()}
        self.default_class = (
            "general" if class_mode == "service" else "eMBB" if class_mode == "tgpp" else None
        )
        self.capacity = 100.0
        self._configured = False
        self.flow_rules: dict[tuple, str] = {}
        self.applied: list[dict[str, float]] = []
        self._last_rc_known: list[bool] = []

    # ------------------------------------------------------------------ setup

    def _directions(self):
        return (
            (UPLINK, self.net.get("s_rural"), self.bottleneck_intf),
            (DOWNLINK, self.net.get("s_edge"), self.downlink_intf),
        )

    def setup_htb(self, total_bandwidth_mbps: float = 100.0, spawns: list[dict] | None = None):
        """Create the qdisc hierarchy on both directions of the bottleneck."""
        if self.net is None:
            return
        self.capacity = float(total_bandwidth_mbps)
        cap = int(self.capacity)
        if self.backend == "ovs":
            self._setup_ovs(spawns or [])
            return
        for _, switch, iface in self._directions():
            switch.cmd(f"tc qdisc del dev {iface} root 2>/dev/null")
            if self.class_mode == "none":
                # Traditional single FIFO (tail drop) shaped to link capacity.
                switch.cmd(f"tc qdisc add dev {iface} root handle 1: htb default 1 r2q 100")
                switch.cmd(f"tc class add dev {iface} parent 1: classid 1:1 htb rate {cap}mbit ceil {cap}mbit quantum 1514")
                switch.cmd(f"tc qdisc add dev {iface} parent 1:1 handle 2: pfifo limit 1000")
                continue
            default_minor = self.class_ids[self.default_class].split(":")[1]
            switch.cmd(f"tc qdisc add dev {iface} root handle 1: htb default {default_minor} r2q 100")
            switch.cmd(
                f"tc class add dev {iface} parent 1: classid 1:1 htb rate {cap}mbit ceil {cap}mbit quantum 1514"
            )
            for name, cfg in self.classes.items():
                classid = cfg["class_id"]
                switch.cmd(
                    f"tc class add dev {iface} parent 1:1 classid {classid} htb "
                    f"rate 1mbit ceil {cap}mbit prio {cfg['htb_prio']} quantum 1514"
                )
                # fq_codel leaf keeps per-slice queueing delay bounded; HTB's
                # default FIFO leaf would buffer ~1000 packets (bufferbloat).
                handle = classid.split(":")[1]
                leaf = "fq_codel" if self.aqm else "pfifo limit 1000"
                switch.cmd(f"tc qdisc add dev {iface} parent {classid} handle {handle}: {leaf}")
        if self.class_mode != "none":
            self._install_filters(spawns or [])
        self._configured = True
        info(f"*** QoS ({self.backend}/{self.class_mode}/{self.classification}) configured ***\n")

    def _install_filters(self, spawns: list[dict]):
        if self.class_mode == "tgpp" or self.classification == "app":
            for spawn in spawns:
                self._app_filters(spawn)
        if self.class_mode == "service":
            for service in SERVICE_IP_BASE:
                for i in range(1, 10):
                    self._host_filter(ue_ip(service, i), self.class_ids[service])

    def _class_for_spawn(self, spawn: dict) -> str:
        key = spawn["slice_type"] if self.class_mode == "tgpp" else spawn["service_class"]
        return self.class_ids[key]

    def _app_filters(self, spawn: dict):
        classid = self._class_for_spawn(spawn)
        ue, server, port = spawn["host_ip"], spawn["server_ip"], spawn["port"]
        for direction, switch, iface in self._directions():
            src, dst = (ue, server) if direction == UPLINK else (server, ue)
            for field in ("sport", "dport"):
                switch.cmd(
                    f"tc filter add dev {iface} protocol ip parent 1: prio {APP_PRIO} u32 "
                    f"match ip src {src}/32 match ip dst {dst}/32 match ip {field} {port} 0xffff "
                    f"flowid {classid}"
                )

    def _host_filter(self, address: str, classid: str):
        for direction, switch, iface in self._directions():
            field = "src" if direction == UPLINK else "dst"
            switch.cmd(
                f"tc filter add dev {iface} protocol ip parent 1: prio {HOST_PRIO} u32 "
                f"match ip {field} {address}/32 flowid {classid}"
            )

    def classify_flow(self, flow: tuple, class_name: str) -> bool:
        """Install a per-flow rule (ue_ip, peer_ip, proto, ue_port, peer_port) → class."""
        if self.net is None or class_name not in self.class_ids or self.flow_rules.get(flow) == class_name:
            return False
        if flow in self.flow_rules:
            return False  # u32 rules are append-only here; first decision sticks
        ue, peer, _, ue_port, peer_port = flow
        classid = self.class_ids[class_name]
        for direction, switch, iface in self._directions():
            src, dst, sport, dport = (
                (ue, peer, ue_port, peer_port) if direction == UPLINK else (peer, ue, peer_port, ue_port)
            )
            switch.cmd(
                f"tc filter add dev {iface} protocol ip parent 1: prio {FLOW_PRIO} u32 "
                f"match ip src {src}/32 match ip dst {dst}/32 "
                f"match ip sport {sport} 0xffff match ip dport {dport} 0xffff flowid {classid}"
            )
        self.flow_rules[flow] = class_name
        return True

    # ------------------------------------------------------------- allocation

    def apply_allocation(
        self, allocation: dict[str, float], ceilings: dict[str, float] | None = None
    ) -> dict[str, Any]:
        """Apply bandwidth allocation to HTB classes (both directions) and verify it.

        ``ceilings`` overrides the borrowing limit per class (e.g. core-bound
        slices while the smaller backup backhaul is in use).

        Returns an enforcement record: every command's exit status is checked
        and the classes are read back from the kernel and compared with the
        intended rate/ceil. ``verified`` is True (read-back matches), False
        (a command failed or the kernel state differs) or None (backend gives
        no read-back, e.g. no network attached).
        """
        ceilings = ceilings or {}
        self._last_rc_known = []
        result: dict[str, Any] = {"allocation": dict(allocation), "failures": [], "mismatches": [], "verified": None}
        if self.net is None:
            self._print_commands(allocation)
            return result
        if not self._configured:
            self.setup_htb(total_bandwidth_mbps=max(sum(allocation.values()), 100))
        if self.class_mode == "none":
            result["verified"] = True
            return result
        self.applied.append(dict(allocation))
        if self.backend == "ovs":
            self._apply_ovs(allocation)
            return result
        cap = int(self.capacity)
        intended: dict[tuple[str, str], tuple[int, int]] = {}
        for direction, switch, iface in self._directions():
            for name, bandwidth in allocation.items():
                classid = self.class_ids.get(name)
                if not classid:
                    continue
                bw = max(int(round(bandwidth)), 1)
                ceil = cap if self.work_conserving else bw
                if name in ceilings:
                    ceil = max(min(ceil, int(round(ceilings[name]))), bw)
                rc = self._run(
                    switch,
                    f"tc class change dev {iface} parent 1:1 classid {classid} htb "
                    f"rate {bw}mbit ceil {ceil}mbit quantum 1514",
                )
                if rc not in (0, None):
                    result["failures"].append({"direction": direction, "class": name, "rc": rc})
                intended[(iface, classid)] = (bw, ceil)
        result["mismatches"] = self._verify(intended)
        observed = any(rc_known for rc_known in self._last_rc_known)
        if result["failures"] or result["mismatches"]:
            result["verified"] = False
        elif observed:
            result["verified"] = True
        info(f"*** QoS allocation applied: {allocation} (verified={result['verified']}) ***\n")
        return result

    def _run(self, switch, command: str) -> int | None:
        """Run a command on a switch and return its exit status (None if unknown)."""
        output = switch.cmd(f"{command}; echo __rc=$?") or ""
        match = _RC_RE.search(output)
        self._last_rc_known.append(match is not None)
        return int(match.group(1)) if match else None

    def read_classes(self, switch, iface: str) -> dict[str, tuple[float, float]]:
        """Kernel view of HTB classes on an interface: classid → (rate, ceil) in Mbit/s."""
        output = switch.cmd(f"tc class show dev {iface}") or ""
        return {
            m.group(1): (float(m.group(2)) * _UNIT[m.group(3)], float(m.group(4)) * _UNIT[m.group(5)])
            for m in _CLASS_RATE_RE.finditer(output)
        }

    def _verify(self, intended: dict[tuple[str, str], tuple[int, int]]) -> list[dict[str, Any]]:
        mismatches = []
        by_iface: dict[str, dict] = {}
        for _, switch, iface in self._directions():
            by_iface[iface] = self.read_classes(switch, iface)
        for (iface, classid), (rate, ceil) in intended.items():
            actual = by_iface.get(iface, {}).get(classid)
            if actual is None:
                if by_iface.get(iface):   # kernel answered but the class is missing
                    mismatches.append({"iface": iface, "class": classid, "expected": (rate, ceil), "actual": None})
                continue
            if abs(actual[0] - rate) > 0.5 or abs(actual[1] - ceil) > 0.5:
                mismatches.append({"iface": iface, "class": classid, "expected": (rate, ceil), "actual": actual})
        return mismatches

    def get_queue_stats(self) -> dict[str, dict]:
        stats = {}
        if self.net is None:
            return stats
        switch = self.net.get("s_rural")
        output = switch.cmd(f"tc -s class show dev {self.bottleneck_intf} 2>/dev/null")
        for service, classid in self.class_ids.items():
            stats[service] = {"classid": classid, "raw": output}
        return stats

    def cleanup(self):
        if self.net is None:
            return
        for _, switch, iface in self._directions():
            switch.cmd(f"tc qdisc del dev {iface} root 2>/dev/null")
        self._configured = False

    # -------------------------------------------------------------------- OVS

    def _setup_ovs(self, spawns: list[dict]):
        """linux-htb QoS with one queue per class on both bottleneck ports."""
        cap_bps = int(self.capacity * 1e6)
        for _, switch, iface in self._directions():
            queues = " ".join(
                f"queues:{i}=@q{i}" for i in range(1, len(self.classes) + 1)
            )
            create = " ".join(
                f"-- --id=@q{i} create queue other-config:min-rate=1000000 other-config:max-rate={cap_bps}"
                for i in range(1, len(self.classes) + 1)
            )
            switch.cmd(
                f"ovs-vsctl -- set port {iface} qos=@qos -- --id=@qos create qos type=linux-htb "
                f"other-config:max-rate={cap_bps} {queues} {create}"
            )
        self._ovs_queue = {name: i for i, name in enumerate(self.classes, start=1)}
        s_rural, s_edge = self.net.get("s_rural"), self.net.get("s_edge")
        for service in SERVICE_IP_BASE if self.class_mode == "service" else []:
            q = self._ovs_queue[service]
            for i in range(1, 10):
                address = ue_ip(service, i)
                s_rural.cmd(f"ovs-ofctl add-flow s_rural priority=20,ip,nw_src={address},actions=set_queue:{q},normal")
                s_edge.cmd(f"ovs-ofctl add-flow s_edge priority=20,ip,nw_dst={address},actions=set_queue:{q},normal")
        if self.class_mode == "tgpp" or self.classification == "app":
            for spawn in spawns:
                key = spawn["slice_type"] if self.class_mode == "tgpp" else spawn["service_class"]
                q = self._ovs_queue[key]
                proto = "udp" if spawn["protocol"] == "udp" else "tcp"
                for field in ("tp_src", "tp_dst"):
                    s_rural.cmd(
                        f"ovs-ofctl add-flow s_rural priority=30,{proto},nw_src={spawn['host_ip']},"
                        f"nw_dst={spawn['server_ip']},{field}={spawn['port']},actions=set_queue:{q},normal"
                    )
                    s_edge.cmd(
                        f"ovs-ofctl add-flow s_edge priority=30,{proto},nw_src={spawn['server_ip']},"
                        f"nw_dst={spawn['host_ip']},{field}={spawn['port']},actions=set_queue:{q},normal"
                    )
        self._configured = True
        info("*** QoS (ovs linux-htb) configured ***\n")

    def _apply_ovs(self, allocation: dict[str, float]):
        cap_bps = int(self.capacity * 1e6)
        for _, switch, iface in self._directions():
            for name, bandwidth in allocation.items():
                if name not in self._ovs_queue:
                    continue
                rate = max(int(bandwidth * 1e6), 1_000_000)
                ceil = cap_bps if self.work_conserving else rate
                switch.cmd(
                    f"ovs-vsctl set queue $(ovs-vsctl get qos $(ovs-vsctl get port {iface} qos) "
                    f"queues:{self._ovs_queue[name]}) other-config:min-rate={rate} other-config:max-rate={ceil}"
                )

    def _print_commands(self, allocation: dict[str, float]):
        print("\nGenerated QoS Commands (no Mininet net attached)")
        print("-" * 40)
        for service, bandwidth in allocation.items():
            classid = self.class_ids.get(service, "?")
            print(f"  tc class change ... classid {classid} rate {bandwidth}Mbit  # {service}")
