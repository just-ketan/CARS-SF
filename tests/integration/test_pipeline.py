"""End-to-end regression on an emulated network (`pytest -m integration`)."""

import pytest

from tests.integration.harness import run_in_namespace, userns_available

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not userns_available(), reason="unprivileged user namespaces unavailable"),
]


def test_normal_pipeline_produces_validated_pcap_dataset():
    result = run_in_namespace("normal", 12, apply_qos=True)
    assert result["data_source"] == "pcap"
    assert result["record_count"] > 0
    assert set(result["slicenet"]) >= {"available"}
    assert result["fault_injected_at_tick"] is None
    assert "fiber_cut" not in result["failure_types"]


def test_fiber_cut_is_detected_and_healed_with_backup():
    result = run_in_namespace("fiber_cut", 15, apply_qos=True)
    assert result["fault_injected_at_tick"] is not None
    assert "fiber_cut" in result["failure_types"]
    assert result["backup_backhaul_activated"] is True
    assert any(a["action"] == "activate_backup" for a in result["recovery_actions"])


def test_timeline_switches_context_and_traffic():
    result = run_in_namespace("normal", 30, apply_qos=True, timeline="rural_day")
    contexts = [c["context"] for c in result["context_history"]]
    assert "school" in contexts and "disaster" in contexts
    assert any(h["reason"].startswith("context") for h in result["controller_history"])


def test_backhaul_degradation_triggers_proactive_switchover():
    result = run_in_namespace("backhaul_degradation", 40, apply_qos=True)
    assert result["predictions"] > 0
    assert result["resilience"].get("proactive") is True
    assert result["resilience"].get("switched_before_cut") is True


def test_core_switch_failure_is_localised():
    result = run_in_namespace("core_switch_failure", 30, apply_qos=True)
    assert result["resilience"]["diagnosed_core_switch_failure"] is True
    assert any(a["action"] == "fail_back" for a in result["healing_actions"])


def test_baseline_schedulers_run_end_to_end():
    for scheduler in ("tgpp", "no_slicing"):
        result = run_in_namespace("school", 12, apply_qos=True, scheduler=scheduler)
        assert result["data_source"] == "pcap" and result["record_count"] > 0


def test_mixed_ue_flows_are_classified_in_loop():
    import os
    from classification.slicenet import CNN_MODEL_PATH, MODEL_DIR

    if not (os.path.exists(CNN_MODEL_PATH) or os.path.exists(MODEL_DIR / "slicenet_mininet.pkl")):
        pytest.skip("SliceNet Mininet model not trained yet")
    result = run_in_namespace("normal", 20, apply_qos=True, classification="slicenet", mixed_ue=True)
    online = result["online_classification"]
    assert online["enabled"] and online["flows_classified"] > 0


def test_coupled_rl_loop_on_live_network(tmp_path, monkeypatch):
    """Observe → State → Decide → Enforce → Measure → Reward → next State, on real tc/telemetry.

    The online-CEM policy samples a fresh action every control interval, so every
    decision changes the kernel HTB configuration; enforcement is verified by
    reading the classes back, the reward is recomputed from the per-tick feedback
    log, and the policy update is driven only by these live transitions.
    """
    import csv
    import json
    import math

    monkeypatch.setenv("CARS_SF_CEM_ONLINE_PATH", str(tmp_path / "cem_online.json"))
    result = run_in_namespace("school", 32, apply_qos=True, scheduler="rl_online", control_interval=4,
                              run_id="it_coupled_rl_loop")
    run_dir = result["run_dir"]
    records = [json.loads(line) for line in open(f"{run_dir}/rl_transitions.jsonl")]
    with open(f"{run_dir}/feedback.csv") as handle:
        rewards = {int(r["tick"]): float(r["reward"]) for r in csv.DictReader(handle)}

    # 1. initial observation, 8. several consecutive iterations
    assert records[0]["tick"] == 0 and len(records) >= 5
    for record, following in zip(records, records[1:]):
        # 7. the next decision starts from the observation this transition ended in
        assert record["next_obs"] == following["obs"] and record["next_tick"] == following["tick"]
        # 6. reward = mean of the per-tick shared rewards measured during the interval
        interval = [rewards[t] for t in range(record["tick"] + 1, record["next_tick"] + 1)]
        assert math.isclose(record["reward"], sum(interval) / len(interval), abs_tol=1e-3)
    # 2. valid actions in the simulator's action space
    assert all(-1.0 <= a <= 1.0 for r in records for a in r["action"])
    # 3–4. actions reached the kernel and were read back (verified True, not "unverifiable")
    changed = [r for r in records if r["allocation_changed"]]
    assert len(changed) >= 3 and all(r["enforcement_verified"] is True for r in changed)
    history = {h["tick"]: h for h in result["controller_history"]}
    for r in changed[1:]:
        assert history[r["tick"]]["enforcement"]["mismatches"] == []
    # 5. fresh telemetry between decisions: observations move, rewards come from measured ticks
    assert len({tuple(r["obs"]) for r in records}) > 1
    assert all(r["reward_ticks"] >= 1 for r in records)
    # learning used exactly the learnable live transitions and updated the policy
    learning = result["policy_learning"]
    assert learning["samples_this_run"] == sum(r["learnable"] for r in records)
    assert learning["updates_this_run"] >= 1
    assert (tmp_path / "cem_online.json").exists()


def test_qos_aware_allocates_per_direction_and_verifies_both():
    """Module B on the live network: per-direction rates read back from both qdiscs,
    feasibility and headroom recorded, per-slice loss visible in the feedback log."""
    import csv

    result = run_in_namespace("disaster", 25, apply_qos=True, scheduler="qos_aware", run_id="it_qos_aware")
    assert result["data_source"] == "pcap" and result["enforcement_summary"]["failed"] == 0
    history = result["controller_history"]
    first = history[0]
    assert first["directional_allocation"]["uplink"]["healthcare"] >= 85
    assert first["directional_allocation"]["downlink"]["healthcare"] <= 1.0
    assert all("feasibility" in h and "headroom" in h for h in history)
    applied = [h for h in history if h.get("enforcement")]
    assert applied and all(h["enforcement"]["verified"] is True for h in applied)
    with open(f"{result['run_dir']}/feedback.csv") as handle:
        rows = list(csv.DictReader(handle))
    assert any(float(r["healthcare_loss_pct"] or 0) >= 0 for r in rows)
    assert {"healthcare_queue_delay_ms", "reward_sla"} <= set(rows[0])


def test_qos_adaptive_preprovisions_before_clock_driven_context_change():
    """Module C on the live network: the school bell (08:00, tick 3 of school_week) is
    forecast from the clock and capacity is reserved before the traffic switches."""
    result = run_in_namespace("normal", 15, apply_qos=True, scheduler="qos_adaptive",
                              timeline="school_week", run_id="it_qos_adaptive")
    reactions = result["controller_reactions"]
    pre = [r for r in reactions if r["reason"].startswith("pre-provision school")]
    switch = [c["tick"] for c in result["context_history"] if c["context"] == "school"][0]
    assert pre and pre[0]["tick"] < switch
    assert result["enforcement_summary"]["failed"] == 0


def test_residual_online_rl_closed_loop_on_live_network(tmp_path, monkeypatch):
    """Module D on the live network: state v2 from measured per-slice QoS, residual actions
    on the QoS-aware allocation, kernel-verified enforcement, learning from those transitions."""
    import json

    monkeypatch.setenv("CARS_SF_CEM_ONLINE_PATH", str(tmp_path / "residual_online.json"))
    result = run_in_namespace("disaster", 30, apply_qos=True, scheduler="rl_residual_online",
                              control_interval=3, run_id="it_residual_online")
    records = [json.loads(line) for line in open(f"{result['run_dir']}/rl_transitions.jsonl")]
    assert len(records) >= 5
    from scheduler.residual import OBS_DIM
    assert all(len(r["obs"]) == OBS_DIM and len(r["action"]) == 4 for r in records)
    assert any(any(abs(a) > 1e-3 for a in r["action"]) for r in records)          # exploring, not a=0
    for record, following in zip(records, records[1:]):
        assert record["next_obs"] == following["obs"]
    changed = [r for r in records if r["allocation_changed"]]
    assert changed and all(r["enforcement_verified"] is True for r in changed)
    k = OBS_DIM - 17                                                # number of contexts
    assert max(max(r["obs"][k + 8:k + 16]) for r in records) > 0   # measured loss / delay reach the state
    learning = result["policy_learning"]
    assert learning["samples_this_run"] == sum(r["learnable"] for r in records) and learning["updates_this_run"] >= 1


def test_slicenet_classifies_every_ue_flow_without_address_rules():
    """Module E on the live network: no address rules; every UE flow is decided by SliceNet
    from ~1 s of packets, and confirmed later disagreements replace the rule."""
    import os
    from classification.slicenet import MODEL_DIR

    if not os.path.exists(MODEL_DIR / "slicenet_mininet.pkl"):
        pytest.skip("SliceNet Mininet model not trained yet")
    result = run_in_namespace("school", 25, apply_qos=True, scheduler="qos_adaptive",
                              classification="slicenet_all", run_id="it_slicenet_all")
    online = result["online_classification"]
    assert online["enabled"] and online["mode"] == "slicenet_all"
    assert online["flows_classified"] >= 16                       # flows of all 8 single-service UEs
    assert online["median_time_to_decision_s"] < 3.0
    assert online["final_accuracy"] is not None and online["final_accuracy"] >= 0.6
    assert result["enforcement_summary"]["failed"] == 0


def test_workload_surge_oracle_lookahead_and_context_blind_controller():
    """Load events re-spawn traffic; only the labelled oracle sees them coming; a context-blind
    controller never re-plans on a context change."""
    oracle = run_in_namespace("normal", 20, apply_qos=True, scheduler="qos_oracle", timeline="load_surge",
                              run_id="it_oracle_surge")
    assert oracle["load_scale"] == 0.6 and oracle["switch"] == "LinuxBridge"
    pre = [r for r in oracle["controller_reactions"] if r["reason"].startswith("pre-provision")]
    assert pre and pre[0]["tick"] < 14                          # surge scripted at tick 14
    blind = run_in_namespace("normal", 30, apply_qos=True, scheduler="qos_blind", timeline="rural_day",
                             run_id="it_blind_rural_day")
    assert not any(h["reason"].startswith("context") for h in blind["controller_history"])
    assert {c["context"] for c in blind["context_history"]} >= {"school", "disaster"}
