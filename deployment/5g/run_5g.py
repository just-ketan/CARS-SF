#!/usr/bin/env python3
"""
CARS-SF on a real 5G core (Open5GS + UERANSIM, see docker-compose.yml).

Each service is a 5G network slice (S-NSSAI) with its own DNN and UE address
pool; the CARS-SF slice controller enforces its allocation on the UPF (HTB +
fq_codel on N6 egress for uplink and on ogstun for downlink, classified by
slice address pool). Traffic, captures, packet matching and KPIs reuse the
Mininet pipeline unchanged.

    docker compose -f deployment/5g/docker-compose.yml up -d
    python deployment/5g/run_5g.py --scenario disaster --duration 40 --mode both
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from analysis.metrics import jain_fairness, slice_kpis, weighted_utility  # noqa: E402
from core.config import RESULTS_DIR, load_applications, load_scenarios, load_yaml  # noqa: E402
from core.controller import SliceController  # noqa: E402
from features.extractor import FlowFeatureExtractor  # noqa: E402
from features.packet_capture import CapturePoint  # noqa: E402
from traffic.models import mean_rate_mbps, scaled  # noqa: E402

COMPOSE = ["docker", "compose", "-f", os.path.join(os.path.dirname(os.path.abspath(__file__)), "docker-compose.yml")]
SERVICES = ("healthcare", "education", "agriculture", "general")
UE_IP = {"healthcare": "10.60.0.2", "education": "10.61.0.2", "agriculture": "10.62.0.2", "general": "10.63.0.2"}
SLICE_NET = {s: ip.rsplit(".", 1)[0] + ".0/24" for s, ip in UE_IP.items()}
DN_IP, UPF_N6_IP = "10.81.0.100", "10.81.0.10"
CORE_PORT_OFFSET = 100   # core-cloud apps reuse port numbers; one DN hosts everything here
OUT_DIR = RESULTS_DIR / "5g"


def sh(service: str, command: str, detach: bool = False, check: bool = False) -> str:
    args = COMPOSE + ["exec", "-T"] + (["-d"] if detach else []) + [service, "sh", "-c", command]
    proc = subprocess.run(args, capture_output=True, text=True, check=check)
    return proc.stdout


class UpfQoS:
    """CARS-SF QoS backend for the UPF: same interface as slicing.qos_enforcer."""

    def __init__(self, capacity: float, enforce: bool):
        self.capacity, self.enforce = capacity, enforce
        slices = load_yaml("slices.yaml")["service_slices"]
        self.class_ids = {s: slices[s]["class_id"] for s in SERVICES}
        self.prio = {s: slices[s]["htb_prio"] for s in SERVICES}
        out = sh("core", "ip -o -4 addr show")
        self.n6 = re.search(rf"\d+: (\S+)\s+inet {re.escape(UPF_N6_IP)}/", out).group(1)
        self.dirs = (("uplink", self.n6, "src"), ("downlink", "ogstun", "dst"))
        self.applied: list[dict] = []

    def setup(self):
        cap = int(self.capacity)
        cmds = []
        for _, iface, field in self.dirs:
            cmds.append(f"tc qdisc del dev {iface} root 2>/dev/null")
            if not self.enforce:   # one FIFO shaped to capacity: no slicing
                cmds += [f"tc qdisc add dev {iface} root handle 1: htb default 1 r2q 100",
                         f"tc class add dev {iface} parent 1: classid 1:1 htb rate {cap}mbit ceil {cap}mbit quantum 1514",
                         f"tc qdisc add dev {iface} parent 1:1 handle 2: pfifo limit 1000"]
                continue
            cmds += [f"tc qdisc add dev {iface} root handle 1: htb default 40 r2q 100",
                     f"tc class add dev {iface} parent 1: classid 1:1 htb rate {cap}mbit ceil {cap}mbit quantum 1514"]
            for s in SERVICES:
                cid = self.class_ids[s]
                cmds += [f"tc class add dev {iface} parent 1:1 classid {cid} htb rate 1mbit ceil {cap}mbit prio {self.prio[s]} quantum 1514",
                         f"tc qdisc add dev {iface} parent {cid} handle {cid.split(':')[1]}: fq_codel",
                         f"tc filter add dev {iface} protocol ip parent 1: prio 10 u32 match ip {field} {SLICE_NET[s]} flowid {cid}"]
        sh("core", " ; ".join(cmds))

    def apply_allocation(self, allocation: dict[str, float], ceilings: dict | None = None):
        if not self.enforce:
            return
        self.applied.append(dict(allocation))
        cap = int(self.capacity)
        cmds = [
            f"tc class change dev {iface} parent 1:1 classid {self.class_ids[s]} htb "
            f"rate {max(int(round(bw)), 1)}mbit ceil {cap}mbit quantum 1514"
            for _, iface, _ in self.dirs for s, bw in allocation.items() if s in self.class_ids
        ]
        sh("core", " ; ".join(cmds))

    def class_stats(self, iface: str) -> dict:
        out = sh("core", f"tc -s class show dev {iface}")
        stats = {}
        for m in re.finditer(r"class htb (\d+:\d+).*?Sent (\d+) bytes (\d+) pkt \(dropped (\d+).*?backlog (\d+)b", out, re.S):
            for s, cid in self.class_ids.items():
                if cid == m.group(1):
                    stats[s] = {"sent_bytes": int(m.group(2)), "sent_packets": int(m.group(3)),
                                "dropped": int(m.group(4)), "backlog_bytes": int(m.group(5))}
        return stats


def plan_traffic(scenario: dict, scale: float, duration: float, seed: int) -> list[dict]:
    apps = load_applications()
    nominal = {s: sum(mean_rate_mbps(a["model"], a.get("params", {})) for a in apps if a["service_class"] == s)
               for s in SERVICES}
    plans = []
    for i, app in enumerate(apps):
        s = app["service_class"]
        factor = scenario["demand_mbps"][s] * scale / nominal[s]
        params, instances = scaled(app["model"], app.get("params", {}), factor)
        port = app["port"] + (CORE_PORT_OFFSET if app["server"] == "srv_core" else 0)
        plans.append({
            "application_id": app["application_id"], "service_class": s, "slice_type": app["slice_type"],
            "priority": app["priority"], "host": f"ue_{s}", "host_ip": UE_IP[s], "server": "dn",
            "server_ip": DN_IP, "port": port, "protocol": app["protocol"],
            "direction": app.get("direction", "up"), "model": app["model"], "params": params,
            "instances": instances, "dscp": app.get("dscp", 0), "sla": app.get("sla", {}),
            "latency_requirement_ms": app.get("latency_requirement_ms", 100), "seed": seed * 1000 + i,
        })
    return plans


def run_mode(scenario_id: str, duration: int, capacity: float, enforce: bool, seed: int) -> dict:
    scenario = {s["id"]: s for s in load_scenarios()}[scenario_id]
    scale = capacity / 100.0
    demand = {s: v * scale for s, v in scenario["demand_mbps"].items()}
    plans = plan_traffic(scenario, scale, duration + 15, seed)
    run_id = f"5g__{scenario_id}__{'cars_sf' if enforce else 'no_slicing'}__s{seed}"

    for s in SERVICES:   # user-plane routes towards the data network through the PDU session
        sh(f"ue_{s}", "ip route replace 10.81.0.0/24 dev uesimtun0")
    sh("dn", "ip route replace 10.60.0.0/14 via " + UPF_N6_IP)

    qos = UpfQoS(capacity, enforce)
    qos.setup()
    controller = SliceController("proposed", capacity, qos=qos, control_interval_ticks=5)
    qos.apply_allocation(controller.start(scenario_id, demand))

    # Sinks: the data network for uplink/request-response apps, each UE for downlink pushes.
    receivers: dict[str, dict[str, set]] = {}
    for p in plans:
        to_ue = p["direction"] == "down" and (p["protocol"] == "udp" or p["model"] == "bulk_tcp")
        target = f"tg_{p['service_class']}" if to_ue else "dn"
        receivers.setdefault(target, {"udp": set(), "tcp": set()})[p["protocol"]].add(p["port"])
    for target, ports in receivers.items():
        sh(target, f"cd /cars-sf && python -m traffic.sink --udp {','.join(map(str, sorted(ports['udp'])))} "
                   f"--tcp {','.join(map(str, sorted(ports['tcp'])))} > /tmp/sink.log 2>&1", detach=True)
    capture_hosts = {f"tg_{s}": ("uesimtun0", UE_IP[s]) for s in SERVICES} | {"dn": ("eth0", DN_IP)}
    for target, (iface, _) in capture_hosts.items():
        sh(target, f"rm -f /tmp/cap.pcap; tcpdump -i {iface} -s 128 -U -n -w /tmp/cap.pcap > /dev/null 2>&1", detach=True)
    time.sleep(2)

    for p in plans:
        sender_is_server = p["direction"] == "down" and (p["protocol"] == "udp" or p["model"] == "bulk_tcp")
        sender = "dn" if sender_is_server else f"tg_{p['service_class']}"
        dst = p["host_ip"] if sender_is_server else DN_IP
        params = json.dumps(p["params"]).replace('"', '\\"')
        sh(sender, f"cd /cars-sf && python -m traffic.generator --proto {p['protocol']} --dst {dst} "
                   f"--port {p['port']} --model {p['model']} --params \"{params}\" --duration {p['instances'] and duration + 15} "
                   f"--dscp {p['dscp']} --seed {p['seed']} --instances {p['instances']} >> /tmp/gen.log 2>&1", detach=True)

    prev = {}
    start = time.time()
    for tick in range(1, duration + 1):
        time.sleep(max(0.0, start + tick - time.time()))
        up, down = qos.class_stats(qos.n6), qos.class_stats("ogstun")
        offered = {}
        for s in SERVICES:
            u = up.get(s, {})
            vol = u.get("sent_bytes", 0) + u.get("dropped", 0) * u.get("sent_bytes", 0) / max(u.get("sent_packets", 1), 1)
            offered[s] = max(vol - prev.get(s, vol), 0) * 8 / 1e6
            prev[s] = vol
        snapshot = {"tick": tick, "interval_s": 1.0, "service_throughput_mbps": offered,
                    "tc_downlink_class_stats": down, "queue_bytes": {}}
        controller.step(tick, snapshot, {"context": scenario_id}, {"state": "normal", "boosts": {}}, demand)

    for target in list(receivers) + [p for p in ("tg_healthcare", "tg_education", "tg_agriculture", "tg_general")]:
        sh(target, "pkill -f '[t]raffic.generator'; pkill -f '[t]raffic.sink'")
    for target in capture_hosts:
        sh(target, "pkill tcpdump")
    time.sleep(1)

    work = tempfile.mkdtemp(prefix=run_id)
    points = []
    for target, (_, ip) in capture_hosts.items():
        path = os.path.join(work, f"{target}.pcap")
        subprocess.run(COMPOSE + ["cp", f"{target}:/tmp/cap.pcap", path], capture_output=True, check=False)
        if os.path.exists(path):
            points.append(CapturePoint(path, ip))
    extractor = FlowFeatureExtractor(points, spawn_metadata=plans, ue_ips=set(UE_IP.values()), window_s=5.0)
    import pandas as pd

    df = pd.DataFrame(extractor.extract())
    shutil.rmtree(work, ignore_errors=True)
    contract = {"ok": False, "errors": ["no captured flows"]}
    if not df.empty:
        from dataset.builder import DatasetBuilder
        from features.contract import stamp, validate

        df = DatasetBuilder(df.to_dict("records"), scenario_id=scenario_id, context_name=scenario_id).build()
        df["run_id"] = run_id
        df = stamp(df, "5g_core_measured", seed, run_id)
        contract = validate(df, "5g_core_measured", raise_on_error=False).as_dict()
    kpis = slice_kpis(df, demand) if not df.empty else {}
    weights = controller.priority_engine.context_engine.get_context(scenario_id)
    result = {
        "run_id": run_id, "scenario": scenario_id, "mode": "cars_sf" if enforce else "no_slicing",
        "capacity_mbps": capacity, "demand_mbps": demand, "records": len(df),
        "allocations": qos.applied, "slice_kpis": kpis, "contract": contract,
        "weighted_utility": weighted_utility(kpis, weights),
        "fairness_satisfaction": jain_fairness([k.get("demand_satisfaction") for k in kpis.values()]),
        "controller_history": controller.history,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{run_id}.json").write_text(json.dumps(result, indent=2, default=str))
    if not df.empty:
        df.to_csv(OUT_DIR / f"{run_id}.csv", index=False)
    return result


def main():
    parser = argparse.ArgumentParser(description="CARS-SF slicing on Open5GS + UERANSIM")
    parser.add_argument("--scenario", default="disaster")
    parser.add_argument("--duration", type=int, default=40)
    parser.add_argument("--capacity", type=float, default=20.0, help="UPF bottleneck (Mbps)")
    parser.add_argument("--mode", choices=["cars_sf", "no_slicing", "both"], default="both")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0])
    args = parser.parse_args()
    modes = [True, False] if args.mode == "both" else [args.mode == "cars_sf"]
    for seed in args.seeds:
        for enforce in modes:
            r = run_mode(args.scenario, args.duration, args.capacity, enforce, seed)
            print(f"{r['run_id']}: records {r['records']} utility {r['weighted_utility']} fairness {r['fairness_satisfaction']}")
            for s, k in r["slice_kpis"].items():
                print(f"  {s:12s} p95 {k['latency_p95_ms']} ms  loss {k['loss_pct']}%  "
                      f"satisfaction {k['demand_satisfaction']}  SLA {k['sla_satisfied_share']}")


if __name__ == "__main__":
    main()
