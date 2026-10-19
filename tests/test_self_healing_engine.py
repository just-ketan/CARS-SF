"""Self-healing state machine, loop-free ordering, prediction."""

from self_healing.detector import PredictiveDetector
from self_healing.engine import DEGRADED, NORMAL, ON_BACKUP, SelfHealingEngine


class FakeSwitch:
    def __init__(self, name, log):
        self.name, self.log = name, log

    def cmd(self, command):
        self.log.append((self.name, command))


class FakeTopo:
    def __init__(self):
        self.log = []
        self.s_rural, self.s_edge, self.s_core = (FakeSwitch(n, self.log) for n in ("s_rural", "s_edge", "s_core"))
        self.repaired = False
        self.quality = (20.0, 0.0)
        self.nominal_backhaul_delay_ms = 20

    def primary_link_quality(self):
        return self.quality

    def set_backup_backhaul(self, up):
        self.log.append(("backup", up))

    def set_primary_backhaul(self, up):
        self.log.append(("primary", up))

    def primary_repaired(self):
        return self.repaired


def _link_steps(log):
    return [entry for entry in log if entry[0] in ("backup", "primary")]


def test_failover_quarantines_primary_before_backup_and_fails_back_loop_free():
    topo = FakeTopo()
    engine = SelfHealingEngine(topo)
    engine.handle([{"type": "fiber_cut", "timestamp": 1.0}], tick=5)
    assert engine.state == ON_BACKUP
    assert _link_steps(topo.log) == [("primary", False), ("backup", True)]
    assert engine.constraints()["core_capacity_mbps"] == 50.0

    topo.log.clear()
    topo.repaired = True
    engine.handle([], tick=7)
    assert engine.state == ON_BACKUP            # hold-down not yet elapsed
    engine.handle([], tick=11)
    assert engine.state == NORMAL
    assert _link_steps(topo.log) == [("backup", False), ("primary", True)]


def test_core_unreachable_after_failover_escalates_to_degraded():
    engine = SelfHealingEngine(FakeTopo())
    engine.handle([{"type": "fiber_cut"}], tick=5)
    engine.handle([{"type": "core_unreachable"}], tick=6)
    engine.handle([{"type": "core_unreachable"}], tick=7)
    assert engine.state == DEGRADED
    assert engine.constraints()["core_down"] is True
    engine.handle([], tick=8)
    assert engine.state == ON_BACKUP


def test_reroute_can_be_disabled_for_ablation():
    engine = SelfHealingEngine(FakeTopo(), enable_reroute=False)
    engine.handle([{"type": "fiber_cut"}], tick=3)
    assert engine.state == NORMAL


def test_boosts_expire():
    engine = SelfHealingEngine(FakeTopo())
    engine.handle([{"type": "latency_spike", "service_class": "education"}], tick=1)
    assert engine.constraints()["boosts"] == {"education": 2.0}
    engine.handle([], tick=10)
    assert engine.constraints()["boosts"] == {}


def test_predictive_detector_flags_shared_backhaul_trend_only():
    detector = PredictiveDetector({"education": 300, "general": 300}, window=6, horizon_ticks=5)
    predictions = []
    for t in range(1, 9):
        rtt = {"healthcare": 16.0, "agriculture": 16.0, "education": 56 + 30 * t, "general": 56 + 30 * t}
        predictions += detector.observe({"tick": t, "service_rtt_ms": rtt})
    assert predictions and predictions[0]["type"] == "predicted_backhaul_degradation"

    flat = PredictiveDetector({"education": 300, "general": 300})
    for t in range(1, 9):
        rtt = {"healthcare": 16.0 + 30 * t, "agriculture": 16.0 + 30 * t, "education": 56 + 30 * t, "general": 56 + 30 * t}
        assert not flat.observe({"tick": t, "service_rtt_ms": rtt})


def test_no_fail_back_onto_a_degraded_primary():
    topo = FakeTopo()
    engine = SelfHealingEngine(topo)
    engine.handle([{"type": "predicted_backhaul_degradation"}], tick=5)
    topo.repaired = True               # far end is up: it was never cut ...
    topo.quality = (200.0, 3.0)        # ... but OAM shows it is still degraded
    engine.handle([], tick=20)
    assert engine.state == ON_BACKUP
    topo.quality = (20.0, 0.0)
    engine.handle([], tick=21)
    assert engine.state == NORMAL


def test_own_quarantine_is_not_mistaken_for_a_new_cut():
    import time

    topo = FakeTopo()
    engine = SelfHealingEngine(topo)
    engine.handle([{"type": "predicted_backhaul_degradation"}], tick=5)
    own = engine._own_link_changes[-1]
    engine.state = NORMAL   # pretend we failed back
    engine.handle([{"type": "fiber_cut", "source": "link_watcher", "timestamp": own + 0.05}], tick=6)
    assert engine.state == NORMAL
    engine.handle([{"type": "fiber_cut", "source": "link_watcher", "timestamp": time.time() + 5}], tick=7)
    assert engine.state == ON_BACKUP


def test_predictor_ignores_rtt_rise_caused_by_local_congestion():
    detector = PredictiveDetector({"education": 300, "general": 300}, window=6, horizon_ticks=5)
    predictions = []
    for t in range(1, 10):
        rtt = {"healthcare": 16.0, "agriculture": 16.0, "education": 56 + 40 * t, "general": 56 + 40 * t}
        predictions += detector.observe({"tick": t, "service_rtt_ms": rtt, "tc_drops": 12,
                                         "link_utilization_pct": 99.0})
    assert predictions == []


def test_link_event_fast_path_detects_cut_between_ticks():
    from self_healing.detector import FailureDetector
    from topology.rural_topology import BACKHAUL_INTF

    detector = FailureDetector()
    failures = detector.analyze_link_events([{"intf": BACKHAUL_INTF, "up": False, "timestamp": 1.0}], 4)
    assert [f["type"] for f in failures] == ["fiber_cut"]
    assert detector.analyze_link_events([{"intf": BACKHAUL_INTF, "up": False, "timestamp": 1.1}], 4) == []


def test_failover_is_verified_by_restored_core_reachability():
    engine = SelfHealingEngine(FakeTopo())
    engine.handle([{"type": "fiber_cut", "timestamp": 100.0}], tick=5)
    engine.verify({"service_rtt_ms": {"education": None, "general": None}, "timestamp": 100.2}, 5)
    engine.verify({"service_rtt_ms": {"education": 96.0, "general": 97.0}, "timestamp": 100.4}, 6)
    engine.verify({"service_rtt_ms": {"education": 96.0, "general": 97.0}, "timestamp": 101.4}, 7)
    verified = [a for a in engine.actions if a["action"] == "recovery_verified"]
    assert verified and verified[0]["time_to_restore_s"] == 0.4
    assert engine.verifications[-1]["verified"] is True


def test_unverified_recovery_escalates():
    engine = SelfHealingEngine(FakeTopo())
    engine.handle([{"type": "fiber_cut", "timestamp": 1.0}], tick=5)
    for t in range(5, 12):
        engine.verify({"service_rtt_ms": {"education": None, "general": None}, "timestamp": float(t)}, t)
    assert engine.verifications[-1]["verified"] is False
    assert any("not verified" in e["reason"] for e in engine.escalations)
