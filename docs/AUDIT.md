# Implementation Audit and Acceptance Checklist

The audit ran in October 2026 and was extended (modules A–F) on 19–20 October 2026 against the research objective: context-aware slicing
with RL-based adaptation and self-healing, compared with static and context-unaware
slicing in rural conditions.

Statuses:

* **PASS**: connected to the execution pipeline and verified by a test or a
  reproducible experiment whose result was observed.
* **PARTIAL**: works, with a stated limitation.
* **FAIL**: the requirement is not met.
* **BLOCKED**: could not be verified in this environment.

The existence of a class or file was never accepted as evidence.

* **Environment.** Linux 7.0, Python 3.12 venv, Mininet 2.3. Emulated-network runs are
  sudo-free (user + network namespaces, Linux bridges). Docker hosts Open5GS 2.7.2 +
  UERANSIM 3.2.6.
* **Reference execution.** `run_pipeline.py --mode full` finished with every stage ok.
  The manifest is `results/evidence/pipeline_full_manifest.json`: stage commands, exit
  codes and durations; code fingerprint `32d91b5d244df3b9`; model fingerprint
  `17c8208f5188afaf`. 665 runs, all current.

## 1. Gap analysis: defects found and fixed

| # | Defect found | Fix | Regression test |
|---|---|---|---|
| G1 | The live per-tick reward used an older reward function than the simulator. Reward and transition semantics diverged between modes. | `scheduler/reward.py` is the single reward (satisfaction, SLA, loss, starvation, reallocation, idle). `outcomes_from_snapshot` maps live telemetry onto it. | `tests/test_reward.py` (10) |
| G1b | **Credit-assignment bug.** The reward measured at tick t was logged after the controller decided at t, so it was credited to the new action. It also used the new context's demand and weights at a context switch. | The interval reward is computed with the allocation, demand and context in force during the interval, and credited before the next decision (`core/orchestrator.py`). | `tests/test_transitions.py`; integration test recomputes rewards from `feedback.csv` |
| G2 | **RL not coupled to the live network.** Policies were queried live but no (s, a, r, s′) existed. Nothing learned from Mininet. CEM was trained on a different environment and reward than PPO. | `scheduler/transitions.py` logs every live decision (`rl_transitions.jsonl`). `rl_online` (online CEM) learns from verified live transitions with a checkpoint. CEM is retrained on `SequentialSlicingEnv` with the shared reward. PPO has 3 seeds, learning curves, checkpoints, and validation/test seed separation. | `tests/test_transitions.py` (4); `test_coupled_rl_loop_on_live_network` |
| G3 | Allocations were "applied" without checking the kernel. Failed `tc` commands went unnoticed. | `QoSEnforcer.apply_allocation` parses exit codes and reads the HTB classes back (`verified` True / False / None). On failure the controller keeps the last good allocation and counts it. | `tests/test_qos.py` |
| G4 | **No shared data contract; synthetic data not reproducible.** Unseeded module RNG, `uuid4` flow IDs and per-process salted `hash()` ports meant the same seed gave different data. There was no scenario key for leakage-free splits. | `features/contract.py` (`rsnsd-contract-2.0`: provenance, field categories, rejecting validation). `dataset/rsnsd.py` (seeded, manifest, statistical validation). Mininet, merged and 5G datasets are stamped and validated; non-conforming runs are rejected at merge. | `tests/test_contract.py` (13, incl. cross-process byte identity) |
| G5 | **SliceNet oracle leak.** An untrained classifier returned the record's ground-truth label. There was no low-confidence or invalid-input policy. Synthetic splits were random rows. The CNN had no validation set. | `ModelNotTrained` instead of the label. Confidence-gated abstention; online deferral then best-effort fallback. RSNSD-scenario hold-out; CNN validation groups with early stopping; abstention and accepted-accuracy metrics. | `tests/test_contract.py` (3 SliceNet tests) |
| G6 | Stale or dead probe threads produced old RTTs, and missing counters looked like zero traffic. This caused false failure detection and demand collapse. | `telemetry_health` (missing interfaces, stale probes, tc and OVS polling status). The detector and demand estimator skip unhealthy ticks. | `tests/test_telemetry_health.py` |
| G7 | Recovery was declared on action, never verified. | `SelfHealingEngine.verify`: core services must answer for 2 ticks (`recovery_verified`, time to restore), else escalate after 5 ticks; DEGRADED always escalates. | `tests/test_self_healing_engine.py` |
| G8 | With no captured flows, a run silently substituted telemetry-derived records. | It refuses (`RuntimeError`) unless `allow_telemetry_fallback=True`, and then labels the data `telemetry_fallback`. | integration tests assert `data_source == "pcap"` |
| G9 | No service-aware but context-unaware baseline in the main comparison. | `context_unaware` scheduler (registry field `context_aware: false`) added to the main study (25 runs); H9 added. | `tests/test_context_decisions.py` |
| G10 | No single pipeline. Matrix results were reused without any check that code or models had not changed. | `run_pipeline.py` (modes, fail-fast environment check, manifest). Code and model fingerprints per run; stale runs reported and archived/re-run (`--rerun-stale`); aggregator flags stale runs and writes `provenance.json`. | full pipeline run; `run_matrix.py --list` |
| G11 | No proof that the loop runs on the real network over several iterations. | Integration test of the coupled loop on a live emulated network (below). | `test_coupled_rl_loop_on_live_network` |
| G12 | SIGTERM bypassed teardown. A harness timeout killed only `sh`, which could orphan generators and tcpdump. Mid-run errors left traffic, captures and faults running. | SIGTERM → `SystemExit`. The harness signals the whole process group (TERM, then KILL). The orchestrator's `finally` stops traffic, telemetry and faults, then the network. Failed OVS polls and fault reverts are now reported instead of swallowed. | integration suite |
| G13 | `RL_DESIGN.md` described observations and actions that do not exist. | Rewritten to the implemented state, action, reward and timing. | — |
| G14 | **The controller could not see the loss that broke the SLAs.** CoDel drops in the fq_codel leaf qdiscs were never read; HTB class counters read 0 while telemedicine lost 3–6 %. | Leaf-qdisc drops and backlog; per-slice `slice_qos` (loss, queueing delay, delivered) in every snapshot; loss above the SLA is an SLA violation in the shared reward. | `tests/test_telemetry_health.py`, `tests/test_reward.py` |
| G15 | Demand was summed over both directions and compared with one direction's capacity; the same rate was applied to both directions. | Per-direction demand and allocation (`slicing/directions.py`, `QoSAwareAllocator`). | `tests/test_qos_aware.py` |
| G16 | Elastic probe-up applied to UDP and a trend forecaster chasing VBR bursts: demand estimate 228 Mb/s for a 95 Mb/s flow. | Probe-up only for TCP directions with a standing queue; interval-mean demand. | `tests/test_qos_aware.py` |
| G17 | Exposed by G14: the predictive backhaul detector treated any drop, then any single queue spike, as local congestion and muted itself (proactive switchover 1/3, 3/4 runs). | Congestion evidence = sustained core-bound queueing delay. | `tests/test_self_healing_engine.py` (2); 5/5 live runs |
| G18 | Evaluation v1: strict-priority degradation starved best-effort TCP (general SLA 0.0); overload branch ignored burst headroom. | Anti-starvation guard; headroom under overload. | `test_overloaded_direction_*` |
| G19 | Evaluation v2: elastic-demand death spiral defeated the guard (general SLA 0.05). | Guard anchored on the context's design demand. | `test_starved_tcp_slice_keeps_its_guard_from_design_demand` |
| G20 | Evaluation v3: residual RL could override the guard (general SLA 0.04). | Allocator's protected minimum bounds the residual, live and in the simulator. | `test_residual_cannot_breach_the_starvation_guard`, `test_live_residual_respects_allocator_protection` |
| G21 | Raw captures were never deleted: a matrix filled the disk (~79 GB) and crashed. | Captures deleted after extraction (opt-in `keep_pcaps`); pipeline refuses to start with < 20 GB free. | live check; pipeline environment check |
| G22 | The aggregator flagged stale runs but still mixed them into comparisons. | Tables and tests use only current runs; stale runs stay listed in `runs.csv`. | `experiments/aggregate.py` |

## 2. Requirement status

| Requirement | Status | Source / entry point | Verification | Observed result | Limitations |
|---|---|---|---|---|---|
| Synthetic RSNSD reproducible, schema-valid | **PASS** | `dataset/rsnsd.py`, `features/contract.py` | `python -m dataset.rsnsd --seed 42`, repeated in every pipeline run; `tests/test_contract.py` | 108 000 rows, sha256 `6421db4c…` identical in four full pipeline runs; contract ok; statistical validation 90.77/100 | Realism of the parametric models assumed, not validated against rural traces |
| Mininet produces real traffic and telemetry | **PASS** | `core/orchestrator.py`, `telemetry/collector.py`, `features/` | `experiments/collect_dataset.py --seeds 0 1 2` | 18/18 runs `pcap`; 4 662 packet-matched windows | Linux bridges in sudo-free runs |
| Both sources conform to one schema with provenance | **PASS** | `features/contract.py` | `validate()` on RSNSD, merged Mininet and 5G data | All ok; provenance retained; transfer tested on held-out measured groups | — |
| Per-slice QoS visible to the controller | **PASS** | `telemetry/collector.py` (`slice_qos`) | unit tests; module A regression | Emergency loss now measured (≈274 drops/tick in disaster where 0 was reported) | Queueing delay is a 1 s snapshot |
| SliceNet on the runtime path, with fallback | **PASS** | `classification/online.py` | `test_slicenet_classifies_every_ue_flow_without_address_rules`; qos_slicenet study | Every flow classified (median ≈1.5 s; 89 % → 92 % after reclassification); per-class SLA non-inferior to address rules (H14) | Education ↔ general confusion |
| Context affects decisions | **PASS** (mechanism) / effect **not supported** | `core/controller.py` | `tests/test_context_decisions.py`; main study | Allocations differ by context; utility +0.0005 vs context-unaware (p = 0.58) | — |
| Allocations enforced and measured | **PASS** | `slicing/qos_enforcer.py` | read-back in every run | 665 runs: 5 786 allocation changes applied, 0 failed verification | OVS backend: `verified: None` |
| QoS-targeted allocation meets the critical SLA | **PARTIAL** | `slicing/allocators.py` (`QoSAwareAllocator`), `core/controller.py` | contended-regime study v4 (40 pairs) | Healthcare SLA +0.070 vs proposed (p = 0.0002, Bonferroni); worst class +0.054 vs static | Lower-priority slices pay (mean class SLA −0.016, p = 0.005; H11 not supported) |
| Reactive / predictive control | **PASS** (mechanism) / effect **not supported** | `core/controller.py`, `context/engine.py` | unit + integration tests; H13 | Triggers fire (144 times); no measurable gain over B | — |
| RL loop executes real transitions | **PASS** | `scheduler/transitions.py`, `rl_online`, `rl_residual_online` | coupled-loop and residual-online integration tests | 6 618 live transitions across the study; residual online 267 verified, 0 failed | Sample-poor online learning |
| RL improves QoS | **FAIL** (as a claim) | `scheduler/residual.py`, `env_dir.py` | H12; H3 | Simulation +0.3–0.5 %; network = heuristic (p = 0.20); priority PPO marginal (p = 0.011, not Bonferroni, not reproduced) | Sim-to-real gap (per-run loss RMSE ~2 pp) |
| Synthetic and Mininet RL semantics compatible | **PARTIAL** | `scheduler/residual.py` | shared state/action/reward code | Identical layout and reward | Simulator models TCP and bursts approximately |
| Self-healing with verified recovery | **PASS** | `self_healing/` | resilience study; integration tests | 14 verified, 0 unverified; fiber-cut outage ≤ 0.17 s; −10 s outage vs no healing (p = 0.008) | Core-switch failure only escalated |
| Fair baselines | **PASS** | `configs/experiments/thesis.yaml` | 8 schedulers × 5 contexts × 5 seeds; 6 schedulers × 8 contended conditions × 5 seeds | 665/665 runs ok | — |
| Documented pipeline from real commands | **PASS** | `run_pipeline.py`, `docs/EXECUTION_GUIDE.md` | `run_pipeline.py --mode full` | Every stage ok (~6.5 h) | — |
| Automated tests pass | **PASS** | `tests/` | `pytest tests`; `pytest -m integration tests/integration` | 150 unit, 12 integration passed (`results/evidence/`) | — |
| Real Open vSwitch run | **BLOCKED** (this session) | `run_experiment.py` | needs `sudo` | Not executed here; defined in CI | — |
| Real 5G core | **PASS** (deployment) / **PARTIAL** (claim) | `deployment/5g/run_5g.py` | 12 runs | Disaster healthcare p95 349 vs 798 ms; school within noise | UERANSIM; 10 Mb/s |

## 3. End-to-end acceptance checklist

| Critical path | Verified by | Result |
|---|---|---|
| Synthetic generation → contract | `results/evidence/synthetic_path_trace.md` §1 | ✔ |
| Synthetic → SliceNet inference with confidence gate | trace §2 | ✔ |
| Simulator RL: obs → action → allocation → service → reward → next obs | trace §3 | ✔ |
| Mininet traffic → captures → windows → contract | collection stage | ✔ 18/18 |
| Telemetry (incl. per-slice loss) → state → action → per-direction allocation → kernel read-back → measured interval → reward → next state | `results/evidence/live_loop_trace__*.md` (priority, residual, residual-online, QoS-adaptive runs) | ✔ chained, all changes verified |
| Live learning from real feedback | `rl_online`, `rl_residual_online` studies | ✔ (verified transitions only) |
| SliceNet decides every flow on the network | `qos_slicenet`; integration test | ✔ |
| Failure → detection → recovery → verification / escalation | resilience study; integration tests | ✔ |
| Results → aggregate → report with verdicts | `docs/thesis/results.md` (generated; stale runs excluded) | ✔ |

## 4. Findings that contradict or qualify the hypothesis

* **The QoS-targeted control trades.** It protects healthcare (+0.07 SLA share, Bonferroni-significant) and the
  worst-off class on an overloaded uplink. Lower-priority slices pay in the emergencies, so the pre-stated mean-class
  hypothesis (H11) is not supported. This follows the declared priority and was not tuned away.
* **Context awareness per se (H9), prediction (H13) and RL (H12, H3)** show no robust live benefit. The gains came
  from measuring loss and allocating per direction for SLA targets.
* **The contended-regime evaluation needed four rounds** (fresh seeds each time) because each exposed a real defect
  (G18–G20). All rounds are reported.
* **Unchanged from the first audit:**
  * Slicing redistributes toward critical services rather than raising total utility (H1a).
  * Self-healing works (H4, H10).
  * The core-switch failure is only escalated.

## 5. What remains

* Run `sudo .venv/bin/python run_experiment.py …` once to verify the OVS backend.
* Longer live runs are needed before any online-RL convergence claim.
* A per-class SLA-weighted objective, if the operator wants a different trade between priority and fairness, is a
  policy change. It should be decided before, not after, another evaluation.


## 6. "Close the research objective" round (20 October 2026)

* **Runtime-path audit:** `docs/RUNTIME_PATH.md`.
* **Frozen and reproduced baseline:** `results/evidence/baseline_v4/`.
* **Predeclared final evaluation:** `docs/thesis/final_evaluation_plan.md`.
* **Claim traceability:** `docs/TRACEABILITY.md`.

| Gap | Status | Evidence |
|---|---|---|
| G-A SliceNet decisions did not reach uplink demand | **PASS** (fixed) | class-counter uplink demand; `test_uplink_demand_follows_the_class_a_flow_is_queued_in`; C10 non-inferior |
| G-B monitoring fed no decision | documented (observability only) | `RUNTIME_PATH.md` |
| G-C no safety validator before actuation | **PASS** | `slicing/safety.py`; R2: 0 violations in 540 runs |
| G-D feasibility ignored bursts | **PASS** (mechanism) / **PARTIAL** (outcome) | regimes and declared policies; R1 pass; C1 harvest regression |
| G-E prediction untested | **PASS** (evaluated) / benefit **FAIL** | load workloads, oracle bound, forecast quality; C5/C6 unsupported |
| G-F context untested; workload leak to controllers | **PASS** | `qos_blind`; design-demand-only priors; C3a and C4 supported, C3b not |
| G-G RL controls missing | **PASS** (evaluated) / benefit **FAIL** live | safe hybrid, learning-disabled control, reward variants, held-out tests; C7/C8 unsupported; C9 supported vs control |
| G-H real OVS never executed | **PASS** | 33 runs on OVSBridge (`results/tables/runs.csv`, `switch` column); queue read-back; faults; 0 false failovers |
| Prior-checkpoint confound in C9 (found after the run) | reported; post-hoc fresh-checkpoint replication | `configs/experiments/posthoc_rl_online_fresh.yaml` |
| Transient metric missed load changes (analysis) | fixed in analysis only | aggregator reads load events from timelines |

**Remaining.**

* Critical-class protection under the everyday proportional policy (harvest@50 regression). A fix needs a new
  evaluation.
* Prediction and RL show no live benefit.
* Radio-resource slicing and a live 5G RAN are not implemented.
