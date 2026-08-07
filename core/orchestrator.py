"""
Unified Mininet experiment orchestrator.

Merges MininetSims + RSNSDv2 into a single pipeline:
topology → traffic → telemetry → features → dataset → validation
"""

from __future__ import annotations

import os
import time
from typing import Any

from mininet.log import setLogLevel, info

from context.engine import ContextManager
from core.config import ensure_output_dirs, GENERATED_DIR
from dataset.builder import DatasetBuilder
from features.extractor import FlowFeatureExtractor
from scenario.engine import ScenarioOrchestrator
from slicing.allocation_engine import AllocationEngine
from slicing.context_engine import ContextEngine
from slicing.qos_enforcer import QoSEnforcer
from telemetry.collector import TelemetryCollector
from topology.rural_topology import RuralNetworkTopology
from traffic.orchestrator import TrafficOrchestrator
from traffic_models.demand_generator import DemandGenerator
from validation.validator import DatasetValidator


class ExperimentOrchestrator:
    """Runs the full CARS-SF Mininet experiment pipeline."""

    def __init__(
        self,
        scenario_id: str = "normal",
        duration: int = 30,
        total_bandwidth: float = 100.0,
        apply_qos: bool = False,
    ):
        self.scenario_id = scenario_id
        self.duration = duration
        self.total_bandwidth = total_bandwidth
        self.apply_qos = apply_qos
        ensure_output_dirs()

    def run(self) -> dict[str, Any]:
        setLogLevel("info")
        info("*** CARS-SF Unified Experiment Pipeline ***\n")

        scenario_orch = ScenarioOrchestrator(self.scenario_id)
        context_mgr = ContextManager()
        scenario = scenario_orch.get_scenario()

        context_engine = ContextEngine()
        allocation_engine = AllocationEngine()
        demand_generator = DemandGenerator()
        qos_enforcer = QoSEnforcer()

        priorities = scenario.get("priority_weights") or context_engine.get_context(self.scenario_id)
        demands = scenario.get("demand_mbps") or demand_generator.get_demands(self.scenario_id)
        allocation = allocation_engine.allocate(
            self.total_bandwidth, priorities, demands
        )

        info(f"*** Scenario: {scenario['name']} ***\n")
        info(f"*** Allocation: {allocation} ***\n")

        topo = RuralNetworkTopology()
        topo.start()

        results: dict[str, Any] = {
            "scenario_id": self.scenario_id,
            "allocation": allocation,
            "priorities": priorities,
            "demands": demands,
        }

        try:
            if self.apply_qos:
                qos_enforcer = QoSEnforcer(net=topo.net)
                qos_enforcer.apply_allocation(allocation)

            traffic = TrafficOrchestrator(topo)
            telemetry = TelemetryCollector(topo.net)
            from monitoring.monitor import Monitor
            from self_healing.detector import FailureDetector
            from self_healing.injector import FaultInjector
            from self_healing.recovery import RecoveryPlanner

            monitor = Monitor()
            failure_detector = FailureDetector()
            fault_injector = FaultInjector(topo.net)
            recovery_planner = RecoveryPlanner(self.total_bandwidth)

            telemetry.start()
            traffic.run_scenario(self.scenario_id, self.duration)

            for tick in range(self.duration):
                scenario_state = scenario_orch.tick_advance()
                context_mgr.update_from_scenario(scenario_state)
                snap = telemetry.poll(tick)

                if scenario_state.get("backhaul_degraded"):
                    fault_injector.evaluate_scenario(scenario_state)

                failures = failure_detector.analyze(snap)
                for failure in failures:
                    plan = recovery_planner.plan_recovery(failure)
                    if self.apply_qos:
                        recovery_planner.execute_recovery(
                            plan, qos_enforcer=qos_enforcer, net=topo.net
                        )

                time.sleep(1)

            traffic.stop_all()
            telemetry.stop()
            fault_injector.cleanup()

            pcap_paths = telemetry.get_pcap_paths()
            scenario_ctx = {
                "network_load_pct": scenario.get("network_load_pct", 50),
                "scenario_id": self.scenario_id,
            }
            feature_extractor = FlowFeatureExtractor(
                pcap_paths=pcap_paths,
                telemetry_snapshots=telemetry.get_snapshots(),
                spawn_metadata=traffic.get_spawn_metadata(),
                scenario_context=scenario_ctx,
            )
            records = feature_extractor.extract()

            if not records:
                info("*** No PCAP flows; using telemetry fallback records ***\n")
                records = feature_extractor._extract_from_telemetry()

            for record in records:
                monitor.check_snapshot(
                    telemetry.get_snapshots()[-1] if telemetry.get_snapshots() else {},
                    [record],
                )

            dataset_builder = DatasetBuilder(
                records,
                scenario_id=self.scenario_id,
                context_name=scenario["name"],
            )
            output_path = dataset_builder.export()
            df = dataset_builder.build()

            validator = DatasetValidator(df)
            validation_report = validator.validate()
            report_path = str(GENERATED_DIR / "datasets" / "validation_report.txt")
            with open(report_path, "w", encoding="utf-8") as handle:
                handle.write(validator.format_report())

            results.update({
                "dataset_path": output_path,
                "validation_report": validation_report,
                "validation_report_path": report_path,
                "record_count": len(records),
                "pcap_paths": pcap_paths,
                "monitoring_summary": monitor.get_summary(),
                "failures_detected": len(failure_detector.get_failures()),
                "recovery_actions": len(recovery_planner.get_recovery_log()),
            })

            info(f"*** Dataset: {output_path} ({len(records)} records) ***\n")
            info(f"*** Validation score: {validation_report['total_score']}/100 ***\n")

        finally:
            topo.stop()

        return results


def run_experiment(
    scenario_id: str = "normal",
    duration: int = 30,
    apply_qos: bool = False,
) -> dict[str, Any]:
    orchestrator = ExperimentOrchestrator(
        scenario_id=scenario_id,
        duration=duration,
        apply_qos=apply_qos,
    )
    return orchestrator.run()
