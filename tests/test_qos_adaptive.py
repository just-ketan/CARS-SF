"""Module C: reactive re-planning, demand-ramp and queue-growth prediction, pre-provisioning."""

from context.engine import ContextInferenceEngine
from core.controller import SliceController
from slicing.demand_estimator import _ramp_forecast

NORMAL = {"healthcare": 20.0, "education": 20.0, "agriculture": 20.0, "general": 20.0}
SCHOOL = {"healthcare": 5.0, "education": 80.0, "agriculture": 10.0, "general": 50.0}


def _snap(**qos):
    return {"slice_qos": {s: {"loss_pct": v[0], "queue_delay_ms": v[1]} for s, v in qos.items()}}


def test_clock_forecast_sees_school_bell_but_not_future_alerts():
    engine = ContextInferenceEngine(timeline="rural_day")
    for tick in range(11):
        engine.step(tick)
    assert engine.forecast(10, 2) is None          # the flood alert at tick 12 is not predictable
    school = ContextInferenceEngine(timeline="school_week")
    school.step(1)
    assert school.forecast(1, 2) == {"context": "school", "in_ticks": 2, "reason": "school hours"}


def test_ramp_forecast_leads_consistent_rise_only():
    assert _ramp_forecast([10, 20, 30, 40, 50], 2) == 70
    assert _ramp_forecast([50, 48, 52, 49, 51], 2) == 50
    assert _ramp_forecast([10, 11, 12, 13, 100], 2) <= 150      # capped at 1.5 × peak


def test_sla_breach_triggers_replan_next_tick_with_hold_down():
    controller = SliceController("qos_adaptive", capacity=100.0, control_interval_ticks=5)
    controller.start("normal", NORMAL)
    ctx = {"context": "normal"}
    controller.step(1, _snap(healthcare=(0.0, 1.0)), ctx, prior_demand=NORMAL)
    assert len(controller.history) == 1                           # healthy: no decision before the interval
    controller.step(2, _snap(healthcare=(3.0, 1.0)), ctx, prior_demand=NORMAL)
    assert controller.history[-1]["reason"].startswith("sla risk: healthcare loss")
    controller.step(3, _snap(healthcare=(3.0, 1.0)), ctx, prior_demand=NORMAL)
    assert controller.history[-1]["tick"] == 2                    # hold-down: no re-plan one tick later


def test_rising_queue_is_predicted_before_the_breach():
    controller = SliceController("qos_adaptive", capacity=100.0, control_interval_ticks=50)
    controller.start("normal", NORMAL)
    ctx = {"context": "normal"}
    for tick, queue in enumerate((4.0, 9.0, 16.0), start=1):    # limit 25 ms; 16 + 2 × 6 = 28 in two ticks
        controller.step(tick, _snap(healthcare=(0.0, queue)), ctx, prior_demand=NORMAL)
    assert controller.history[-1]["reason"].startswith("sla risk: healthcare queue rising")


def test_preprovisioning_reserves_for_the_upcoming_context():
    controller = SliceController("qos_adaptive", capacity=100.0, control_interval_ticks=50)
    controller.start("normal", NORMAL)
    assert controller._planned_info["downlink"]["regime"] == "sla_feasible"
    ctx = {"context": "normal", "upcoming": {"context": "school", "in_ticks": 2}, "upcoming_demand": SCHOOL}
    controller.step(1, {}, ctx, prior_demand=NORMAL)
    assert controller.history[-1]["reason"] == "pre-provision school in 2 ticks"
    # planned against the school demand (130 Mb/s downlink) under school's declared policy
    assert controller._planned_info["downlink"]["regime"] == "overload"
    assert controller._planned_info["downlink"]["policy"] == "proportional"
    controller.step(2, {}, ctx, prior_demand=NORMAL)
    assert len([h for h in controller.history if h["reason"].startswith("pre-provision")]) == 1


def test_explicitly_degraded_slices_do_not_retrigger():
    controller = SliceController("qos_adaptive", capacity=100.0)
    controller.start("medical_emergency", {"healthcare": 95.0, "education": 5.0, "agriculture": 8.0, "general": 10.0})
    assert "agriculture" in controller._planned_info["uplink"]["degraded"]
    assert controller._sla_risk(_snap(agriculture=(9.0, 1.0))) is None


def test_queue_risk_ignores_elastic_tcp_slices_but_not_their_loss():
    controller = SliceController("qos_adaptive", capacity=100.0)
    controller.start("normal", NORMAL)                       # feasible: no slice is degraded
    assert controller._sla_risk(_snap(education=(0.0, 140.0))) is None
    assert controller._sla_risk(_snap(education=(3.0, 1.0))).startswith("education loss")
