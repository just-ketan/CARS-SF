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
