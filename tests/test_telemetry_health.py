"""Telemetry health: stale probes and missing counters are reported, never read as zero."""

import time

from slicing.demand_estimator import MeasuredDemandEstimator
from telemetry.collector import _ProbeWorker


class FakeCollector:
    probe_targets = {"healthcare": ("h", "10.0.2.10"), "general": ("g", "10.0.3.10")}

    def _probe_rtts(self):
        return {"healthcare": 16.0, "general": 56.0}


def test_probe_results_expire_when_stale():
    worker = _ProbeWorker(FakeCollector())
    worker.latest, worker.latest_at = {"healthcare": 16.0, "general": 56.0}, time.time() - 10
    rtts, age = worker.snapshot()
    assert age > 3 and set(rtts.values()) == {None}


def test_estimator_skips_snapshots_without_counters():
    est = MeasuredDemandEstimator(prior={"healthcare": 20, "education": 20, "agriculture": 20, "general": 20})
    good = {"interval_s": 1.0, "service_throughput_mbps": {"healthcare": 5.0}}
    for _ in range(3):
        est.observe(good, {})
    before = est.estimate()["healthcare"]
    broken = {"interval_s": 1.0, "service_throughput_mbps": {"healthcare": 0.0},
              "telemetry_health": {"services_without_counters": ["healthcare"]}}
    assert est.observe(broken, {}) == {}
    assert est.estimate()["healthcare"] == before
