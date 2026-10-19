"""
Unified Mininet experiment orchestrator.

    topology → traffic → telemetry ─┬─▶ monitoring / detection ─▶ self-healing ─┐
                                    └─▶ slice controller (context → demand →    │
                                        priorities → allocation → QoS) ◀────────┘
    after the run: endpoint captures → flow-window dataset → validation → KPIs

Every run writes a self-contained artefact directory ``results/runs/<run_id>/``.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import time
from typing import Any

from mininet.log import setLogLevel, info

from analysis.metrics import jain_fairness, outage_metrics, slice_kpis, weighted_utility
from context.engine import ContextInferenceEngine, ContextManager
from core.config import ensure_output_dirs, GENERATED_DIR, RESULTS_DIR, load_scenarios
from core.controller import SliceController, scheduler_spec
from dataset.builder import DatasetBuilder
from features.contract import SCHEMA_VERSION, stamp
from features.contract import validate as validate_contract
from features.extractor import FlowFeatureExtractor
from scenario.engine import ScenarioOrchestrator
from scheduler.env import SERVICE_CLASSES
from slicing.qos_enforcer import QoSEnforcer
from telemetry.collector import TelemetryCollector
from topology.rural_topology import SERVERS, RuralNetworkTopology
from traffic.orchestrator import TrafficOrchestrator
from validation.validator import DatasetValidator

RUNS_DIR = RESULTS_DIR / "runs"


class ExperimentOrchestrator:
    """Runs the full CARS-SF Mininet experiment pipeline."""

    def __init__(
        self,
        scenario_id: str = "normal",
        duration: int = 30,
        total_bandwidth: float = 100.0,
        apply_qos: bool = False,
        scheduler: str = "proposed",
        topology_factory=None,
        seed: int = 0,
        ues_per_service: int = 2,
        window_s: float = 5.0,
        timeline: str | None = None,
        classification: str = "host",
        work_conserving: bool = True,
        demand_mode: str = "measured",
        control_interval: int = 5,
        self_healing: bool = True,
        predictive: bool = True,
        mixed_ue: bool = False,
        qos_backend: str = "tc",
        run_id: str | None = None,
        aqm: bool = True,
        context_aware: bool = True,
        load_scale: float = 1.0,
        allow_telemetry_fallback: bool = False,
    ):
        self.scenario_id = scenario_id
        self.duration = duration
        self.total_bandwidth = total_bandwidth
        self.apply_qos = apply_qos
        self.spec = scheduler_spec(scheduler)
        self.scheduler_name = self.spec["name"]
        self.seed = seed
        self.window_s = window_s
        self.timeline = timeline
        self.classification = classification
        self.work_conserving = work_conserving
        self.demand_mode = demand_mode
        self.control_interval = control_interval
        self.self_healing = self_healing
        self.predictive = predictive
        self.qos_backend = qos_backend
        self.aqm = aqm
        self.context_aware = context_aware
        self.load_scale = load_scale
        self.allow_telemetry_fallback = allow_telemetry_fallback
        self.topology_factory = topology_factory or (
            lambda: RuralNetworkTopology(ues_per_service=ues_per_service, mixed_ue=mixed_ue)
        )
        self.run_id = run_id or f"{timeline or scenario_id}__{self.scheduler_name}__s{seed}"
        self.scenarios = {s["id"]: s for s in load_scenarios()}
        ensure_output_dirs()

    def _demand(self, context: str) -> dict[str, float]:
        demand = self.scenarios.get(context, self.scenarios["normal"])["demand_mbps"]
        return {s: v * self.load_scale for s, v in demand.items()}

    def run(self) -> dict[str, Any]:
        setLogLevel("info")
        info(f"*** CARS-SF run {self.run_id} ***\n")
        from monitoring.monitor import Monitor, SliceMonitor
        from self_healing.detector import FailureDetector, PredictiveDetector
        from self_healing.engine import SelfHealingEngine
        from self_healing.injector import FaultInjector

        context_engine = ContextInferenceEngine(
            timeline=self.timeline, fixed_context=None if self.timeline else self.scenario_id
        )
        first_context = context_engine.step(0)["context"]
        scenario_orch = ScenarioOrchestrator(first_context)
        scenario = scenario_orch.get_scenario()
        context_mgr = ContextManager()

        topo = self.topology_factory()
        capacity = getattr(topo, "BOTTLENECK_BW_MBPS", self.total_bandwidth)
        qos_enforcer = QoSEnforcer(
            net=None, class_mode=self.spec["class_mode"], classification=self.classification,
            work_conserving=self.work_conserving, backend=self.qos_backend, aqm=self.aqm,
        )
        controller = SliceController(
            self.scheduler_name, capacity, qos=qos_enforcer if self.apply_qos else None,
            demand_mode=self.demand_mode, control_interval_ticks=self.control_interval,
            context_aware=self.context_aware,
        )
        allocation = controller.start(first_context, self._demand(first_context))
        info(f"*** Context: {first_context} | scheduler: {self.scheduler_name} | allocation {allocation} ***\n")

        results: dict[str, Any] = {
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "timeline": self.timeline,
            "scheduler": self.scheduler_name,
            "scheduler_spec": self.spec,
            "policy_fallback_to_rule": controller.policy_fallback,
            "seed": self.seed,
            "apply_qos": self.apply_qos,
            "classification": self.classification,
            "work_conserving": self.work_conserving,
            "demand_mode": self.demand_mode,
            "self_healing": self.self_healing,
            "predictive": self.predictive,
            "aqm": self.aqm,
            "context_aware": self.context_aware,
            "load_scale": self.load_scale,
            "capacity_mbps": capacity,
            "allocation": allocation,
            "priorities": controller.history[0]["priorities"],
            "demands": self._demand(first_context),
        }

        traffic = telemetry = injector = None
        try:
            # Inside try so a failure while starting still tears the network
            # down instead of leaving veths/bridges behind (`sudo mn -c`).
            topo.start()
            run_dir = RUNS_DIR / self.run_id
            run_dir.mkdir(parents=True, exist_ok=True)

            traffic = TrafficOrchestrator(
                topo, seed=self.seed, log_dir=GENERATED_DIR / "logs" / self.run_id, load_scale=self.load_scale
            )
            plans = traffic.prepare(first_context, self.duration * 2 + 10)
            if self.apply_qos:
                qos_enforcer.net = topo.net
                qos_enforcer.setup_htb(capacity, spawns=plans)
                initial = qos_enforcer.apply_allocation(allocation)
                controller.history[0]["enforcement"] = {
                    k: initial.get(k) for k in ("verified", "failures", "mismatches")
                }

            telemetry = TelemetryCollector(
                topo.net, topo=topo, pcap_dir=str(GENERATED_DIR / "pcap" / self.run_id)
            )
            telemetry.class_ids = dict(qos_enforcer.class_ids)
            monitor, slice_monitor = Monitor(), SliceMonitor()
            failure_detector = FailureDetector()
            predictor = PredictiveDetector(
                {s: cfg["sla"]["latency_ms"] * 2 for s, cfg in slice_monitor.slices.items()}
            )
            injector = FaultInjector(topo.net, spec=scenario.get("failure"), duration=self.duration)
            healer = SelfHealingEngine(
                topo, backup_capacity_mbps=getattr(topo, "BACKUP_BACKHAUL_BW_MBPS", 50),
                enable_reroute=self.self_healing, enable_predictive=self.predictive,
            )
            online_classifier = None

            if self.classification == "slicenet" and self.apply_qos:
                from classification.online import OnlineSliceClassifier
                online_classifier = OnlineSliceClassifier(telemetry, qos_enforcer, topo, traffic, self.window_s)

            feedback: list[dict[str, Any]] = []
            previous_snap, previous_allocation, interval_context = None, None, None
            telemetry.start()   # captures must be running before the first packet
            traffic.start(plans, first_context)
            loop_start = time.time()

            for tick in range(1, self.duration + 1):
                self._wait_for_tick(loop_start + tick, telemetry, failure_detector, healer, tick)
                context_state = context_engine.step(tick)
                context = context_state["context"]
                if context_state["changed"] and self.timeline:
                    info(f"*** Tick {tick} {context_state['clock']}: context → {context} ({context_state['reason']}) ***\n")
                    traffic.switch_context(context, self.duration - tick + 10)
                scenario_state = scenario_orch.tick_advance()
                context_mgr.update_from_scenario(scenario_state)
                if not self.timeline:
                    injector.evaluate_scenario(scenario_state, max(2, self.duration // 3))

                snap = telemetry.poll(tick)
                true_demand = self._demand(context)
                monitor.check_snapshot(snap)
                slice_monitor.check(snap, true_demand)

                events = failure_detector.analyze(snap)
                if self.predictive:
                    events += predictor.observe(snap)
                healer.handle(events, tick)
                healer.verify(snap, tick)
                for event in events:
                    if event["type"] not in ("latency_spike", "link_saturation", "congestion"):
                        info(f"*** Tick {tick}: {event['type']} ***\n")

                # The snapshot measures the interval that just ended, under the allocation
                # in force during it: its reward belongs to the decision that set that
                # allocation, so it is credited before the controller decides again.
                interval_context = interval_context or context
                feedback.append(self._feedback_row(
                    tick, snap, previous_snap, allocation, previous_allocation, self._demand(interval_context),
                    controller.priority_engine.context_engine.get_context(interval_context),
                    controller.capacity, interval_context, healer.state,
                ))
                controller.observe_reward(feedback[-1]["reward"])
                previous_snap, previous_allocation, interval_context = snap, dict(allocation), context

                new_allocation = controller.step(
                    tick, snap, context_state,
                    constraints=healer.constraints() if self.self_healing else None,
                    prior_demand=true_demand,
                )
                if new_allocation is not None:
                    allocation = new_allocation
                if online_classifier is not None and tick % self.control_interval == 0:
                    online_classifier.step(tick)

            info(f"*** Control loop: {self.duration} ticks in {time.time() - loop_start:.1f}s ***\n")
            controller.finish(self.duration, previous_snap or {}, context,
                              healer.constraints() if self.self_healing else None)
            controller.transitions.write(run_dir / "rl_transitions.jsonl")
            traffic.stop_all()
            telemetry.stop()
            injector.cleanup()

            # ---------------------------------------------------- dataset
            scenario_ctx = {
                "network_load_pct": scenario.get("network_load_pct", 50),
                "scenario_id": self.scenario_id,
            }
            feature_extractor = FlowFeatureExtractor(
                capture_points=telemetry.get_capture_points(),
                telemetry_snapshots=telemetry.get_snapshots(),
                spawn_metadata=traffic.get_spawn_metadata(),
                scenario_context=scenario_ctx,
                ue_ips={h.IP() for h in topo.ue_hosts},
                window_s=self.window_s,
            )
            packets = feature_extractor.matched_packets()
            records = feature_extractor.records_from_packets(packets) if not packets.empty else []
            data_source = "pcap"
            if not records:
                if not self.allow_telemetry_fallback:
                    raise RuntimeError(
                        "no application flows were captured (empty or missing pcaps); "
                        "refusing to substitute telemetry-derived records. Check tcpdump and "
                        "traffic logs, or pass allow_telemetry_fallback=True for a labelled degraded dataset."
                    )
                info("*** No PCAP flows; using telemetry fallback records (labelled degraded) ***\n")
                records = feature_extractor._extract_from_telemetry()
                data_source = "telemetry_fallback"

            last_snapshot = telemetry.get_snapshots()[-1] if telemetry.get_snapshots() else {}
            flow_violations = monitor.check_snapshot(last_snapshot, records)

            dataset_builder = DatasetBuilder(records, scenario_id=self.scenario_id, context_name=scenario["name"])
            df = dataset_builder.build()
            df["run_id"] = self.run_id
            df["scheduler"] = self.scheduler_name
            df = stamp(df, "mininet_measured", self.seed, self.run_id)
            contract_report = validate_contract(df, "mininet_measured", raise_on_error=False)
            if not contract_report.ok:
                info(f"*** Dataset violates {SCHEMA_VERSION}: {contract_report.errors} ***\n")
            output_path = str(run_dir / "dataset.csv")
            df.to_csv(output_path, index=False)
            if feature_extractor.sequences and len(feature_extractor.sequences) == len(df):
                import numpy as np
                np.savez_compressed(
                    run_dir / "sequences.npz",
                    X=np.stack(feature_extractor.sequences),
                    flow_id=df["flow_id"].to_numpy(),
                )

            validator = DatasetValidator(df)
            validation_report = validator.validate()
            report_path = str(run_dir / "validation_report.txt")
            with open(report_path, "w", encoding="utf-8") as handle:
                handle.write(validator.format_report())

            # ---------------------------------------------------- KPIs
            demand_by_design = self._average_demand(context_engine)
            kpis = slice_kpis(df, demand_by_design, self.window_s) if data_source == "pcap" else {}
            weights = controller.priority_engine.context_engine.get_context(first_context)
            resilience = healer.resilience_summary(injector.events)
            failure_event = next((e for e in injector.events if e["event"] in (
                "fiber_cut", "core_switch_failure")), None)
            if failure_event is not None and not packets.empty:
                services_by_ip = {
                    ip: service for service in SERVICE_CLASSES for ip in topo.ue_ips.get(service, [])
                }
                core_ips = {ip for ip, sw, _ in SERVERS.values() if sw == "s_core"}
                resilience["outage"] = outage_metrics(
                    packets, failure_event["timestamp"], services_by_ip, core_ips
                )

            self._write_csv(run_dir / "feedback.csv", feedback)
            self._write_csv(run_dir / "slice_monitor.csv", slice_monitor.records)
            if (run_dir / "feedback.csv").exists():
                shutil.copy(run_dir / "feedback.csv", GENERATED_DIR / "telemetry" / f"feedback_{self.run_id}.csv")

            results.update({
                "run_dir": str(run_dir),
                "ues_per_service": len(topo.ue_hosts) // 4,
                "app_instances": len(traffic.get_spawn_metadata()),
                "final_allocation": allocation,
                "dataset_path": output_path,
                "data_source": data_source,
                "contract": contract_report.as_dict(),
                "rl_transitions": controller.transitions.summary(),
                "policy_learning": controller.policy.learning_summary()
                if hasattr(controller.policy, "learning_summary") else None,
                "record_count": len(records),
                "validation_report": validation_report,
                "validation_report_path": report_path,
                "slice_kpis": kpis,
                "fairness_satisfaction": jain_fairness(
                    [k.get("demand_satisfaction") for k in kpis.values()]
                ),
                "weighted_utility": weighted_utility(kpis, weights),
                "slice_sla_monitor": slice_monitor.summary(),
                "monitoring_summary": monitor.get_summary(),
                "flow_sla_violations": len(flow_violations),
                "failures_detected": len(failure_detector.get_failures()),
                "failure_types": sorted({f["type"] for f in failure_detector.get_failures()}),
                "predictions": len(predictor.predictions),
                "fault_injected_at_tick": injector.injection_tick,
                "injector_events": injector.events,
                "backup_backhaul_activated": any(
                    a["action"].startswith("activate_backup") for a in healer.actions
                ),
                "healing_actions": healer.actions,
                "resilience": resilience,
                "recovery_actions": [
                    {"tick": a["tick"], "failure": a["trigger"], "action": a["action"]}
                    for a in healer.actions
                ],
                "controller_history": controller.history,
                "telemetry_health_summary": {
                    "ticks": len(telemetry.get_snapshots()),
                    "ticks_with_missing_counters": sum(
                        1 for snap in telemetry.get_snapshots()
                        if (snap.get("telemetry_health") or {}).get("missing_interfaces")),
                    "ticks_with_stale_probes": sum(
                        1 for snap in telemetry.get_snapshots()
                        if (snap.get("telemetry_health") or {}).get("probes_stale")),
                    "ticks_tc_unavailable": sum(
                        1 for snap in telemetry.get_snapshots()
                        if (snap.get("telemetry_health") or {}).get("tc_ok") is False),
                },
                "enforcement_summary": {
                    "decisions_applied": sum(1 for h in controller.history if h.get("applied")),
                    "verified": sum(1 for h in controller.history if (h.get("enforcement") or {}).get("verified") is True),
                    "failed": sum(1 for h in controller.history if (h.get("enforcement") or {}).get("verified") is False),
                    "unverifiable": sum(1 for h in controller.history
                                        if h.get("applied") and (h.get("enforcement") or {}).get("verified") is None),
                },
                "context_history": [
                    c for c in context_engine.get_history() if c["changed"]
                ],
                "slicenet": self._classify(df),
                "online_classification": online_classifier.summary() if online_classifier else None,
                "mean_reward": round(sum(r["reward"] for r in feedback) / max(len(feedback), 1), 2),
            })

            info(f"*** Dataset: {output_path} ({len(records)} records, {data_source}) ***\n")
            info(f"*** Validation score: {validation_report['total_score']}/100 ***\n")

            with open(run_dir / "summary.json", "w", encoding="utf-8") as handle:
                json.dump(results, handle, indent=2, default=str)
            results["summary_path"] = str(run_dir / "summary.json")

        finally:
            # Best-effort teardown in dependency order, also after errors and
            # SIGTERM (raised as SystemExit by the entry points): generators and
            # captures first, then injected faults, then the emulated network.
            for name, stop in (("traffic", getattr(traffic, "stop_all", None)),
                               ("telemetry", getattr(telemetry, "stop", None)),
                               ("injector", getattr(injector, "cleanup", None))):
                if stop is not None:
                    try:
                        stop()
                    except Exception as exc:
                        info(f"*** cleanup of {name} failed: {exc} ***\n")
            topo.stop()

        return results

    @staticmethod
    def _wait_for_tick(deadline, telemetry, detector, healer, tick):
        """Sleep until the next tick, but react to link transitions immediately.

        A carrier loss wakes the loop at once (event-driven fast path), so
        failover does not wait for the next 1 s telemetry tick.
        """
        watcher = telemetry.link_watcher
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return
            if watcher is None or not watcher.changed.wait(remaining):
                return
            watcher.changed.clear()
            events = watcher.drain()
            telemetry.link_events.extend(events)
            failures = detector.analyze_link_events(events, tick - 1)
            if failures:
                healer.handle(failures, tick - 1)
                for failure in failures:
                    info(f"*** Fast path: {failure['type']} ***\n")

    def _average_demand(self, context_engine) -> dict[str, float]:
        """Time-averaged demand by design over the run (contexts may change)."""
        history = context_engine.get_history()
        totals = {s: 0.0 for s in SERVICE_CLASSES}
        for entry in history:
            for s, v in self._demand(entry["context"]).items():
                totals[s] += v
        return {s: round(v / max(len(history), 1), 3) for s, v in totals.items()}

    @staticmethod
    def _feedback_row(tick, snap, previous_snap, allocation, previous_allocation, demands, priorities,
                      capacity, context, healing_state) -> dict[str, Any]:
        """Measured QoS + reward for this tick, with the shared reward (scheduler/reward.py)
        that the simulator and the live RL environment also use."""
        from scheduler.reward import compute_reward, outcomes_from_snapshot, sla_delay_targets

        up = snap.get("service_throughput_mbps", {})
        down = snap.get("service_downlink_mbps", {})
        rtt = snap.get("service_rtt_ms", {})
        tput = {s: round(up.get(s, 0.0) + down.get(s, 0.0), 3) for s in SERVICE_CLASSES}
        reward, reward_info = (0.0, {"terms": {}, "sla_violations": [], "starved": []})
        if allocation:
            reward, reward_info = compute_reward(
                outcomes_from_snapshot(snap, previous_snap, allocation, previous_allocation, demands),
                priorities, sla_delay_targets(), capacity,
            )
        row = {
            "tick": tick,
            "timestamp": snap.get("timestamp"),
            "context": context,
            "healing_state": healing_state,
            "reward": round(reward, 4),
            **{f"reward_{k}": v for k, v in reward_info["terms"].items()},
            "sla_violations": len(reward_info["sla_violations"]),
            "starved": len(reward_info["starved"]),
            "link_utilization_pct": snap.get("link_utilization_pct", 0),
            "tc_drops": snap.get("tc_drops", 0),
            "backhaul_up": snap.get("backhaul_up"),
            "backup_backhaul_up": snap.get("backup_backhaul_up"),
        }
        for s in SERVICE_CLASSES:
            row[f"{s}_alloc_mbps"] = allocation.get(s, 0)
            row[f"{s}_demand_mbps"] = demands.get(s, 0)
            row[f"{s}_tput_mbps"] = tput[s]
            row[f"{s}_rtt_ms"] = rtt.get(s)
        return row

    @staticmethod
    def _write_csv(path, rows: list[dict[str, Any]]):
        if not rows:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _classify(df) -> dict[str, Any]:
        """Run the trained SliceNet over the captured flows and score it against ground truth."""
        from classification.slicenet import MODEL_DIR, SliceNetClassifier

        for name in ("slicenet_mininet.pkl", "slicenet_baseline.pkl"):
            model_path = MODEL_DIR / name
            if os.path.exists(model_path) and not df.empty:
                classifier = SliceNetClassifier(model_path=str(model_path))
                predictions = classifier.predict_batch(df)
                truth = df["service_class"].tolist()
                correct = sum(p == t for p, t in zip(predictions, truth))
                return {
                    "available": True,
                    "model": str(model_path),
                    "flows": len(truth),
                    "accuracy": round(correct / len(truth), 4),
                }
        return {"available": False, "reason": "no flows or no trained model"}


def run_experiment(
    scenario_id: str = "normal",
    duration: int = 30,
    apply_qos: bool = False,
    scheduler: str = "proposed",
    **options,
) -> dict[str, Any]:
    orchestrator = ExperimentOrchestrator(
        scenario_id=scenario_id,
        duration=duration,
        apply_qos=apply_qos,
        scheduler=scheduler,
        **options,
    )
    return orchestrator.run()
