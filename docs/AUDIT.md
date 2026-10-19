# Implementation Audit and Acceptance Checklist

The audit ran in October 2026 against the research objective: context-aware slicing
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
  codes and durations; code fingerprint `7f21f5629bbdc315`; model fingerprint
  `d7de7d9ea894e82b`.

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

## 2. Requirement status

| Requirement | Status | Source / entry point | Verification | Observed result | Limitations |
|---|---|---|---|---|---|
| Synthetic RSNSD reproducible, schema-valid | **PASS** | `dataset/rsnsd.py`, `features/contract.py` | `python -m dataset.rsnsd --seed 42` twice, different `PYTHONHASHSEED`; `tests/test_contract.py` | 108 000 rows, 18 scenarios, sha256 `6421db4c…` identical across runs; contract ok; RSNSD statistical validation 90.77/100 (PASS) | Classes are imbalanced (healthcare 36 k vs education 17.8 k); handled with class weights, not resampling. Realism of the parametric models is assumed, not validated against rural traces. |
| Mininet produces real traffic and telemetry | **PASS** | `core/orchestrator.py`, `telemetry/collector.py`, `features/` | `experiments/collect_dataset.py --seeds 0 1 2` | 18/18 runs `pcap`, 4 655 packet-matched flow windows, no run rejected | Linux bridges in sudo-free runs; the OVS-specific code needs a root run |
| Both sources conform to one schema with provenance | **PASS** | `features/contract.py` | `validate()` on the RSNSD release, merged Mininet dataset and 12 5G CSVs | All ok; records keep `provenance_source` / `seed` / `config_id`; the transfer study tests only on held-out measured groups | — |
| SliceNet connected to the runtime path, with fallback | **PASS** | `classification/online.py`, `slicenet.py` | `test_mixed_ue_flows_are_classified_in_loop`; slicenet_inloop study | Held-out macro F1: RF 0.955, CNN 0.850 (measured), synthetic 0.946 (scenario hold-out); in-loop mixed-UE SLA share 0.961 vs 0.830 host-based (school), 1.0 vs 1.0 (disaster) | Confidence is not calibrated |
| Context affects decisions testably | **PASS** (mechanism) / effect **not supported** | `core/controller.py`, `slicing/priority_engine.py` | `tests/test_context_decisions.py`; main study | Allocations differ by context; live effect on utility +0.0022 vs `context_unaware` (p = 0.054, n = 25): **H9 not supported** | See §4 |
| Allocations enforced and effects measured | **PASS** | `slicing/qos_enforcer.py` | Read-back in every run | 375 matrix runs: 2 846 applied allocation changes, **0** failed verification | The OVS `linux-htb` backend returns `verified: None` (no read-back) |
| RL loop runs multiple real transitions | **PASS** | `scheduler/transitions.py`, `rl_online` | `test_coupled_rl_loop_on_live_network`; online_rl study | Integration run: 11 transitions, all verified in the kernel, rewards equal to `feedback.csv` means, 2 online updates; 2 932 transitions across the matrix | Online learning is sample-poor (≈ 15–20 transitions per run) |
| Synthetic and Mininet modes semantically compatible | **PARTIAL** | `RL_DESIGN.md` | Same observation, action and reward code in both | Identical layout and reward function | Simulator: one pipe and modelled delay. Live: full duplex and probed RTT/2. |
| RL training: seeds, checkpoints, reload, evaluation | **PASS** | `scheduler/agent.py`, `train.py` | `scheduler/train.py --algo all --seeds 0 1 2`, `--evaluate-only` | Deterministic (re-run gave identical per-seed rewards); deployed model reloaded from disk; paired test-seed comparison | — |
| Self-healing with verified recovery | **PASS** | `self_healing/` | resilience study (27 runs), 5 integration tests | 14 recoveries verified, 0 unverified, 3 escalations (core switch failures, which need repair); fiber-cut outage ≤ 0.17 s; vs no_healing outage −10 s (p ≈ 0.03) | Core-switch failure cannot be healed (outage ≈ 15 s, same as no healing); OAM is emulated |
| Fair baselines executable | **PASS** | `configs/experiments/thesis.yaml` | Main study: 8 schedulers × 5 contexts × 5 seeds, same seeds and traffic | 200/200 runs ok | — |
| Documented pipeline runs from real commands | **PASS** | `run_pipeline.py`, `docs/EXECUTION_GUIDE.md` | `run_pipeline.py --mode full` | Every stage ok (unit 3.6 s … matrix 6 781 s) | Full mode ≈ 2.6 h on this host |
| Automated tests pass | **PASS** | `tests/` | `pytest tests`; `pytest -m integration tests/integration` | 111 unit passed; 8 integration passed (`results/evidence/`) | — |
| Real Open vSwitch run | **BLOCKED** (this session) | `run_experiment.py` | needs `sudo` | Not executed: no root in this session. CI (`.github/workflows/ci.yml`) defines the real-OVS run. | — |
| Real 5G core | **PASS** (deployment) / **PARTIAL** (claim) | `deployment/5g/run_5g.py` | 12 runs, stamped `5g_core_measured` | 12/12 runs contract-valid; healthcare p95 349 vs 798 ms (disaster), 4.5 vs 5.4 ms (school, within noise; sign flipped from the pre-audit runs) | UERANSIM user-space GTP; 10 Mb/s UPF bottleneck |

## 3. End-to-end acceptance checklist

| Critical path | Verified by | Result |
|---|---|---|
| Synthetic generation → contract | `results/evidence/synthetic_path_trace.md` §1 | ✔ identical regeneration, contract ok |
| Synthetic → SliceNet inference with the confidence gate | trace §2 | ✔ |
| Simulator RL: observation → action → priorities → allocation → service → reward terms → next observation | trace §3 | ✔ |
| Mininet traffic → captures → windows → contract | collection stage; `summary.json["contract"]` | ✔ 18/18 |
| Telemetry → state → policy action → allocation → kernel read-back → measured interval → reward → next state | `results/evidence/live_loop_trace__*.md` (integration run, `rl_ppo`, `rl_online`) | ✔ every transition chained; every change verified |
| Live learning from real feedback | online_rl study; `cem_online.json` | ✔ (updates only from verified transitions) |
| Failure injection → detection → recovery → verification / escalation | resilience study; `test_fiber_cut…`, `test_backhaul_degradation…`, `test_core_switch_failure…` | ✔ |
| Results → aggregate → report with verdicts | `docs/thesis/results.md` | ✔ generated from tables; no hand-entered numbers |

## 4. Findings that contradict or qualify the hypothesis

These are reported as measured. None was tuned away.

* **Context awareness (H9).** The context-aware scheduler is not significantly better than
  the identical scheduler without context: weighted utility +0.002, p = 0.054;
  healthcare SLA share identical. The demand-aware allocator with HTB borrowing already
  serves most demand, so the priority matrix rarely binds at 100 Mb/s. Where it does
  bind (school, under capacity or load pressure), the ablation and sensitivity studies
  show gains over static slicing.
* **RL vs heuristic (H3).**
  * Simulation: CEM and PPO beat the rule-based priorities by a small but significant
    margin (+0.50 % and +0.31 % reward, paired p < 0.001), at the cost of slightly more
    SLA violations per episode (37.7 / 39.1 vs 36.4).
  * Live network: no measurable difference (p = 0.72 for PPO, 0.80 for CEM). The live
    trace shows PPO choosing near-identity multipliers.
* **Slicing vs no slicing (H1a).** `no_slicing` has slightly *higher* weighted utility
  (Δ −0.0037, p = 0.026, not Bonferroni-significant). Slicing's benefit is
  distributional: healthcare SLA-met share rises from 0.786 to 0.889 (p = 0.0007,
  Bonferroni-significant).
* **Robustness (H7).** Proposed ≥ static in 7 of 12 capacity/load settings: it is better
  in school, and equal in disaster.
* **5G (H8)** is now marked supported, but only the disaster effect is substantive. The
  school difference (≈ 1 ms, n = 3) changed sign between the pre- and post-audit runs.
* **Self-healing (H10, H4a/b) is supported.** But the core-switch failure is only
  diagnosed and escalated, not healed.

## 5. What remains

* Run `sudo .venv/bin/python run_experiment.py …` once to verify the OVS backend
  (read-back is `None` there by design; flow stats are OVS-only).
* Online RL needs longer live runs before any convergence claim. The current evidence
  shows coupling and bounded adaptation only.
