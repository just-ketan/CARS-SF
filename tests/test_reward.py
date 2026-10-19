"""Reward components and edge cases (scheduler/reward.py)."""

import pytest

from scheduler.reward import SliceOutcome, compute_reward

W = {"healthcare": 5, "education": 5, "agriculture": 2, "general": 1}
SLA = {"healthcare": 50, "education": 150, "agriculture": 250, "general": 500}


def outcome(demand=10, delivered=10, delay=10, loss=0.0, alloc=10, prev=None):
    return SliceOutcome(demand, delivered, delay, loss, alloc, prev)


def all_met(**kw):
    return {s: outcome(**kw) for s in W}


def test_everything_met_scores_100():
    r, info = compute_reward(all_met(), W, SLA, 100)
    assert r == pytest.approx(100.0)
    assert info["sla_violations"] == [] and info["starved"] == []


def test_satisfaction_is_priority_weighted_and_capped():
    out = all_met()
    out["general"] = outcome(demand=10, delivered=0)              # weight 1 of 13 unmet
    r, info = compute_reward(out, W, SLA, 100)
    assert info["terms"]["satisfaction"] == pytest.approx(100 * 12 / 13, abs=1e-3)
    over = all_met(delivered=50)                                   # delivering more than demand is not extra credit
    assert compute_reward(over, W, SLA, 100)[1]["terms"]["satisfaction"] == pytest.approx(100.0)


def test_missing_delay_counts_as_sla_violation():
    out = all_met()
    out["healthcare"] = outcome(delay=None)
    r, info = compute_reward(out, W, SLA, 100)
    assert info["sla_violations"] == ["healthcare"] and info["terms"]["sla"] == -10


def test_zero_demand_is_satisfied_and_never_starved():
    out = all_met()
    out["agriculture"] = outcome(demand=0, delivered=0)
    _, info = compute_reward(out, W, SLA, 100)
    assert info["satisfaction"]["agriculture"] == 1.0 and info["starved"] == []


def test_starvation_penalised_beyond_lost_satisfaction():
    out = all_met()
    out["general"] = outcome(demand=10, delivered=0.5)
    _, info = compute_reward(out, W, SLA, 100)
    assert info["starved"] == ["general"] and info["terms"]["starvation"] == -20


def test_reallocation_penalty_scales_with_capacity_moved():
    still = {s: outcome(alloc=25, prev=25) for s in W}
    moved = {s: outcome(alloc=25 + (10 if i % 2 else -10), prev=25) for i, s in enumerate(W)}
    assert compute_reward(still, W, SLA, 100)[1]["terms"]["reallocation"] == 0
    assert compute_reward(moved, W, SLA, 100)[1]["terms"]["reallocation"] == pytest.approx(-5 * 40 / 100)


def test_idle_capacity_penalised_only_while_demand_unserved():
    satisfied_light = all_met(demand=5, delivered=5)               # 20 of 100 used, all satisfied
    assert compute_reward(satisfied_light, W, SLA, 100)[1]["terms"]["idle"] == 0
    starving_idle = all_met(demand=50, delivered=5)                 # 80 idle while demand unmet
    assert compute_reward(starving_idle, W, SLA, 100)[1]["terms"]["idle"] == pytest.approx(-5 * 0.8)


def test_policy_cannot_inflate_reward_by_reweighting():
    """Weights are the context's; scaling one slice's weight must not change a fully-met score."""
    r_base, _ = compute_reward(all_met(), W, SLA, 100)
    r_skew, _ = compute_reward(all_met(), {**W, "general": 1000}, SLA, 100)
    assert r_base == pytest.approx(r_skew)


def test_loss_penalty_is_mean_percent():
    out = all_met(loss=4.0)
    assert compute_reward(out, W, SLA, 100)[1]["terms"]["loss"] == pytest.approx(-2.0)


def test_live_outcomes_use_counter_deltas_and_flag_missing_probes():
    from scheduler.reward import outcomes_from_snapshot

    def snap(sent, dropped, rtt):
        stats = {"healthcare": {"sent_packets": sent, "dropped": dropped}}
        return {"service_throughput_mbps": {"healthcare": 3.0}, "service_downlink_mbps": {"healthcare": 1.0},
                "service_rtt_ms": {"healthcare": rtt}, "tc_class_stats": stats, "tc_downlink_class_stats": {}}

    out = outcomes_from_snapshot(snap(1100, 20, 40.0), snap(1000, 10, 30.0),
                                 {"healthcare": 5.0}, {"healthcare": 4.0}, {"healthcare": 6.0})
    h = out["healthcare"]
    assert h.delivered_mbps == 4.0 and h.delay_ms == 20.0
    assert abs(h.loss_pct - 100 * 10 / 110) < 1e-9          # Δdropped / (Δsent + Δdropped)
    assert h.previous_allocation_mbps == 4.0
    assert out["education"].delay_ms is None                 # no probe → counted as an SLA violation
    first = outcomes_from_snapshot(snap(10, 0, None), None, {"healthcare": 5.0}, None, {"healthcare": 6.0})
    assert first["healthcare"].previous_allocation_mbps is None and first["healthcare"].delay_ms is None
