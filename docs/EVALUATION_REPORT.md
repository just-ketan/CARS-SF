# Experiment and Evaluation Report

The hypothesis under test: for rural network conditions, context-aware slicing with
RL-based adaptation and autonomous self-healing delivers better QoS, utilisation,
continuity and resilience than static or context-unaware slicing.

The pre-declared questions, hypotheses, metrics and statistics are in
[thesis/research_design.md](thesis/research_design.md). Every number below is generated
by `experiments/report.py` into [thesis/results.md](thesis/results.md), which also holds
the full tables. This report summarises those numbers and does not add new ones.

## 1. Setup

* **Testbed.** A three-tier rural network in Mininet:
  * 2 UEs per service (healthcare, education, agriculture, general);
  * a 100 Mb/s full-duplex rural uplink as the single contention point;
  * edge and core clouds;
  * a 20 ms fiber backhaul with a standby 50 Mb/s backup.

  Enforcement is HTB + fq_codel in both directions; the switches are Linux bridges in
  user namespaces.
* **Traffic.** Seeded parametric application models (`registries/applications.yaml`),
  with demand per context from `registries/scenarios.yaml` (80–145 Mb/s offered).
* **Contexts.** normal, school, harvest, disaster, medical_emergency, plus a compressed
  rural-day timeline.
* **Failures.** fiber cut, gradual backhaul degradation, core switch failure.
* **Real 5G core.** Open5GS + UERANSIM, one slice per service, with a 10 Mb/s UPF
  bottleneck.

## 2. Policies compared

All policies use the same scenarios, seeds, offered traffic, capacity and failure
events. They are paired by (scenario, seed).

| Policy | Role in the comparison |
|---|---|
| `no_slicing` | No enforcement (FIFO / fq_codel at the bottleneck) |
| `static_equal` | Static slicing with fixed equal shares |
| `tgpp` | Technology-centric 3GPP slices (URLLC / eMBB / mMTC), static |
| `proportional` | Context priorities, but no demand awareness |
| `context_unaware` | Service-aware demand-aware slicing using the normal-context matrix throughout |
| `proposed` | Context-aware demand-aware heuristic (floors, surplus redistribution, healing constraints) |
| `rl_cem`, `rl_ppo` | Proposed allocator with priorities from simulator-trained CEM / PPO |
| `rl_online` | Online CEM that keeps learning from verified live transitions |
| Healing variants | full, reactive_only (no prediction), no_healing |

## 3. Metrics

* **Weighted utility:** priority-weighted demand satisfaction.
* **Per-slice measures:** demand satisfaction; p95 and p99 one-way delay from
  packet-matched captures; jitter; loss; SLA-met share of flow windows.
* **Fairness:** Jain index.
* **Resilience:** MTTD and MTTR; outage, the longest delivery gap of core-bound flows;
  packets lost during failover; time to verified restore; escalations.
* **Control:** decisions applied and failed enforcement.
* **Learning:** RL transition reward.

Definitions are in research_design.md §Metrics and ARCHITECTURE.md §5.

## 4. Data provenance and splits

* **Synthetic (path A).**
  * `python -m dataset.rsnsd --seed 42`: 108 000 records, 18 scenarios.
  * Byte-reproducible (sha256 `6421db4c…`), contract `rsnsd-contract-2.0`.
  * RSNSD statistical validation 90.77/100.
* **Measured (path B).** 18 collection runs (6 scenarios × seeds 0–2), 4 655
  packet-matched flow windows. All conform to the contract; none were rejected.
* **5G.** 12 runs, stamped `5g_core_measured`.
* **Splits.**
  * Synthetic classifiers hold out whole RSNSD scenarios.
  * Measured classifiers hold out whole run × UE groups; CNN validation groups are
    carved from the training groups.
  * The synthetic→measured transfer study tests only on held-out measured groups.
  * RL uses disjoint training, validation (2000…) and test (1000…) seeds.

## 5. Results

### Supporting the hypothesis

* **Self-healing works and matters (H4a, H4b, H10).**
  * Fiber-cut outage stays at or below 0.17 s.
  * Predictive switchover happened before the cut in 3 of 3 runs, with less outage than
    reactive-only (0.013 s vs 0.054 s).
  * Against no healing, core-bound outage falls by about 10 s (paired p = 0.027 and
    0.039).
  * Recovery verification: 14 recoveries verified, 0 unverified.
* **Slicing protects the critical service.** Healthcare SLA-met share is 0.889 vs 0.786
  without slicing (p = 0.0007, survives Bonferroni).
* **Design elements matter (H2).** Removing surplus redistribution or work-conservation
  costs up to 0.18 utility. Removing context lowers utility slightly in both ablation
  scenarios.
* **Service identification (H5a, H6).**
  * Measured macro F1 is 0.955 (random forest).
  * Synthetic-only models transfer poorly (F1 0.10 zero-shot), and recover with 50 %
    measured groups (0.90).

* **Real 5G core (H8, supported by its directional criterion).** With CARS-SF enforcement
  on the UPF, mean healthcare p95 is 349 ms vs 798 ms without slicing in disaster.
  School shows 4.5 vs 5.4 ms, but that 1 ms difference is within run-to-run variation
  (n = 3): the pre-audit runs had the opposite sign (5.3 vs 4.7). Only the disaster
  effect is substantive.

### Contradicting or qualifying the hypothesis

* **Context awareness per se (H9 not supported).** `proposed` vs `context_unaware`:
  utility +0.002 (p = 0.054), identical healthcare SLA share. At the nominal capacity the
  demand-aware allocator with borrowing makes the priority matrix rarely binding.
* **RL vs heuristic (H3 not supported live).**
  * In simulation, CEM and PPO beat the heuristic by +0.50 % and +0.31 % reward (paired
    p < 0.001), but with slightly more SLA violations.
  * On the network the difference vanishes (p = 0.72 and 0.80).
  * Online CEM ran 10 consecutive live runs with 14–21 verified transitions each and 0
    enforcement failures, but shows no measurable improvement trend at this sample size.
* **Slicing vs no slicing on utility (H1a not supported).** `no_slicing` scores slightly
  higher weighted utility (−0.0037, p = 0.026, not Bonferroni-significant). The benefit
  of slicing is redistribution toward critical services, not more total satisfaction.
* **Robustness (H7 not supported).** Proposed ≥ static in 7 of 12 capacity/load
  settings: it is better in school and equal in disaster.
* **Core switch failure.** Diagnosed and escalated, but not healable: outage is about
  15 s with or without healing.

### Where the approach provides no meaningful improvement

* Disaster context at nominal capacity (all schedulers near utility 0.96).
* Low load (0.5×), where every scheduler satisfies demand.
* Severe overload (1.5× in disaster), where proposed and static are equal.

## 6. Reproducibility

* `run_pipeline.py --mode full` regenerates everything: datasets, models, 375 matrix
  runs, tables, the report. The reference run is
  `results/evidence/pipeline_full_manifest.json`.
* Every run records its code and model fingerprints, and stale runs cannot be reused
  silently.
* RL training is deterministic: a repeated training run gave identical per-seed test
  rewards.

## 7. Limitations

* Emulation, not radio; parametric rather than trace-driven traffic.
* Linux bridges instead of OVS in sudo-free runs.
* Emulated OAM.
* The simulator and the live network differ in reward semantics as listed in
  RL_DESIGN.md.
* Online RL is sample-poor.
* The UERANSIM GTP path limits 5G rates.
