import time
import os
import sys

# Ensure the parent directory is in the path to allow 'RSNSDv2.*' absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mininet.log import setLogLevel, info

from RSNSDv2.simulation.topology import TopologyManager
from RSNSDv2.traffic.orchestrator import TrafficOrchestrator
from RSNSDv2.scenario.engine import ScenarioOrchestrator
from RSNSDv2.context.engine import ContextManager
from RSNSDv2.telemetry.collector import TelemetryCollector
from RSNSDv2.failure_injection.injector import FaultInjector
from RSNSDv2.features.extractor import FeatureExtractor
from RSNSDv2.qos.evaluator import QoSEvaluator
from RSNSDv2.labels.labeler import AutoLabeler
from RSNSDv2.dataset.builder import DatasetBuilder
from RSNSDv2.validation.engine import ValidationEngine
from RSNSDv2.export.exporter import ExportEngine

def run_rsnsd_v3_pipeline():
    setLogLevel("info")
    info("*** Starting RSNSD v3 Digital Twin (Production Pipeline) ***\n")

    info("[Phases 1-6] Initializing Infrastructure & Topology...\n")
    topo_manager = TopologyManager()
    topo_manager.start_network()

    try:
        info("[Phases 8-10] Initializing Registries, Scenario, and Context...\n")
        context_mgr = ContextManager()
        scenario_orch = ScenarioOrchestrator(context_mgr)

        info("[Phase 12] Initializing Telemetry Collectors (OVS, PCAP, TC)...\n")
        telemetry_collector = TelemetryCollector(topo_manager.net)
        telemetry_collector.start_collection()

        info("[Phase 11] Initializing Failure Injection...\n")
        fault_injector = FaultInjector(topo_manager.net)

        info("[Phase 7] Initializing Traffic Engine...\n")
        traffic_orch = TrafficOrchestrator(topo_manager.net)
        
        duration = 10
        info(f"*** Running Live Simulation for {duration} seconds ***\n")
        
        for tick in range(duration):
            scenario_state = scenario_orch.tick()
            context_state = context_mgr.get_snapshot()
            
            traffic_orch.update_demands(scenario_state)
            fault_injector.evaluate_scenario(scenario_state)
            telemetry_collector.poll_sync(tick) # Synchronous polling (Phase 11 Sampling)
            
            time.sleep(1)

        info("*** Stopping Live Simulation ***\n")
        traffic_orch.stop_all()
        telemetry_collector.stop_collection()
        fault_injector.cleanup()

        info("[Phase 14 & 15] Feature Extraction & QoS Derivation...\n")
        raw_telemetry = telemetry_collector.get_data()
        feature_extractor = FeatureExtractor(raw_telemetry)
        flow_features = feature_extractor.extract()
        
        qos_evaluator = QoSEvaluator()
        qos_metrics = qos_evaluator.derive(flow_features)

        info("[Phase 16] Auto Label Generation...\n")
        labeler = AutoLabeler()
        labeled_records = labeler.generate_labels(flow_features, qos_metrics, context_mgr.get_history())

        info("[Phase 17] Dataset Builder (Time Alignment)...\n")
        dataset_builder = DatasetBuilder(labeled_records)
        dataset_df = dataset_builder.build()

        info("[Phase 18] Statistical Validation...\n")
        validator = ValidationEngine()
        is_valid, report = validator.validate(dataset_df)
        info(f"Validation Result: {'PASS' if is_valid else 'FAIL'}\n")

        info("[Phases 19-20] Versioning and Exporting...\n")
        exporter = ExportEngine(output_dir="RSNSDv2/release")
        exporter.export(dataset_df, report)

    finally:
        topo_manager.stop_network()
        info("*** RSNSD v3 Pipeline Shutdown Complete ***\n")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Root privileges required for Mininet. Please run with sudo.")
        sys.exit(1)
    run_rsnsd_v3_pipeline()
