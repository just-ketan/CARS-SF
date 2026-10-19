"""Tests for monitoring and self-healing modules."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring.monitor import Monitor
from self_healing.detector import FailureDetector
from self_healing.recovery import RecoveryPlanner


def test_monitor_detects_latency_violation():
    monitor = Monitor()
    flows = [{
        "application_id": "healthcare.telemedicine",
        "service_class": "healthcare",
        "end_to_end_latency_ms": 200,
        "packet_loss_rate": 0,
    }]
    violations = monitor.check_snapshot({"tick": 1}, flows)
    assert len(violations) >= 1
    assert violations[0]["type"] == "latency"


def test_failure_detector_congestion():
    detector = FailureDetector()
    failures = detector.analyze({"tick": 1, "tc_drops": 100, "ovs_bytes": 50000})
    assert any(f["type"] == "congestion" for f in failures)


def test_failure_detector_fiber_cut():
    detector = FailureDetector()
    detector.analyze({"tick": 1, "ovs_bytes": 100000, "tc_drops": 0})
    failures = detector.analyze({"tick": 2, "ovs_bytes": 100, "tc_drops": 0})
    assert any(f["type"] == "fiber_cut" for f in failures)


def test_recovery_planner_disaster():
    planner = RecoveryPlanner()
    plan = planner.plan_recovery({"type": "fiber_cut", "severity": "critical"})
    assert plan["action"] == "reroute_and_protect"
    assert plan["new_allocation"] is not None
    assert plan["new_allocation"]["healthcare"] > plan["new_allocation"]["general"]


def test_detector_uses_link_state_for_fiber_cut():
    detector = FailureDetector()
    failures = detector.analyze({"tick": 3, "backhaul_up": False, "backup_backhaul_up": False})
    assert any(f["type"] == "fiber_cut" for f in failures)


def test_detector_ignores_quiet_sources_when_link_is_up():
    detector = FailureDetector()
    detector.analyze({"tick": 1, "backhaul_up": True, "backhaul_throughput_mbps": 50.0})
    failures = detector.analyze({"tick": 2, "backhaul_up": True, "backhaul_throughput_mbps": 0.0})
    assert not any(f["type"] == "fiber_cut" for f in failures)


def test_detector_latency_spike_names_service():
    detector = FailureDetector()
    failures = detector.analyze({"tick": 1, "service_rtt_ms": {"healthcare": 10.0, "education": 450.0}})
    spikes = [f for f in failures if f["type"] == "latency_spike"]
    assert [f["service_class"] for f in spikes] == ["education"]


def test_recovery_cooldown_and_backup_capacity():
    planner = RecoveryPlanner(total_bandwidth=100, backup_bandwidth=50, context_id="fiber_cut")
    cut = {"type": "fiber_cut", "tick": 5}
    assert planner.should_act(cut)
    plan = planner.plan_recovery(cut)
    assert sum(plan["new_allocation"].values()) <= 50.01
    planner.backup_active = True
    assert not planner.should_act({"type": "fiber_cut", "tick": 20})
    planner.plan_recovery({"type": "congestion", "tick": 6})
    assert not planner.should_act({"type": "congestion", "tick": 7})
    assert planner.should_act({"type": "congestion", "tick": 11})


def test_recovery_boosts_affected_service():
    planner = RecoveryPlanner(context_id="school", demands={
        "healthcare": 5, "education": 80, "agriculture": 10, "general": 50,
    })
    before = planner.allocation_engine.allocate(
        100, planner.context_engine.get_context("school"), planner.demands
    )
    plan = planner.plan_recovery({"type": "latency_spike", "service_class": "general", "tick": 1})
    assert plan["new_allocation"]["general"] > before["general"]


if __name__ == "__main__":
    test_monitor_detects_latency_violation()
    test_failure_detector_congestion()
    test_failure_detector_fiber_cut()
    test_recovery_planner_disaster()
    print("All monitoring/self-healing tests passed.")
