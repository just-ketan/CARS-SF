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


if __name__ == "__main__":
    test_monitor_detects_latency_violation()
    test_failure_detector_congestion()
    test_failure_detector_fiber_cut()
    test_recovery_planner_disaster()
    print("All monitoring/self-healing tests passed.")
