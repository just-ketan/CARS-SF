# Research Design

This document fixes the research questions, hypotheses, method and analysis plan
*before* the evaluation matrix is run. Results are reported against it in
[results.md](results.md), including hypotheses that are not supported.

## Research questions and hypotheses

| # | Research question | Hypothesis (falsifiable) | Study | Primary metric |
|---|---|---|---|---|
| RQ1 | Does service-centric, context-aware slicing serve socially critical rural services better than technology-centric (3GPP) or no slicing? | **H1a:** the proposed scheduler achieves higher priority-weighted demand satisfaction than `tgpp`, `static_equal` and `no_slicing`.<br>**H1b:** healthcare p95 one-way delay is lower than under `tgpp` and `no_slicing` in high-load contexts. | main | weighted utility; healthcare p95 delay |
| RQ2 | Which design elements contribute? | **H2:** removing surplus redistribution (with strict caps), context awareness or AQM lowers utility or raises critical-slice delay. | ablation | weighted utility; healthcare p95 |
| RQ3 | Does a learned priority policy improve on the rule-based demand-aware heuristic? | **H3:** `rl_ppo` exceeds `proposed` on weighted utility. | main (+ simulator) | weighted utility; mean reward |
| RQ4 | Can the network recover autonomously from backhaul and core failures? | **H4a:** with self-healing, core-bound service outage after a fiber cut is below 1 s.<br>**H4b:** predictive detection switches over before the cut, with less outage than reactive-only. | resilience | outage (s); packets lost; MTTD/MTTR |
| RQ5 | Can services be identified from traffic shape and used to slice a multi-service UE? | **H5a:** SliceNet macro F1 ≥ 0.9 on held-out runs and UEs.<br>**H5b:** in-loop SliceNet raises the mixed UE's SLA-met share over address-based slicing. | SliceNet training; slicenet_inloop | macro F1; mixed-UE SLA share |
| RQ6 | Do synthetic datasets transfer to measured traffic? | **H6:** a model trained only on RSNSD v1 synthetic data performs near chance on measured flows; adding measured data recovers performance. | transfer study | macro F1 vs share of measured data |
| RQ7 | How robust is the approach to capacity, load and scale? | **H7:** the proposed scheduler's advantage over static slicing persists from 50 to 150 Mbps and from 0.5× to 1.5× load. | sensitivity, scalability | weighted utility |
| RQ8 | Does the control plane carry over to a real 5G core? | **H8:** on Open5GS + UERANSIM, CARS-SF enforcement on the UPF lowers critical-slice delay compared with no slicing. | 5G deployment | healthcare p95; SLA share |
| RQ9 | Does context awareness itself help, against service-aware slicing that ignores context? | **H9:** `proposed` exceeds `context_unaware` (same scheduler, normal-context priority matrix throughout) on weighted utility. | main | weighted utility; healthcare SLA share |
| RQ10 | Does self-healing reduce service interruption? | **H10:** full self-healing gives lower core-bound outage than `no_healing` on the same failures (paired by scenario and seed). | resilience | outage (s) |

H9 and H10 were added during the engineering audit (October 2026), after a first
evaluation in which context awareness was tested only as a two-scenario ablation.
They are therefore **not pre-registered**. They are evaluated on the complete
re-run of the matrix with the audited code, and reported whichever way they come out.

## Method

* **Testbed:** Mininet emulation of a three-tier rural private network (§3 of
  ARCHITECTURE.md) with a 100 Mbps rural uplink, 2 UEs per service and 16
  registry applications per service set, whose traffic models are listed in
  `registries/applications.yaml`.
* **Operating contexts:** normal, school, harvest, disaster and medical emergency, each
  with a design demand (offered load 80–145 Mbps) and priority matrix
  (`registries/scenarios.yaml`). There are three failure scenarios.
* **Runs:** 40 s (45 s for resilience). Five seeds in the main study and three
  elsewhere. Seeds fix every traffic model's random stream.
* **Measurement:** endpoint captures matched packet by packet (one-way delay, loss,
  jitter, queueing delay); per-slice SLA monitoring; control-plane timestamps.
* **Execution:** 4 parallel runs, each in its own network namespace. Host load is kept
  below the core count, because CPU starvation perturbs emulated link timing (an
  earlier busy-waiting traffic generator did exactly that; those runs were discarded).

## Metrics

| Metric | Definition |
|---|---|
| Weighted utility | Σ wₛ · min(1, delivered/demand)ₛ / Σ wₛ, with w = the context priority weights |
| Demand satisfaction | delivered / design demand per slice (time-averaged over the run) |
| SLA-satisfied share | fraction of flow windows meeting all of their application's latency, jitter and loss targets |
| p95 / p99 delay | percentiles of per-window p95 one-way delay |
| Jain fairness | (Σx)² / (n Σx²) over per-slice demand satisfaction |
| Outage | longest delivery gap of core-bound flows after a failure |
| MTTD / MTTR | detection and recovery-action time minus injection time |

## Statistics

* Means are reported with 95 % confidence intervals (Student t across seeds).
* Scheduler comparisons use **paired Wilcoxon signed-rank tests** on (scenario, seed)
  pairs (n = 25 per comparison in the main study), with α = 0.05. With six
  baselines × six metrics, results are flagged at both the nominal level and a
  Bonferroni level (α/36 ≈ 0.0014).
* Classifier results use group hold-out (run × UE), never random row splits.

## Threats to validity

* **Internal.**
  * Emulation timing depends on host load: runs are parallelised conservatively and
    pacing never busy-waits.
  * Captures run in software on the same host as the traffic, so the timestamps
    include kernel scheduling noise. That noise is on the order of tens of µs,
    which is negligible against the ms-scale delays measured.
* **Construct.**
  * Weighted utility rewards satisfying high-priority slices by design.
  * SLA targets are the registry's values, chosen from literature-typical
    requirements, not from measurements of real rural services.
* **External.**
  * Linux-bridge emulation replaces OVS in sudo-free runs.
  * Traffic comes from parametric models, not real traces.
  * The radio layer is absent in Mininet; in the 5G deployment it is simulated by
    UERANSIM, whose user-space data path limits throughput.
  * Results characterise this topology (a single shared bottleneck) and should not
    be generalised to multi-cell RAN scheduling.
* **Conclusion.**
  * Three to five seeds per configuration bound statistical power; CIs are reported
    throughout.
  * The learned policies are trained in a simulator calibrated from the emulation,
    not trained on the emulation itself.
