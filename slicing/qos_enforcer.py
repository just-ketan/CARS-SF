"""
QoS Enforcer — applies allocation decisions to Mininet via Linux tc HTB.

Maps service classes to HTB classes on the bottleneck link and sets
bandwidth limits based on the allocation engine output.
"""

from __future__ import annotations

from mininet.log import info

from topology.rural_topology import SERVICE_HOSTS


class QoSEnforcer:
    """Enforces bandwidth allocation using Linux HTB traffic control."""

    SERVICE_CLASS_IDS = {
        "healthcare": "1:10",
        "education": "1:20",
        "agriculture": "1:30",
        "general": "1:40",
    }

    def __init__(self, net=None, bottleneck_intf: str = "s_rural-eth4"):
        self.net = net
        self.bottleneck_intf = bottleneck_intf
        self._configured = False

    def setup_htb(self, total_bandwidth_mbps: float = 100.0):
        """Create HTB root qdisc and per-service classes on bottleneck link."""
        if self.net is None:
            return

        switch = self.net.get("s_rural")
        iface = self.bottleneck_intf

        switch.cmd(f"tc qdisc del dev {iface} root 2>/dev/null")
        switch.cmd(f"tc qdisc add dev {iface} root handle 1: htb default 40")
        switch.cmd(
            f"tc class add dev {iface} parent 1: classid 1:1 htb "
            f"rate {int(total_bandwidth_mbps)}mbit ceil {int(total_bandwidth_mbps)}mbit"
        )

        priorities = {"healthcare": 1, "education": 2, "agriculture": 3, "general": 4}
        for service, classid in self.SERVICE_CLASS_IDS.items():
            switch.cmd(
                f"tc class add dev {iface} parent 1:1 classid {classid} htb "
                f"rate 1mbit ceil {int(total_bandwidth_mbps)}mbit "
                f"prio {priorities[service]}"
            )

        self._setup_filters(switch, iface)
        self._configured = True
        info(f"*** HTB queues configured on {iface} ***\n")

    def _setup_filters(self, switch, iface: str):
        """Map UE source IPs to HTB classes via u32 filters."""
        ip_class_map = {
            "10.0.1.10": "1:10",  # healthcare
            "10.0.1.20": "1:20",  # education
            "10.0.1.30": "1:30",  # agriculture
            "10.0.1.40": "1:40",  # general
        }
        prio = 1
        for src_ip, classid in ip_class_map.items():
            switch.cmd(
                f"tc filter add dev {iface} protocol ip parent 1: prio {prio} "
                f"u32 match ip src {src_ip}/32 flowid {classid}"
            )
            prio += 1

    def apply_allocation(self, allocation: dict[str, float]):
        """Apply bandwidth allocation to HTB classes."""
        if self.net is None:
            self._print_commands(allocation)
            return

        if not self._configured:
            total = sum(allocation.values())
            self.setup_htb(total_bandwidth_mbps=max(total, 100))

        switch = self.net.get("s_rural")
        iface = self.bottleneck_intf

        for service, bandwidth in allocation.items():
            classid = self.SERVICE_CLASS_IDS.get(service)
            if not classid:
                continue
            bw = max(int(bandwidth), 1)
            switch.cmd(
                f"tc class change dev {iface} parent 1:1 classid {classid} htb "
                f"rate {bw}mbit ceil {bw}mbit"
            )
            info(f"*** QoS: {service} → {bw} Mbps (class {classid}) ***\n")

    def get_queue_stats(self) -> dict[str, dict]:
        """Read current queue statistics from tc."""
        stats = {}
        if self.net is None:
            return stats

        switch = self.net.get("s_rural")
        output = switch.cmd(
            f"tc -s class show dev {self.bottleneck_intf} 2>/dev/null"
        )
        for service, classid in self.SERVICE_CLASS_IDS.items():
            stats[service] = {"classid": classid, "raw": output}
        return stats

    def cleanup(self):
        if self.net is None:
            return
        switch = self.net.get("s_rural")
        switch.cmd(f"tc qdisc del dev {self.bottleneck_intf} root 2>/dev/null")
        self._configured = False

    def _print_commands(self, allocation: dict[str, float]):
        print("\nGenerated QoS Commands (no Mininet net attached)")
        print("-" * 40)
        for service, bandwidth in allocation.items():
            classid = self.SERVICE_CLASS_IDS.get(service, "?")
            print(f"  tc class change ... classid {classid} rate {bandwidth}Mbit  # {service}")
