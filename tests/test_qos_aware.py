"""Module B: direction-aware, QoS-targeted allocation with a loss-driven headroom loop."""

from core.controller import SliceController
from slicing.allocators import QoSAwareAllocator
from slicing.directions import split_demand, uplink_share
from slicing.qos_enforcer import QoSEnforcer
from tests.test_qos import KernelNet

DISASTER = {"healthcare": 90.0, "education": 5.0, "agriculture": 5.0, "general": 20.0}
PRIO = {"healthcare": 10, "education": 1, "agriculture": 1, "general": 1}


def test_direction_split_follows_application_registry():
    share = uplink_share()
    assert share["healthcare"] == 1.0 and share["general"] == 0.0
    split = split_demand(DISASTER)
    assert split["uplink"]["healthcare"] == 90.0 and split["downlink"]["general"] == 20.0


def test_demands_first_then_headroom_never_displaces_demand():
    alloc = QoSAwareAllocator().allocate(100, PRIO, {"healthcare": 90, "education": 0, "agriculture": 5, "general": 0})
    assert alloc["agriculture"] >= 5.0              # fits: must get its demand
    assert 90.0 < alloc["healthcare"] <= 99.0        # burst headroom from the spare
    assert abs(sum(alloc.values()) - 100.0) < 0.05


def test_infeasible_demand_degrades_in_explicit_priority_order():
    allocator = QoSAwareAllocator()
    alloc = allocator.allocate(100, PRIO, {"healthcare": 95, "education": 0, "agriculture": 8, "general": 3})
    assert not allocator.feasible
    assert alloc["healthcare"] >= 95.0
    assert allocator.degraded == ["agriculture", "general"]
    assert all(alloc[s] >= 0.5 for s in alloc)        # floors are kept


def test_directional_controller_allocates_each_direction_against_capacity():
    controller = SliceController("qos_aware", capacity=100.0)
    controller.start("disaster", DISASTER)
    up, down = controller.directional_allocation["uplink"], controller.directional_allocation["downlink"]
    assert up["healthcare"] >= 90.0                   # fits the uplink although total demand is 120
    assert down["general"] >= 20.0 and down["healthcare"] <= 1.0
    assert abs(sum(up.values()) - 100) < 0.1 and abs(sum(down.values()) - 100) < 0.1
    assert controller.allocation["healthcare"] == up["healthcare"]


def test_headroom_rises_with_loss_and_relaxes_when_quiet():
    controller = SliceController("qos_aware", capacity=100.0, control_interval_ticks=5)
    controller.start("disaster", DISASTER)
    base = controller.allocator.headroom["healthcare"]
    lossy = {"slice_qos": {"healthcare": {"loss_pct": 4.0}}}
    for _ in range(5):
        controller._observe_qos(lossy)
    assert controller._adapt_headroom() == {"healthcare": round(base * 1.15, 3)}
    quiet = {"slice_qos": {"healthcare": {"loss_pct": 0.0}}}
    for _ in range(controller.QUIET_INTERVALS):
        controller._observe_qos(quiet)
        changes = controller._adapt_headroom()
    assert changes["healthcare"] < base * 1.15


def test_enforcer_applies_directional_rates_and_sla_queue_profile():
    qos = QoSEnforcer(net=KernelNet(), queue_profile="sla")
    qos.setup_htb(100)
    leaf = [c for c in qos.net.get("s_rural").commands if "parent 1:10 handle" in c][0]
    assert "fq_codel target 12ms interval 120ms" in leaf
    directional = {"uplink": {"healthcare": 94, "education": 1, "agriculture": 4, "general": 1},
                   "downlink": {"healthcare": 1, "education": 30, "agriculture": 1, "general": 68}}
    result = qos.apply_allocation({"healthcare": 94, "education": 30, "agriculture": 4, "general": 68},
                                  directional=directional)
    assert result["verified"] is True
    assert qos.net.get("s_rural").classes["1:10"][0] == 94 and qos.net.get("s_edge").classes["1:10"][0] == 1
    assert qos.net.get("s_edge").classes["1:40"][0] == 68


def test_default_profile_and_proposed_scheduler_are_unchanged():
    qos = QoSEnforcer(net=KernelNet())
    qos.setup_htb(100)
    assert any(c.endswith("handle 10: fq_codel") for c in qos.net.get("s_rural").commands)
    assert not SliceController("proposed").directional


def test_directional_estimate_probes_only_elastic_traffic_and_never_overshoots_peak():
    from slicing.demand_estimator import MeasuredDemandEstimator

    est = MeasuredDemandEstimator(prior=DISASTER)
    alloc = {"uplink": {"healthcare": 99.0}, "downlink": {"education": 10.0}}
    sent = 0.0
    for i, rate in enumerate((10, 40, 70, 90, 90, 90)):    # ramp-up then steady UDP uplink video
        sent += rate * 1e6 / 8                              # per-class counters at the bottleneck
        up_stats = {"healthcare": {"sent_bytes": sent, "sent_packets": int(sent / 1200), "dropped": 0,
                                   "backlog_bytes": 50_000}}
        # education: TCP at exactly its 10 Mb/s allocation with a standing queue
        down_stats = {"education": {"sent_bytes": (i + 1) * 1_250_000, "sent_packets": (i + 1) * 1000,
                                    "dropped": 0, "backlog_bytes": 50_000}}
        est.observe({"interval_s": 1.0, "service_throughput_mbps": {"healthcare": rate},
                     "tc_class_stats": up_stats, "tc_downlink_class_stats": down_stats}, {}, alloc)
    up, down = est.estimate_directional()["uplink"], est.estimate_directional()["downlink"]
    assert 70 <= up["healthcare"] <= 90 * 1.05       # interval mean from class counters; no probe-up/overshoot
    assert down["education"] > 10.0                 # TCP at its allocation with a queue: probed up


def test_headroom_goes_first_to_slices_failing_their_sla():
    allocator = QoSAwareAllocator()
    demand = {"healthcare": 90, "education": 0, "agriculture": 5, "general": 0}
    calm = allocator.allocate(100, PRIO, demand)
    allocator.at_risk = {"agriculture"}
    allocator.headroom["agriculture"] = 1.6
    risky = allocator.allocate(100, PRIO, demand)
    assert risky["agriculture"] > calm["agriculture"] and risky["healthcare"] >= 90


def test_overloaded_direction_never_starves_best_effort():
    """Evaluation v1 defect: strict priority on bare demand left general at its 1 Mb/s floor."""
    allocator = QoSAwareAllocator()
    school = {"healthcare": 5, "education": 5, "agriculture": 2, "general": 1}
    alloc = allocator.allocate(50, school, {"healthcare": 0, "education": 80, "agriculture": 0, "general": 50})
    assert alloc["general"] >= 0.2 * 50 and alloc["education"] > alloc["general"]
    assert abs(sum(alloc.values()) - 50) < 0.05 and set(allocator.degraded) == {"education", "general"}


def test_overloaded_direction_still_grants_burst_headroom_by_priority():
    """Evaluation v1 defect: the overload branch ignored headroom, so the loss loop could not act."""
    allocator = QoSAwareAllocator()
    harvest = {"healthcare": 5, "education": 3, "agriculture": 5, "general": 1}
    demand = {"healthcare": 5, "education": 0, "agriculture": 80, "general": 0}
    before = allocator.allocate(50, harvest, demand)["healthcare"]
    allocator.headroom["healthcare"] = 1.6
    after = allocator.allocate(50, harvest, demand)["healthcare"]
    assert before >= 5.5 and after >= 8.0


def test_starved_tcp_slice_keeps_its_guard_from_design_demand():
    """Evaluation v2 defect: a starved TCP slice's measured demand collapses, and a guard
    computed from it collapsed too (general SLA ≈ 0.05 at 50 Mb/s)."""
    controller = SliceController("qos_aware", capacity=50.0)
    school = {"healthcare": 5.0, "education": 80.0, "agriculture": 10.0, "general": 50.0}
    controller.start("school", school)
    collapsed = {"uplink": {"healthcare": 5.0, "education": 0.0, "agriculture": 10.0, "general": 0.0},
                 "downlink": {"healthcare": 0.0, "education": 80.0, "agriculture": 0.0, "general": 1.0}}
    controller.plan("school", school, directional_demands=collapsed)
    assert controller._planned_directional["downlink"]["general"] >= 0.2 * 50.0 - 0.01


def test_uplink_demand_follows_the_class_a_flow_is_queued_in():
    """SliceNet decisions reach demand estimation: per-class bottleneck counters, not host ports."""
    from slicing.demand_estimator import MeasuredDemandEstimator

    est = MeasuredDemandEstimator(prior=DISASTER)
    for i in range(1, 7):
        # host counters say agriculture sends 10 Mb/s, but SliceNet queued that flow as healthcare
        est.observe({"interval_s": 1.0,
                     "service_throughput_mbps": {"agriculture": 10.0},
                     "tc_class_stats": {"healthcare": {"sent_bytes": i * 1.25e6, "sent_packets": i * 1000, "dropped": 0},
                                        "agriculture": {"sent_bytes": 0, "sent_packets": 0, "dropped": 0}}},
                    {}, None)
    up = est.estimate_directional()["uplink"]
    assert up["healthcare"] > 9.0 and up["agriculture"] < 1.0
