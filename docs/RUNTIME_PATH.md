# Runtime Path Audit

This traces the code that actually executes during a live run (`core/orchestrator.py::ExperimentOrchestrator.run`,
one iteration per 1 s tick). Each stage records:

* the implementation and its runtime call site;
* inputs, outputs and failure modes;
* whether its output influences a downstream decision;
* how it is exercised (simulated, mocked, unit-tested or live);
* the evidence for its behaviour.

**Status: as audited on 20 October 2026, before the "close the research objective" changes.** Baseline:
`results/evidence/baseline_v4/BASELINE.json`; code fingerprint `32d91b5d244df3b9`. §3 lists the changes made after
this audit.

## 1. Stages

| # | Stage | Implementation · call site | Inputs → outputs | Failure modes and handling | Influences a decision? | Exercised | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | **Monitor** | `monitoring/monitor.py` `Monitor.check_snapshot`, `SliceMonitor.check` · `orchestrator.py:225–226` | snapshot, design demand → per-slice SLA records, violations | missing telemetry → `loss_ok`/None | **No.** Written to `slice_monitor.csv` and the summary only; no controller, healer or learner reads them. | live | `tests/test_monitoring.py` |
| 2 | **Telemetry** | `telemetry/collector.py` `TelemetryCollector.poll` · `:223` | interface counters, HTB class + leaf qdisc stats (both directions), RTT probes, link watcher → snapshot incl. `slice_qos`, `telemetry_health` | missing interfaces, stale probes, tc/OVS failures → reported in `telemetry_health`; estimator and detector skip unhealthy ticks | Yes: estimator, detector, healer, controller state, reward | live | `tests/test_telemetry_health.py`; integration suite |
| 3 | **Flow classification** | default `classification=host`: static address rules at setup (`qos_enforcer._install_filters`); `slicenet`/`slicenet_all`: `classification/online.py` `OnlineSliceClassifier.step` · `:257` | captures → per-flow `tc flower` rules | abstention → deferral → best-effort fallback; untrained model → `ModelNotTrained` | **Partially.** SliceNet changes which class a flow is queued in. **Uplink demand is still measured per host interface (address-based)**, so a SliceNet decision does not change the measured per-class uplink demand the allocator plans for. The final evaluation's scheduler comparison used address rules; SliceNet appeared only in `qos_slicenet`. | live (`qos_slicenet`, integration) | `tests/test_online_slicenet.py`; `test_slicenet_classifies_every_ue_flow_without_address_rules` |
| 4 | **Context interpretation** | `context/engine.py` `ContextInferenceEngine.step` · `:209`; `forecast` · `:211` | clock, calendar, alerts, admin override → context id; upcoming clock-driven change | unknown context → normal matrix | Yes: priority matrix (`PriorityEngine`) → allocator order under overload; design demand → estimator prior and the guard anchor; healing boosts | live | `tests/test_context*.py` |
| 4b | (dead) `ContextManager.update_from_scenario` | `:219` | scenario state → nothing read | — | **No.** Updated every tick, never read. | — | — |
| 5 | **Demand estimation / prediction** | `slicing/demand_estimator.py` `MeasuredDemandEstimator.observe` (`controller.step`) / `estimate_directional(trend=…)` | per-direction offered load → interval-mean demand (+ ramp extrapolation when predictive) | TCP demand unobservable → probe-up on queue evidence; unhealthy ticks skipped | Yes: allocator input | live; unit | `tests/test_qos_aware.py`, `tests/test_qos_adaptive.py` |
| 6 | **Allocation policy** | `core/controller.py` `SliceController.plan` → `QoSAwareAllocator.allocate` per direction (+ `PriorityEngine`, residual policy) | demands, priorities, constraints → per-direction rates | infeasible → explicit degradation with anti-starvation guard | Yes | live; simulator (RL) | `tests/test_qos_aware.py`, `tests/test_residual_rl.py` |
| 7 | **Safety validation** | **No dedicated validator.** Invariants are spread out: allocator floors and guard; `apply_constraints` (healing); `apply_residual` bounds; the enforcer clamps ceilings. | — | — | **Implicit only.** Nothing checks Σ ≤ C per direction, floors and finite values on the *final* allocation before actuation. | unit (pieces) | — |
| 8 | **Network actuation** | `slicing/qos_enforcer.py` `apply_allocation(…, directional)` · `controller.step` and `orchestrator.py:175` | per-direction rates → `tc class change` on both qdiscs | command failure → `verified=False` → last good allocation kept | Yes | **live (Linux bridges + kernel HTB); real OVS backend never executed in the evaluation** | `tests/test_qos.py`; read-back in every run |
| 9 | **Verification** | enforcer read-back (`_verify`); `SelfHealingEngine.verify` · `:232` | kernel class table; core-service reachability | mismatch → `verified=False`; recovery not verified in 5 ticks → escalation | Yes (keeps the last good allocation; escalates) | live | integration suite |
| 10 | **Learning update** | `scheduler/transitions.py` `TransitionLog` (every scheduler); learner = `OnlineCEMPolicy.learn` / `OnlineResidualCEM.learn` (online schedulers only) | interval reward (`scheduler/reward.py`, from measured outcomes) → per-context Gaussian update | unverified enforcement → not learnable | Only for `rl_online` / `rl_residual_online`. PPO/CEM policies are trained offline in simulators and frozen live. | live (online), simulator (PPO) | `tests/test_transitions.py`, residual-online integration test |
| — | Failure detection / self-healing | `self_healing/detector.py`, `engine.py` · `:228–232`, fast path `:451` | snapshot, link events → actions (backup, fail-back), constraints, boosts | — | Yes: network actions + allocation constraints | live | resilience study; 5 integration tests |

## 2. Gaps found

* **G-A (classification ↔ demand).** SliceNet decisions do not reach the uplink demand estimate (stage 3 vs 5), so
  classification and allocation disagree for any misclassified or address-ambiguous flow.
* **G-B (monitor).** Monitoring output is never consumed by a decision (stage 1).
* **G-C (safety).** No single safety validator on the final allocation before actuation (stage 7).
* **G-D (feasibility).** "Feasible" means Σ mean demand ≤ C. It ignores burst requirements, so a direction is
  declared feasible while a VBR slice cannot meet its loss SLA (e.g. disaster uplink 95 of 100 Mb/s).
* **G-E (prediction).** Only clock-driven contexts and per-tick ramps are forecast. There is no evaluation of
  forecast quality, no gradual-ramp workload and no oracle upper bound; module C showed no benefit.
* **G-F (context).** Context reaches decisions only through the priority order under overload and the design-demand
  prior. No predeclared test of where context *should* help (e.g. at a context switch, before measurements catch up).
* **G-G (RL).** No safe-hybrid controller, no learning-disabled comparison of the online learner, no reward-weight
  sensitivity, no held-out workload.
* **G-H (real OVS).** Real-OVS actuation has never been executed in this environment (BLOCKED for lack of sudo; the
  project's privileged Docker image is available).
* **Dead code.**
  * `self_healing/recovery.py` (`RecoveryPlanner`, tests only).
  * `scheduler/env.py` + `scheduler/baseline.py` (old bandit env and rule scheduler; only `RLAgent.decide` uses
    them, and no runtime path calls it).
  * `ContextManager` updates.
  * `experiments/run_all_contexts.py`, `experiments/run_reproducible.py` (legacy, old allocation engine).
* **Claimed vs actual.**
  * The pipeline is described as Monitor → … → Learning. In the evaluated schedulers, monitoring does not feed
    back, classification is by address, and learning happens only in the two online schedulers.

## 3. Changes after this audit (code frozen for the final evaluation)

| Gap | Change | Where | Tests |
|---|---|---|---|
| G-A classification ↔ demand | Direction-aware schedulers measure uplink offered load from the bottleneck's per-class counters (sent + dropped), as downlink already did. A SliceNet decision now moves the flow's demand to the class it is queued in. | `slicing/demand_estimator.py` | `test_uplink_demand_follows_the_class_a_flow_is_queued_in` |
| G-B monitor | Kept as observability; documented as not a decision stage. The controller reads the same per-slice QoS (`slice_qos`) directly. | — | — |
| G-C safety | `slicing/safety.py`: every plan is validated before actuation (finite, Σ ≤ C per direction, protected minimums). A failing plan is never actuated; the last good allocation stays. Safe RL hybrid acceptance gate. | `slicing/safety.py`, `core/controller.py` | `test_invalid_plan_is_never_actuated`, `test_safe_hybrid_*` |
| G-D feasibility | Explicit regimes per direction (`sla_feasible` / `mean_feasible` / `overload`), with a declared per-context degradation policy (`registries/scenarios.yaml` `degradation`: priority for emergencies and failures, proportional for everyday contexts). An audit (owed / granted / degraded) is recorded per decision. Leftover capacity is split by demand, so context changes do not reconfigure a feasible plan. | `slicing/allocators.py` | `tests/test_objective.py` (regimes, policies, boundary, overload, asymmetry, transitions, misleading/stale estimates, hysteresis) |
| G-E prediction | Load-change workloads (`load_ramp`, `load_surge`, `emergency_ramp`); `qos_reactive` (reaction without prediction); `qos_oracle` (labelled upper bound reading the scripted timeline); forecast-quality evaluator. | `context/engine.py`, `registries/timelines.yaml`, `experiments/forecast_eval.py` | `test_workload_surge_oracle_lookahead_and_context_blind_controller` |
| G-F context | Truly context-blind controller (`qos_blind`: no context changes, priorities or priors). Controllers now receive the context's nominal design demand only, never the workload's actual load scale. | `core/orchestrator.py`, `core/controller.py` | `test_same_observation_different_relevant_context_*`, `test_irrelevant_context_change_*`, `test_context_never_breaks_capacity_or_safety`, live blind test |
| G-G RL | Safe hybrid (`rl_residual_safe`); learning-disabled control (`rl_residual_online_nolearn`); configurable reward weights with sensitivity variants (`sla_x2`, `loss_x4`); training on 4 contexts with `medical_emergency` held out; evaluation under 1.3× load. | `scheduler/agent.py`, `scheduler/reward.py`, `scheduler/env_dir.py` | `tests/test_objective.py` |
| G-H real OVS | Per-direction OVS queues with read-back; runs record the switch type; real-OVS validation driver (privileged project image, real OVS bridges); repeated-fiber-cut fault. | `slicing/qos_enforcer.py`, `experiments/ovs_validation.py`, `self_healing/injector.py` | `test_ovs_backend_applies_per_direction_and_reads_queues_back`, `test_repeated_fiber_cut_injects_and_repairs_twice` |
| Dead code | `ContextManager` updates removed from the run loop. The other dead modules are documented, not deleted. | `core/orchestrator.py` | — |

The final evaluation of these changes is predeclared in `docs/thesis/final_evaluation_plan.md`.
