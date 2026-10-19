"""
Telemetry collector: interface counters, tc queue stats, RTT probes, OVS flow
stats, PCAP, and host metrics.

Counters are cumulative in the kernel; every poll converts them to per-tick
deltas so that downstream consumers (monitoring, self-healing, the scheduler)
see rates rather than ever-growing totals.
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from typing import Any

from mininet.log import info

from core.config import GENERATED_DIR, load_applications
from topology.rural_topology import (
    BACKUP_BACKHAUL_INTFS, BACKHAUL_INTF, BOTTLENECK_INTF, EDGE_DOWNLINK_INTF,
)

SERVICE_CLASS_IDS = {
    "healthcare": "1:10",
    "education": "1:20",
    "agriculture": "1:30",
    "general": "1:40",
}

_CLASS_STATS_RE = re.compile(
    r"class htb (\d+:\d+).*?Sent (\d+) bytes (\d+) pkt \(dropped (\d+).*?backlog (\d+)b",
    re.S,
)
_QDISC_STATS_RE = re.compile(r"Sent (\d+) bytes (\d+) pkt \(dropped (\d+).*?backlog (\d+)b", re.S)
_RTT_RE = re.compile(r"time=([\d.]+) ms")


class _ProbeWorker(threading.Thread):
    """Probes every service once per interval so polling never blocks on ICMP."""

    def __init__(self, collector, interval_s: float = 1.0):
        super().__init__(daemon=True)
        self.collector = collector
        self.interval_s = interval_s
        self.latest: dict[str, float | None] = {}
        self.latest_at: float | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def run(self):
        while not self._stop_event.is_set():
            started = time.time()
            rtts = self.collector._probe_rtts()
            with self._lock:
                self.latest = rtts
                self.latest_at = time.time()
            self._stop_event.wait(max(0.0, self.interval_s - (time.time() - started)))

    STALE_AFTER_S = 3.0

    def snapshot(self) -> tuple[dict[str, float | None], float | None]:
        """Latest probe results and their age; results older than 3 s are dropped (stale)."""
        with self._lock:
            age = None if self.latest_at is None else time.time() - self.latest_at
            if age is None or age > self.STALE_AFTER_S or not self.is_alive():
                return {s: None for s in self.collector.probe_targets}, age
            return dict(self.latest), age

    def stop(self):
        self._stop_event.set()


class LinkWatcher(threading.Thread):
    """Polls interface operstate every ``interval_s`` and timestamps transitions.

    Gives self-healing sub-tick failure detection (MTTD in tens of ms rather
    than the 1 s telemetry tick).
    """

    def __init__(self, intfs: list[str], interval_s: float = 0.05):
        super().__init__(daemon=True)
        self.intfs = intfs
        self.interval_s = interval_s
        self.state = {i: TelemetryCollector._link_up(i) for i in intfs}
        self.events: list[dict[str, Any]] = []
        self.changed = threading.Event()     # set on any transition: wakes the control loop
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def run(self):
        while not self._stop_event.wait(self.interval_s):
            for intf in self.intfs:
                up = TelemetryCollector._link_up(intf)
                if up != self.state[intf]:
                    with self._lock:
                        self.state[intf] = up
                        self.events.append({"intf": intf, "up": up, "timestamp": time.time()})
                    self.changed.set()

    def drain(self) -> list[dict[str, Any]]:
        with self._lock:
            events, self.events = self.events, []
        return events

    def stop(self):
        self._stop_event.set()


class TelemetryCollector:
    """Collects measurable statistics from Mininet network elements."""

    def __init__(self, net, output_dir: str | None = None, topo=None, pcap_dir: str | None = None):
        self.net = net
        self.topo = topo
        self.output_dir = output_dir or str(GENERATED_DIR / "telemetry")
        # Per-run capture directory so concurrent runs never share files.
        self.pcap_dir = pcap_dir or str(GENERATED_DIR / "pcap")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.pcap_dir, exist_ok=True)
        self.snapshots: list[dict[str, Any]] = []
        self._captures: list[tuple] = []
        self.bottleneck_bw_mbps = getattr(topo, "BOTTLENECK_BW_MBPS", 100)
        self.service_intfs: dict[str, list[str]] = {
            service: [intfs] if isinstance(intfs, str) else list(intfs)
            for service, intfs in (getattr(topo, "service_intfs", {}) or {}).items()
        }
        self.probe_targets = self._probe_targets()
        self._prev_counters: dict[str, int] = {}
        self._prev_time: float | None = None
        self._is_ovs = any("OVS" in type(sw).__name__ for sw in getattr(net, "switches", []))
        self._prober: _ProbeWorker | None = None
        self.class_ids: dict[str, str] = dict(SERVICE_CLASS_IDS)
        self._missing_intfs: list[str] = []
        self._tc_ok = True
        self.link_watcher: LinkWatcher | None = None
        self.link_events: list[dict[str, Any]] = []

    def start(self):
        info("*** Starting telemetry collection\n")
        self._start_pcap_capture()
        self._prev_counters = self._read_counters()
        self._prev_time = time.time()
        self._prober = _ProbeWorker(self)
        self._prober.start()
        watched = [BACKHAUL_INTF, BACKUP_BACKHAUL_INTFS[0], "s_core-bh", BOTTLENECK_INTF]
        self.link_watcher = LinkWatcher([i for i in watched if os.path.exists(f"/sys/class/net/{i}")])
        self.link_watcher.start()

    def _start_pcap_capture(self):
        """Capture at every application endpoint (UE and server interfaces).

        Endpoint captures share one clock, so the extractor can match each
        packet's transmission with its reception: true one-way delay and loss.
        """
        hosts = list(getattr(self.topo, "ue_hosts", [])) + list(getattr(self.topo, "server_hosts", []))
        for host in hosts:
            path = os.path.join(self.pcap_dir, f"{host.name}.pcap")
            if os.path.exists(path):
                os.remove(path)
            try:
                proc = host.popen(
                    ["tcpdump", "-Z", "root", "-i", str(host.defaultIntf()), "-s", "128",
                     "-U", "-n", "-w", path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                self._captures.append((proc, path, host.IP()))
            except Exception as exc:
                info(f"*** PCAP capture failed on {host.name}: {exc}\n")
        time.sleep(0.5)  # let tcpdump attach before traffic starts

    def poll(self, tick: int) -> dict[str, Any]:
        now = time.time()
        dt = max(now - (self._prev_time or now), 1e-3)
        counters = self._read_counters()
        delta = {
            k: max(v - self._prev_counters.get(k, v), 0) for k, v in counters.items()
        }
        self._prev_counters, self._prev_time = counters, now

        def mbps(key: str) -> float:
            return round(delta.get(key, 0) * 8 / dt / 1_000_000, 3)

        # rx on the switch-side access port = what the service's UEs offered.
        service_tput = {
            service: round(sum(mbps(f"{intf}:rx") for intf in intfs), 3)
            for service, intfs in self.service_intfs.items()
        }
        service_down = {
            service: round(sum(mbps(f"{intf}:tx") for intf in intfs), 3)
            for service, intfs in self.service_intfs.items()
        }
        bottleneck_tput = mbps(f"{BOTTLENECK_INTF}:tx")          # uplink into the edge
        downlink_tput = mbps(f"{EDGE_DOWNLINK_INTF}:tx")         # downlink into the village
        backhaul_tput = round(
            mbps(f"{BACKHAUL_INTF}:tx") + mbps(f"{BACKHAUL_INTF}:rx")
            + mbps(f"{BACKUP_BACKHAUL_INTFS[0]}:tx") + mbps(f"{BACKUP_BACKHAUL_INTFS[0]}:rx"),
            3,
        )

        class_stats = self._poll_tc_classes("s_rural", BOTTLENECK_INTF)
        downlink_stats = self._poll_tc_classes("s_edge", EDGE_DOWNLINK_INTF)
        tc_drops_total = sum(c["dropped"] for c in class_stats.values()) + sum(
            c["dropped"] for c in downlink_stats.values()
        )
        link_events = self.link_watcher.drain() if self.link_watcher else []
        self.link_events.extend(link_events)
        prev_drops = self.snapshots[-1]["tc_drops_total"] if self.snapshots else 0
        if self._prober:
            rtt, probe_age = self._prober.snapshot()
        else:
            rtt, probe_age = self._probe_rtts(), 0.0
        service_missing = sorted(
            s for s, intfs in self.service_intfs.items() if any(i in self._missing_intfs for i in intfs)
        )
        self._ovs_ok = True              # reset per tick, like _tc_ok
        flow_entries = self._poll_ovs_flow_count()
        ovs_bytes = self._poll_ovs_bytes()

        snapshot = {
            "tick": tick,
            "timestamp": now,
            # Explicit health so that "no data" is never mistaken for "zero traffic".
            "telemetry_health": {
                "missing_interfaces": list(self._missing_intfs),
                "services_without_counters": service_missing,
                "tc_ok": self._tc_ok,
                "ovs_stats_ok": self._ovs_ok if self._is_ovs else None,
                "probe_age_s": None if probe_age is None else round(probe_age, 3),
                "probes_stale": all(v is None for v in rtt.values()) and bool(rtt) and (
                    probe_age is None or probe_age > _ProbeWorker.STALE_AFTER_S),
            },
            "interval_s": round(dt, 3),
            "ovs_bytes": ovs_bytes,
            "ovs_flow_entries": flow_entries,
            "tc_drops": max(tc_drops_total - prev_drops, 0),
            "tc_drops_total": tc_drops_total,
            "tc_class_stats": class_stats,
            "tc_downlink_class_stats": downlink_stats,
            "link_events": link_events,
            "queue_bytes": {
                service: stats["backlog_bytes"] + downlink_stats.get(service, {}).get("backlog_bytes", 0)
                for service, stats in class_stats.items()
            },
            "service_throughput_mbps": service_tput,
            "service_downlink_mbps": service_down,
            "bottleneck_throughput_mbps": bottleneck_tput,
            "backhaul_throughput_mbps": backhaul_tput,
            "backhaul_up": self._link_up(BACKHAUL_INTF),
            "backup_backhaul_up": self._link_up(BACKUP_BACKHAUL_INTFS[0]),
            "service_rtt_ms": rtt,
            "host_cpu_pct": self._poll_host_cpu(),
            "host_mem_pct": self._poll_host_mem(),
            "active_flows": flow_entries,
            "uplink_utilization_pct": round(min(100.0, bottleneck_tput / self.bottleneck_bw_mbps * 100), 2),
            "downlink_utilization_pct": round(min(100.0, downlink_tput / self.bottleneck_bw_mbps * 100), 2),
            # The rural uplink is full-duplex: it is saturated if either direction is.
            "link_utilization_pct": round(
                min(100.0, max(bottleneck_tput, downlink_tput) / self.bottleneck_bw_mbps * 100), 2
            ),
        }
        self.snapshots.append(snapshot)
        return snapshot

    # ------------------------------------------------------------------ counters

    def _counter_intfs(self) -> list[str]:
        return [
            BOTTLENECK_INTF, EDGE_DOWNLINK_INTF, BACKHAUL_INTF, BACKUP_BACKHAUL_INTFS[0],
            *(intf for intfs in self.service_intfs.values() for intf in intfs),
        ]

    def _read_counters(self) -> dict[str, int]:
        counters = {}
        missing = set()
        for intf in self._counter_intfs():
            for direction in ("rx", "tx"):
                path = f"/sys/class/net/{intf}/statistics/{direction}_bytes"
                try:
                    with open(path, encoding="utf-8") as handle:
                        counters[f"{intf}:{direction}"] = int(handle.read().strip())
                except (OSError, ValueError):
                    missing.add(intf)
        self._missing_intfs = sorted(missing)
        return counters

    @staticmethod
    def _link_up(intf: str) -> bool:
        try:
            with open(f"/sys/class/net/{intf}/operstate", encoding="utf-8") as handle:
                return handle.read().strip() in ("up", "unknown")
        except OSError:
            return False

    def _poll_tc_classes(self, switch_name: str, intf: str) -> dict[str, dict[str, int]]:
        """Cumulative per-class HTB stats on one interface; falls back to the root qdisc."""
        stats: dict[str, dict[str, int]] = {}
        self._tc_ok = True
        try:
            switch = self.net.get(switch_name)
            output = switch.cmd(f"tc -s class show dev {intf} 2>/dev/null")
            by_class = {
                m.group(1): {
                    "sent_bytes": int(m.group(2)),
                    "sent_packets": int(m.group(3)),
                    "dropped": int(m.group(4)),
                    "backlog_bytes": int(m.group(5)),
                }
                for m in _CLASS_STATS_RE.finditer(output)
            }
            for name, classid in self.class_ids.items():
                if classid in by_class:
                    stats[name] = by_class[classid]
            if not stats:
                output = switch.cmd(f"tc -s qdisc show dev {intf} 2>/dev/null")
                match = _QDISC_STATS_RE.search(output)
                if match:
                    stats["aggregate"] = {
                        "sent_bytes": int(match.group(1)),
                        "sent_packets": int(match.group(2)),
                        "dropped": int(match.group(3)),
                        "backlog_bytes": int(match.group(4)),
                    }
        except Exception as exc:
            self._tc_ok = False
            info(f"*** telemetry: tc stats unavailable on {intf}: {exc} ***\n")
        return stats

    # -------------------------------------------------------------------- probes

    def _probe_targets(self) -> dict[str, tuple[str, str]]:
        """First registry application per service decides the probe target."""
        targets: dict[str, tuple[str, str]] = {}
        for app in load_applications():
            targets.setdefault(app["service_class"], (app["host"], app["server_ip"]))
        return targets

    def _probe_rtts(self) -> dict[str, float | None]:
        """One concurrent ICMP echo per service host; None means the probe was lost."""
        procs = {}
        for service, (host_name, server_ip) in self.probe_targets.items():
            try:
                host = self.net.get(host_name)
                procs[service] = host.popen(
                    ["ping", "-c1", "-W1", server_ip], stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, text=True,
                )
            except Exception:
                procs[service] = None

        rtts: dict[str, float | None] = {}
        for service, proc in procs.items():
            if proc is None:
                rtts[service] = None
                continue
            try:
                output, _ = proc.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                output = ""
            match = _RTT_RE.search(output or "")
            rtts[service] = float(match.group(1)) if match else None
        return rtts

    # ----------------------------------------------------------------------- OVS

    def _poll_ovs_bytes(self) -> int:
        total = 0
        if not self._is_ovs:
            return total
        for switch_name in ("s_rural", "s_edge", "s_core"):
            try:
                switch = self.net.get(switch_name)
                output = switch.cmd(f"ovs-ofctl dump-flows {switch_name} 2>/dev/null")
                for match in re.finditer(r"n_bytes=(\d+)", output):
                    total += int(match.group(1))
            except Exception as exc:
                self._ovs_ok = False      # reported in telemetry_health; 0 here is not "no traffic"
                info(f"*** OVS byte counters unavailable on {switch_name}: {exc} ***\n")
        return total

    def _poll_ovs_flow_count(self) -> int:
        count = 0
        if not self._is_ovs:
            return count
        try:
            switch = self.net.get("s_edge")
            output = switch.cmd("ovs-ofctl dump-flows s_edge 2>/dev/null")
            count = output.count("priority=")
        except Exception as exc:
            self._ovs_ok = False
            info(f"*** OVS flow table unavailable: {exc} ***\n")
        return count

    # ---------------------------------------------------------------------- host

    def _poll_host_cpu(self) -> float:
        try:
            import psutil
            return psutil.cpu_percent(interval=None)
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
        if self._prober:
            self._prober.stop()
            self._prober.join(timeout=3)
        if self.link_watcher:
            self.link_watcher.stop()
            self.link_watcher.join(timeout=1)
        for proc, _, _ in self._captures:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                pass

    def get_snapshots(self) -> list[dict[str, Any]]:
        return list(self.snapshots)

    def get_pcap_paths(self) -> list[str]:
        return [path for _, path, _ in self._captures if os.path.exists(path)]

    def get_capture_points(self):
        from features.packet_capture import CapturePoint
        return [
            CapturePoint(path=path, host_ip=ip)
            for _, path, ip in self._captures if os.path.exists(path)
        ]
