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


def test_slice_qos_counts_leaf_qdisc_drops_per_interval():
    from telemetry.collector import TelemetryCollector

    collector = TelemetryCollector.__new__(TelemetryCollector)
    collector.class_ids = {"healthcare": "1:10"}
    collector.snapshots = [{
        "tc_class_stats": {"healthcare": {"sent_packets": 1000, "dropped": 10, "sent_bytes": 1_000_000}},
        "tc_downlink_class_stats": {},
    }]
    up = {"healthcare": {"sent_packets": 1900, "dropped": 110, "sent_bytes": 2_250_000,
                         "backlog_bytes": 12_500, "leaf_backlog_bytes": 12_500}}
    qos = collector._slice_qos(up, {}, {"healthcare": 9.0}, {"healthcare": 1.0}, 1.0)["healthcare"]
    assert qos["drops"] == 100 and qos["loss_pct"] == 10.0            # 100 / (900 + 100)
    assert qos["queue_delay_ms"] == 10.0                              # 100 kbit backlog at 10 Mb/s
    assert qos["delivered_mbps"] == 10.0
