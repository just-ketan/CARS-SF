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
| RQ11 | Can QoS-targeted, direction-aware control meet per-class SLAs where slices compete? | **H11:** `qos_adaptive` raises the mean per-class SLA-met share over `proposed` in contended regimes. | qos_* | mean / worst class SLA share |
| RQ12 | Does residual RL improve on the QoS-targeted heuristic? | **H12:** `rl_residual` exceeds `qos_adaptive` on mean class SLA share. | qos_* | mean class SLA share |
| RQ13 | Do reactive and predictive triggers add to QoS-targeted allocation? | **H13:** `qos_adaptive` exceeds `qos_aware`. | qos_* | mean class SLA share |
| RQ14 | Can SliceNet replace address rules for every flow? | **H14:** with `slicenet_all`, mean class SLA share is at most 0.02 below address-based classification and not significantly lower. | qos_slicenet | mean class SLA share |


H11–H14 were formulated after the post-audit diagnosis (healthcare missed its SLA only on loss, in emergencies),
before the contended-regime runs were made. They are not part of the original pre-registration.

Four evaluations exist; each later one uses fresh seeds, so a fix is never validated on the seeds that revealed
the defect.

* **v1** (seeds 0–4): H11–H14 not supported. Exposed best-effort starvation under overload and burst headroom
  ignored under overload.
* **v2** (seeds 5–9), after those fixes: H14 supported, H11–H13 not. Exposed an elastic-demand death spiral that
  defeated the starvation guard.
* **v3** (seeds 10–14): starvation fixed for the heuristic (worst-class SLA significantly better than `proposed`),
  H14 supported. Exposed that the residual RL could override the starvation guard.
* **v4** (seeds 15–19) is the confirmatory run after that fix, with residual RL retrained.

All four are reported (`results/evidence/qos_eval_v1/` … `qos_eval_v3/`, and the current tables). Agriculture's
degradation in the emergencies was judged a declared-priority trade-off, not a defect, and was not changed.

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


## Final evaluation

The final evaluation is predeclared in [final_evaluation_plan.md](final_evaluation_plan.md): claims C1–C11 and
requirements R1–R3, fresh seeds 20–24, Holm correction. It supersedes H11–H14 and the contended-regime rounds v1–v4,
which are kept as history.

Two deviations were found after the run and are reported, not hidden:

1. The plan listed school as a feasible condition, but its downlink demand exceeds capacity. R1's own
   verified-feasible rule excluded it.
2. The online learner's checkpoint carried state from earlier rounds. A post-hoc fresh-checkpoint replication is
   reported separately.

One analysis-only fix: the transient windows now include load changes, as the plan defines.
