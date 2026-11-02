#!/usr/bin/env python3
"""
CARS-SF closed loop on a real 5G core (Open5GS + UERANSIM, see docker-compose.yml).

One run executes the whole control loop, without manual intervention, on the live user
plane; the controller, SliceNet, RL and self-healing are the same classes the emulated
testbed uses (stack5g.py adapts them to the containers):

    monitor      per-class counters at both enforcement points, per-slice probes
    classify     SliceNet on the UPF's flow captures (classification=slicenet_all)
    evaluate     QoSViolationMonitor: thresholds per class and scenario, transient vs persistent
    act          rules plan per direction; a persistent violation hands the correction to RL,
                 behind the safety gate; the plan is validated before actuation
    enforce      HTB rates at the cell site (uplink) and the UPF (downlink), read back
    observe      the next measurements score the adaptation and feed the reward
    learn        online update from verified transitions (scheduler=closed_loop)

    docker compose -f deployment/5g/docker-compose.yml up -d
    python deployment/5g/run_5g.py --scenario disaster --scheduler closed_loop --classification slicenet_all

Radio resources are not scheduled: UERANSIM simulates the radio link, so slices are
enforced on the transport path and the UPF.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from analysis.metrics import jain_fairness, slice_kpis, weighted_utility  # noqa: E402
from classification.online import OnlineSliceClassifier  # noqa: E402
from context.engine import ContextInferenceEngine  # noqa: E402
from core.config import GENERATED_DIR, RESULTS_DIR, load_applications, load_scenarios  # noqa: E402
from core.controller import SliceController, scheduler_spec  # noqa: E402
from core.orchestrator import ExperimentOrchestrator  # noqa: E402
from core.provenance import code_fingerprint, model_fingerprint  # noqa: E402
from features.extractor import FlowFeatureExtractor  # noqa: E402
from features.packet_capture import CapturePoint  # noqa: E402
from self_healing.detector import FailureDetector, PredictiveDetector  # noqa: E402
from self_healing.engine import SelfHealingEngine, ceilings_for  # noqa: E402
from stack5g import (BACKUP_SHARE, CORE_DN_IP, EDGE_DN_IP, SERVICES, UE_IP, FaultInjector5G, LinkWatcher5G, Net5G,  # noqa: E402
                     Telemetry5G, Topology5G, Transport5GQoS, ensure_stack)
from traffic.models import mean_rate_mbps, scaled  # noqa: E402

OUT_DIR = RESULTS_DIR / "5g"
WORK_DIR = GENERATED_DIR / "5g_run"
SERVER = {"srv_edge": ("dn", EDGE_DN_IP), "srv_core": ("dn_core", CORE_DN_IP)}
STREAMS_PER_APP, STREAM_PORT_STEP = 2, 1000


class Traffic5G:
    """Application plans for one scenario; ``get_spawn_metadata`` is SliceNet's scoring truth."""

    def __init__(self, scenario: dict, load_scale: float, seed: int):
        apps = load_applications()
        nominal = {s: sum(mean_rate_mbps(a["model"], a.get("params", {})) for a in apps if a["service_class"] == s)
                   for s in SERVICES}
        self.plans = []
        for i, app in enumerate(apps):
            s = app["service_class"]
            server, server_ip = SERVER[app["server"]]
            to_ue = app.get("direction", "up") == "down" and (app["protocol"] == "udp" or app["model"] == "bulk_tcp")
            # As on the emulated testbed (2 UEs per service), each application is two independent
            # streams: a slice's load is multiplexed, not one stream at twice the rate.
            factor = scenario["demand_mbps"][s] * load_scale / nominal[s] / STREAMS_PER_APP
            params, instances = scaled(app["model"], app.get("params", {}), factor)
            for stream in range(STREAMS_PER_APP):
                self.plans.append({
                    "application_id": app["application_id"], "service_class": s, "slice_type": app["slice_type"],
                    "priority": app["priority"], "host": f"ue_{s}", "host_ip": UE_IP[s], "server": server,
                    "server_ip": server_ip, "port": app["port"] + STREAM_PORT_STEP * stream, "protocol": app["protocol"],
                    "direction": app.get("direction", "up"), "model": app["model"], "params": params,
                    "instances": instances, "dscp": app.get("dscp", 0), "sla": app.get("sla", {}),
                    "latency_requirement_ms": app.get("latency_requirement_ms", 100),
                    "seed": seed * 1000 + i * 10 + stream,
                    "sink": f"tg_{s}" if to_ue else server, "sender": server if to_ue else f"tg_{s}",
                    "destination": UE_IP[s] if to_ue else server_ip,
                })

    def get_spawn_metadata(self) -> list[dict]:
        return list(self.plans)

    def start(self, net: Net5G, duration: int):
        receivers: dict[str, dict[str, set]] = {}
        for p in self.plans:
            receivers.setdefault(p["sink"], {"udp": set(), "tcp": set()})[p["protocol"]].add(p["port"])
        for target, ports in receivers.items():
            flags = " ".join(f"--{proto} {','.join(map(str, sorted(ports[proto])))}"
                             for proto in ("udp", "tcp") if ports[proto])
            net.get(target).cmd(f"cd /cars-sf && python -m traffic.sink {flags} > /tmp/sink.log 2>&1 &")
        time.sleep(1)
        for p in self.plans:
            if p["instances"]:
                params = json.dumps(p["params"]).replace('"', '\\"')
                net.get(p["sender"]).cmd(
                    f"cd /cars-sf && python -m traffic.generator --proto {p['protocol']} --dst {p['destination']} "
                    f"--port {p['port']} --model {p['model']} --params \"{params}\" --duration {duration + 15} "
                    f"--dscp {p['dscp']} --seed {p['seed']} --instances {p['instances']} >> /tmp/gen.log 2>&1 &")

    def stop(self, net: Net5G):
        for target in {p["sink"] for p in self.plans} | {p["sender"] for p in self.plans}:
            net.get(target).cmd("pkill -f '[t]raffic.generator'; pkill -f '[t]raffic.sink'")


def run_loop(scenario_id: str, scheduler: str, classification: str, duration: int, capacity: float, seed: int,
             run_prefix: str = "5g", self_healing: bool = True) -> dict:
    ensure_stack()
    scenario = {s["id"]: s for s in load_scenarios()}[scenario_id]
    run_id = f"{run_prefix}__{scenario_id}__{scheduler}__{classification}__s{seed}"
    run_dir = WORK_DIR / run_id
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True)
    os.chmod(run_dir, 0o777)

    net = Net5G()
    topo = Topology5G(net, capacity)
    topo.reset()
    spec = scheduler_spec(scheduler)
    # Scenario demands are defined for a 100 Mb/s link; a smaller testbed link scales them
    # together, so every contention ratio is preserved.
    load_scale = capacity / 100.0
    traffic = Traffic5G(scenario, load_scale, seed)
    design = offered = {s: v * load_scale for s, v in scenario["demand_mbps"].items()}

    qos = Transport5GQoS(net, topo, class_mode=spec["class_mode"], classification=classification,
                         queue_profile=spec.get("queue_profile", "default"))
    qos.setup_htb(capacity, traffic.get_spawn_metadata())
    controller = SliceController(scheduler, capacity, qos=qos, control_interval_ticks=5)
    if controller.policy_fallback:
        raise RuntimeError(f"{scheduler}: trained policy missing (experiments/semantic_study.py --deploy)")
    context_engine = ContextInferenceEngine(fixed_context=scenario_id)
    context = context_engine.step(0)["context"]
    allocation = controller.start(context, design)
    qos.apply_allocation(allocation, directional=controller.directional_allocation)

    probes = {}
    for app in load_applications():
        probes.setdefault(app["service_class"], SERVER[app["server"]][1])
    telemetry = Telemetry5G(net, topo, qos, run_dir, probes)
    telemetry.start()
    injector = FaultInjector5G(net, topo, spec=scenario.get("failure"), duration=duration)
    detector, predictor = FailureDetector(), None
    healer = SelfHealingEngine(topo=topo, backup_capacity_mbps=capacity * BACKUP_SHARE,
                               enable_reroute=self_healing, enable_predictive=self_healing)
    if self_healing:
        slices = {s: float(controller.qos_monitor.thresholds[scenario_id][s]["latency_ms"]) * 2 for s in SERVICES}
        predictor = PredictiveDetector(slices)
    watcher = LinkWatcher5G(telemetry, topo, Node5G("upf_tap"))
    watcher.start()

    classifier = None
    captures = {f"tg_{s}": ("uesimtun0", ip) for s, ip in UE_IP.items()} | {"dn": ("eth0", EDGE_DN_IP)}
    capture_dir = f"/cars-sf/{run_dir.relative_to(REPO_ROOT)}"
    for target, (iface, _) in captures.items():
        net.get(target).cmd(f"tcpdump -i {iface} -s 128 -U -n -w {capture_dir}/{target}.pcap > /dev/null 2>&1 &")
    net.get("dn_core").cmd(f"tcpdump -i any -y LINUX_SLL -s 128 -U -n -w {capture_dir}/dn_core.pcap host {CORE_DN_IP} > /dev/null 2>&1 &")
    if classification == "slicenet_all":
        telemetry.start_flow_capture()
        classifier = OnlineSliceClassifier(telemetry, qos, topo, traffic=traffic, all_ues=True)
        if not classifier.enabled:
            raise RuntimeError("SliceNet model missing: train it first (experiments/collect_5g.py)")
    time.sleep(1)
    traffic.start(net, duration)

    feedback, previous_snap, previous_allocation = [], None, dict(allocation)
    loop_start = time.time()
    try:
        for tick in range(1, duration + 1):
            time.sleep(max(0.0, loop_start + tick - time.time()))
            context_state = context_engine.step(tick)
            state = {"tick": tick, **{k: v for k, v in _scenario_state(scenario).items()}}
            injector.evaluate_scenario(state, max(2, duration // 3))
            snap = telemetry.poll(tick)
            events = detector.analyze(snap)
            if predictor is not None:
                events += predictor.observe(snap)
            healer.handle(events, tick)
            healer.verify(snap, tick)
            feedback.append(ExperimentOrchestrator._feedback_row(
                tick, snap, previous_snap, allocation, previous_allocation, offered,
                controller.priority_engine.context_engine.get_context(context), capacity, context, healer.state))
            feedback[-1]["jitter"] = json.dumps(snap.get("service_jitter_ms"))
            feedback[-1]["violations"] = json.dumps({s: v["status"] for s, v in controller.qos_status.items()})
            controller.observe_reward(feedback[-1]["reward"])
            previous_snap, previous_allocation = snap, dict(allocation)
            if classifier is not None:
                classifier.step(tick)
                confidences = [d["confidence"] for d in classifier.decisions[-20:]]
                if confidences:
                    controller.classifier_confidence = sum(confidences) / len(confidences)
            new_allocation = controller.step(tick, snap, context_state,
                                             constraints=healer.constraints() if self_healing else None,
                                             prior_demand=design)
            if new_allocation is not None:
                allocation = new_allocation
        controller.finish(duration, previous_snap or {}, context, healer.constraints() if self_healing else None)
    finally:
        watcher.stop()
        traffic.stop(net)
        telemetry.stop()
        for target in list(captures) + ["dn_core"]:
            net.get(target).cmd("pkill tcpdump")
        time.sleep(1)

    points = [CapturePoint(str(run_dir / f"{t}.pcap"), ip) for t, (_, ip) in captures.items()]
    points.append(CapturePoint(str(run_dir / "dn_core.pcap"), CORE_DN_IP))
    extractor = FlowFeatureExtractor([p for p in points if os.path.exists(p.path)],
                                     spawn_metadata=traffic.get_spawn_metadata(), ue_ips=set(UE_IP.values()), window_s=5.0)
    df = pd.DataFrame(extractor.extract())
    contract = {"ok": False, "errors": ["no captured flows"]}
    if not df.empty:
        from dataset.builder import DatasetBuilder
        from features.contract import stamp, validate

        df = DatasetBuilder(df.to_dict("records"), scenario_id=scenario_id, context_name=scenario_id).build()
        df["run_id"] = run_id
        df = stamp(df, "5g_core_measured", seed, run_id)
        contract = validate(df, "5g_core_measured", raise_on_error=False).as_dict()
    kpis = slice_kpis(df, offered) if not df.empty else {}
    weights = controller.priority_engine.context_engine.get_context(context)
    actions = [h for h in controller.history if h.get("enforcement")]
    result = {
        "run_id": run_id, "scenario": scenario_id, "scheduler": scheduler, "classification": classification,
        "seed": seed, "duration": duration, "capacity_mbps": capacity, "demand_mbps": offered, "records": len(df),
        "self_healing": self_healing, "contract": contract, "slice_kpis": kpis,
        "weighted_utility": weighted_utility(kpis, weights),
        "fairness_satisfaction": jain_fairness([k.get("demand_satisfaction") for k in kpis.values()]),
        "enforcement": {"decisions_applied": len(actions),
                        "verified": sum(h["enforcement"].get("verified") is True for h in actions),
                        "failed": sum(h["enforcement"].get("verified") is False for h in actions)},
        "safety_rejections": controller.safety_rejections,
        "hybrid": controller.hybrid_stats, "adaptations": controller.adaptations,
        "qos_monitor": controller.qos_monitor.summary(),
        "transitions": controller.transitions.summary(),
        "policy_learning": controller.policy.learning_summary() if hasattr(controller.policy, "learning_summary") else None,
        "slicenet": classifier.summary() if classifier else None,
        "healing": {"actions": healer.actions, "verifications": healer.verifications, "escalations": healer.escalations,
                    "summary": healer.resilience_summary(injector.events)},
        "faults": injector.events, "controller_history": controller.history,
        "code_fingerprint": code_fingerprint(), "model_fingerprint": model_fingerprint(),
        "environment": "Open5GS 2.7 + UERANSIM 3.2 in Docker: real 5G core signalling and GTP-U, simulated radio",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{run_id}.json").write_text(json.dumps(result, indent=2, default=str))
    pd.DataFrame(feedback).to_csv(OUT_DIR / f"{run_id}__feedback.csv", index=False)
    controller.transitions.write(OUT_DIR / f"{run_id}__transitions.jsonl")
    if not df.empty:
        df.to_csv(OUT_DIR / f"{run_id}.csv", index=False)
    net.get("dn").cmd(f"rm -rf {capture_dir}")
    net.close()
    shutil.rmtree(run_dir, ignore_errors=True)
    return result


def _scenario_state(scenario: dict) -> dict:
    return {"backhaul_degraded": False}


def Node5G(service: str):
    from stack5g import Node
    return Node(service)


def main():
    parser = argparse.ArgumentParser(description="CARS-SF closed loop on Open5GS + UERANSIM")
    parser.add_argument("--scenario", default="disaster")
    parser.add_argument("--scheduler", default="closed_loop")
    parser.add_argument("--classification", default="slicenet_all", choices=["host", "slicenet_all"])
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--capacity", type=float, default=100.0,
                        help="rural N3 link (Mb/s, each direction); scenario demands scale with it")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0])
    parser.add_argument("--run-prefix", default="5g")
    parser.add_argument("--no-healing", action="store_true")
    args = parser.parse_args()
    for seed in args.seeds:
        r = run_loop(args.scenario, args.scheduler, args.classification, args.duration, args.capacity, seed,
                     args.run_prefix, not args.no_healing)
        print(f"{r['run_id']}: records {r['records']} utility {r['weighted_utility']} enforcement {r['enforcement']}")
        for s, k in r["slice_kpis"].items():
            print(f"  {s:12s} p95 {k['latency_p95_ms']} ms  loss {k['loss_pct']}%  "
                  f"satisfaction {k['demand_satisfaction']}  SLA {k['sla_satisfied_share']}")
        print("  monitor", {k: v for k, v in r["qos_monitor"].items() if k != "episodes"})
        if r["slicenet"]:
            print("  slicenet", {k: r["slicenet"][k] for k in ("flows_classified", "accuracy", "final_accuracy",
                                                              "median_time_to_decision_s")})


if __name__ == "__main__":
    main()
