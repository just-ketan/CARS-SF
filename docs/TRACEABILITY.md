# Claim Traceability Matrix

Every research claim is linked to its implementation, tests, metric, baseline, final result and evidence. Results
are from the predeclared final evaluation (`docs/thesis/final_evaluation_plan.md`):

* fresh seeds 20–24;
* pipeline manifest `results/pipeline/20261020-122626_full/manifest.json`;
* analysis `results/tables/final_claims.csv`, `final_requirements.csv`.

Differences are paired (condition, seed), shown as mean Δ [95 % CI], with the rank-biserial r. p values are
Holm-adjusted over the primary family.

| Claim | Implementation | Tests | Metric | Baseline | Final result | Verdict | Evidence |
|---|---|---|---|---|---|---|---|
| R1 All four classes meet their SLA where demand fits | `slicing/allocators.py` (`QoSAwareAllocator`, regimes), `core/controller.py` | `tests/test_objective.py::test_feasible_low_and_high_load_meet_every_target` | class SLA share ≥ 0.95, verified-feasible runs | — | 5/5 verified-feasible runs pass (normal); school/harvest not verified feasible | supported (narrow) | `final_requirements.csv`; `final_feasible` runs |
| R2 Safety invariants always hold | `slicing/safety.py`, `slicing/qos_enforcer.py` (read-back) | `test_invalid_plan_is_never_actuated`, `test_context_never_breaks_capacity_or_safety`, `tests/test_qos.py` | failed verifications, planned violations, validator rejections | — | 0 in 540 final runs | supported | `final_requirements.csv` |
| R3 Degradation never starves a class | `QoSAwareAllocator` (guard anchored on design demand), residual protection | `test_sustained_overload_degrades_explicitly_without_starvation`, `test_misleading_low_tcp_estimate_does_not_starve`, `test_residual_cannot_breach_the_starvation_guard` | starvation flag | v1–v3 showed starvation (preserved) | 0 in 240 contended QoS runs | supported | `final_requirements.csv`; `results/evidence/qos_eval_v1..v3` |
| C1 QoS-targeted allocation protects the critical class | `QoSAwareAllocator`, per-direction demand, SLA queue profiles, loss loop | `tests/test_qos_aware.py` | healthcare SLA share | `proposed` | +0.043 [−0.006, 0.093], r 0.37, p 0.58. Emergencies: disaster 0.77→0.92, medical 0.65→0.89, night 0.76→0.93. Harvest@50: 0.71 vs 1.00 under `proposed` (0.94 with v4's priority policy): a regression caused by the new everyday proportional policy | partially supported | `final_summary.csv`; `final_contended_*` runs |
| C2 …without hurting the worst-off class | same | same | worst-class SLA (margin −0.01) | `proposed` | −0.000 [−0.023, 0.022] | unsupported (inconclusive) | `final_claims.csv` |
| C3a Context helps the critical class where informative | `core/controller.py`, `context/engine.py`, `registries/scenarios.yaml` (priorities, degradation policy) | `test_same_observation_different_relevant_context_*`, `test_emergency_transition_switches_policy_and_stays_safe` | healthcare SLA (emergencies, timelines) | `qos_blind` | +0.032 [0.013, 0.050], r 0.80, p 0.023 | supported | `final_claims.csv` |
| C3b Context helps right after changes | same | live blind test | transient SLA | `qos_blind` | −0.001 [−0.023, 0.022] | unsupported | same |
| C4 Context is redundant when demand fits | demand-proportional leftover split | `test_irrelevant_context_change_causes_no_reconfiguration`, `test_clock_change_without_context_change_does_not_replan` | mean class SLA (equivalence ±0.01) | `qos_blind` | +0.001 [−0.002, 0.004] | supported | same |
| C5 Reaction within 1 s helps | `SliceController._sla_risk` | `tests/test_qos_adaptive.py` | transient SLA | `qos_aware` | +0.002 [−0.003, 0.007] | unsupported | `final_prediction` runs |
| C6 Prediction helps beyond reaction | ramp extrapolation, queue prediction, clock pre-provisioning; oracle bound | `tests/test_qos_adaptive.py`, live oracle test | transient and mean class SLA | `qos_reactive`; `qos_oracle` = bound | −0.002 / −0.001, n.s.; the oracle does not beat reaction either | unsupported | `forecast_quality.csv`; `final_prediction` runs |
| C7 Residual RL beats the heuristic | `scheduler/residual.py`, `env_dir.py`, `agent.py` | `tests/test_residual_rl.py` | mean class SLA | `qos_adaptive` | +0.001 [−0.005, 0.006] (simulation +3.2–3.6 %; held-out context −0.1 to −2.2 %) | unsupported live | `rl_training.json`; learning curves `docs/figures/final/` |
| C8 Safe RL hybrid beats the heuristic | `slicing/safety.py::accept_learned`, `rl_residual_safe` | `test_safe_hybrid_*` | mean class SLA | `qos_adaptive` | −0.000 [−0.004, 0.003] | unsupported | `final_claims.csv` |
| C9 Online learning helps | `OnlineResidualCEM` (learning on/off) | `test_learning_disabled_control_explores_but_never_updates`, live residual-online test | mean class SLA | `rl_residual_online_nolearn` | +0.054 [0.043, 0.065], p 0.018. Confound: prior checkpoint; see the post-hoc fresh replication | supported vs exploration control | `final_rl_online*` runs; `posthoc_rl_online_fresh` |
| C10 SliceNet on every flow is non-inferior | `classification/online.py`, class-aware demand | `tests/test_online_slicenet.py`, live slicenet_all test | mean class SLA (margin −0.02) | address rules | −0.004 [−0.014, 0.006] | supported | `final_slicenet` runs |
| C11 Self-healing cuts outage | `self_healing/` | `tests/test_self_healing_engine.py`, 5 live tests | core-bound outage (s) | `no_healing` | −10.0 s [−14.0, −5.9], p 0.010; real OVS: fiber cut 0.15 s, repeated cuts recovered, 0 false failovers | supported | `resilience` + `ovs_resilience` runs |
| Actuation changes real traffic outcomes | `slicing/qos_enforcer.py` (tc on OVS ports; OVS queues with read-back) | `test_ovs_backend_applies_per_direction_and_reads_queues_back` | per-class SLA on real OVS | `no_slicing`, `static_equal` | disaster healthcare 0.50 → 0.74 → 0.86; school worst class 0.65 → 0.93 → 0.98 | supported (real OVS) | `ovs_actuation` runs; `results/evidence/ovs_logs/` |
| Radio-resource slicing; live 5G RAN | not implemented | — | — | — | — | not evaluated | — |
