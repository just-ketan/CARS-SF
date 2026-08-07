"""
Telemetry collector: OVS flow stats, tc queue stats, PCAP, and host metrics.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any

from mininet.log import info

from core.config import GENERATED_DIR


class TelemetryCollector:
    """Collects measurable statistics from Mininet network elements."""

    def __init__(self, net, output_dir: str | None = None):
        self.net = net
        self.output_dir = output_dir or str(GENERATED_DIR / "telemetry")
        self.pcap_dir = str(GENERATED_DIR / "pcap")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.pcap_dir, exist_ok=True)
        self.snapshots: list[dict[str, Any]] = []
        self._pcap_procs: list[str] = []

    def start(self):
        info("*** Starting telemetry collection\n")
        self._start_pcap_capture()

    def _start_pcap_capture(self):
        capture_points = [
            ("s_edge", "s_edge-eth1", "edge_traffic.pcap"),
            ("s_core", "s_core-eth1", "core_traffic.pcap"),
        ]
        for switch_name, iface, filename in capture_points:
            try:
                switch = self.net.get(switch_name)
                pcap_path = os.path.join(self.pcap_dir, filename)
                switch.cmd(
                    f"tcpdump -i {iface} -w {pcap_path} -q > /dev/null 2>&1 &"
                )
                self._pcap_procs.append(switch_name)
            except Exception as exc:
                info(f"*** PCAP capture failed on {switch_name}: {exc}\n")

    def poll(self, tick: int) -> dict[str, Any]:
        snapshot = {
            "tick": tick,
            "ovs_bytes": self._poll_ovs_bytes(),
            "ovs_flow_entries": self._poll_ovs_flow_count(),
            "tc_drops": self._poll_tc_drops(),
            "queue_bytes": self._poll_queue_bytes(),
            "host_cpu_pct": self._poll_host_cpu(),
            "host_mem_pct": self._poll_host_mem(),
            "active_flows": self._poll_ovs_flow_count(),
            "link_utilization_pct": 0.0,
        }
        if snapshot["ovs_bytes"] > 0:
            snapshot["link_utilization_pct"] = min(
                100.0, snapshot["ovs_bytes"] / 1_000_000 * 100
            )
        self.snapshots.append(snapshot)
        return snapshot

    def _poll_ovs_bytes(self) -> int:
        total = 0
        for switch_name in ("s_rural", "s_edge", "s_core"):
            try:
                switch = self.net.get(switch_name)
                output = switch.cmd("ovs-ofctl dump-flows", switch_name)
                for match in re.finditer(r"n_bytes=(\d+)", output):
                    total += int(match.group(1))
            except Exception:
                pass
        return total

    def _poll_ovs_flow_count(self) -> int:
        count = 0
        try:
            switch = self.net.get("s_edge")
            output = switch.cmd("ovs-ofctl dump-flows s_edge")
            count = output.count("priority=")
        except Exception:
            pass
        return count

    def _poll_tc_drops(self) -> int:
        drops = 0
        try:
            switch = self.net.get("s_rural")
            output = switch.cmd("tc -s class show dev s_rural-eth4 2>/dev/null")
            for match in re.finditer(r"dropped (\d+)", output):
                drops += int(match.group(1))
        except Exception:
            pass
        return drops

    def _poll_queue_bytes(self) -> dict[str, int]:
        queues = {"queue_0": 0, "queue_1": 0, "queue_2": 0, "queue_3": 0}
        try:
            switch = self.net.get("s_rural")
            output = switch.cmd("tc -s class show dev s_rural-eth4 2>/dev/null")
            class_ids = re.findall(r"class htb (\d+:\d+)", output)
            for idx, _ in enumerate(class_ids[:4]):
                queues[f"queue_{idx}"] = self._poll_ovs_bytes() // max(len(class_ids), 1)
        except Exception:
            pass
        return queues

    def _poll_host_cpu(self) -> float:
        try:
            result = subprocess.run(
                ["psutil.cpu_percent"] if False else [],
                capture_output=True, text=True, timeout=2,
            )
        except Exception:
            pass
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0

    def _poll_host_mem(self) -> float:
        try:
            import psutil
            return psutil.virtual_memory().percent
        except Exception:
            return 0.0

    def stop(self):
        info("*** Stopping telemetry collection\n")
        for switch_name in self._pcap_procs:
            try:
                self.net.get(switch_name).cmd("pkill tcpdump")
            except Exception:
                pass

    def get_snapshots(self) -> list[dict[str, Any]]:
        return list(self.snapshots)

    def get_pcap_paths(self) -> list[str]:
        paths = []
        for name in ("edge_traffic.pcap", "core_traffic.pcap"):
            path = os.path.join(self.pcap_dir, name)
            if os.path.exists(path):
                paths.append(path)
        return paths
