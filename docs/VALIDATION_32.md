# 32-Combination Validation Report

Results of the integrated closed loop across 4 traffic classes × 8 scenarios, on the 5G deployment. The plan, written
before the runs, is [thesis/validation_32_plan.md](thesis/validation_32_plan.md). The setup is in [spec.md](../spec.md).

**Environment.** Real Open5GS 5G core signalling and real GTP-U user plane in Docker, with a simulated radio
(UERANSIM) and a 100 Mb/s N3 link each way. These are testbed results. No radio resources are scheduled, and nothing
here was measured on real radios or at a real rural site.

**Evidence.** Seeds 50–54, 160 runs of 60 s, one code fingerprint (`c49be2a6d6553470`) and one model fingerprint
(`dc473a4288b86caa`). Tables: `results/tables/v32_cells.csv`, `v32_claims.csv`, `v32_chain.csv`, `v32_runs.csv`. Raw
runs: `results/5g/v32b__*`.

## Summary

* **The loop works end to end.** Every `full` run shows the chain, and all 17 runs with a persistent violation
  triggered RL.
* **Slicing has a large, significant effect.** Healthcare SLA rises by 0.225 under rules, and the worst class rises
  by 0.274 under the full system, both against no slicing.
* **SliceNet can replace address rules.** It is non-inferior at the planned margin, though it costs some SLA in two
  fault scenarios.
* **RL adds nothing measurable on the network.** V4 and V5 are unsupported, and the rules arm passes the most cells.
* **Not every combination passes.** The full system passes 23 of 32 cells. Nine fail, and most of those are capacity
  or topology limits rather than control errors.
* **Safety held.** 0 failed verifications and 0 validator rejections in 160 runs.

## Results for each combination

Each cell is the mean share of flow windows meeting the application's SLA over 5 seeds. A cell passes at ≥ 0.95.
Failing cells are in bold.

**`no_slicing`: 19 of 32 cells pass.**

| Scenario | healthcare | education | agriculture | general |
|---|---|---|---|---|
| normal | 1.000 | 1.000 | 0.997 | 1.000 |
| school | 1.000 | **0.885** | 1.000 | 0.960 |
| harvest | **0.414** | 0.996 | **0.833** | 0.992 |
| disaster | **0.218** | 1.000 | **0.907** | 1.000 |
| medical_emergency | **0.157** | 1.000 | **0.879** | 1.000 |
| fiber_cut | 0.991 | **0.712** | 0.997 | **0.799** |
| backhaul_degradation | 1.000 | **0.812** | 1.000 | **0.881** |
| core_switch_failure | 0.996 | **0.707** | 1.000 | **0.802** |

**`rules`: 26 of 32 cells pass.**

| Scenario | healthcare | education | agriculture | general |
|---|---|---|---|---|
| normal | 1.000 | 1.000 | 1.000 | 1.000 |
| school | 1.000 | 1.000 | 1.000 | 0.996 |
| harvest | 0.983 | 1.000 | 1.000 | 1.000 |
| disaster | **0.824** | 1.000 | **0.806** | 1.000 |
| medical_emergency | **0.779** | 1.000 | **0.733** | 1.000 |
| fiber_cut | 0.998 | 0.998 | 1.000 | 1.000 |
| backhaul_degradation | 0.998 | 1.000 | 1.000 | 1.000 |
| core_switch_failure | 0.993 | **0.791** | 0.998 | **0.814** |

**`slicenet`: 24 of 32 cells pass.**

| Scenario | healthcare | education | agriculture | general |
|---|---|---|---|---|
| normal | 0.996 | 1.000 | 1.000 | 1.000 |
| school | 1.000 | 0.996 | 1.000 | 0.994 |
| harvest | 0.987 | 1.000 | 1.000 | 1.000 |
| disaster | **0.787** | 1.000 | **0.891** | 1.000 |
| medical_emergency | **0.769** | 1.000 | **0.748** | 1.000 |
| fiber_cut | 0.993 | 0.971 | 1.000 | 0.955 |
| backhaul_degradation | 0.998 | **0.936** | 1.000 | **0.866** |
| core_switch_failure | 0.985 | **0.817** | 0.998 | **0.799** |

**`full`: 23 of 32 cells pass.**

| Scenario | healthcare | education | agriculture | general |
|---|---|---|---|---|
| normal | 1.000 | 1.000 | 1.000 | 1.000 |
| school | 1.000 | 1.000 | 1.000 | 0.990 |
| harvest | 0.989 | 1.000 | 0.996 | 1.000 |
| disaster | **0.813** | 1.000 | **0.825** | 1.000 |
| medical_emergency | **0.772** | 1.000 | **0.739** | 1.000 |
| fiber_cut | 0.991 | 0.984 | 1.000 | **0.940** |
| backhaul_degradation | 1.000 | **0.934** | 1.000 | **0.861** |
| core_switch_failure | 1.000 | **0.823** | 1.000 | **0.784** |

### The nine failing cells under `full`

| Cells | Under `rules` | Cause |
|---|---|---|
| disaster and medical_emergency: healthcare, agriculture | Also fail | Uplink overload: healthcare and agriculture together approach the 100 Mb/s link. Slicing limits the damage but cannot create capacity |
| core_switch_failure: education, general | Also fail | No alternate path to core-cloud services. Self-healing diagnoses this and escalates |
| fiber_cut: general; backhaul_degradation: education, general | Pass | Appear only with SliceNet in the loop. They coincide with its lowest flow accuracy, but the cause has not been diagnosed |

## Claims

Paired by (scenario, seed), two-sided Wilcoxon, Holm over V1–V5.

| Claim | Comparison | Metric | Mean difference [95 % CI] | r | Holm p | Verdict |
|---|---|---|---|---|---|---|
| V1 Slicing protects the critical class | `rules` vs `no_slicing` | healthcare_sla | +0.225 [+0.130, +0.320] | +0.92 | < 0.001 | supported |
| V2 Full system beats no slicing on the worst class | `full` vs `no_slicing` | min_class_sla | +0.274 [+0.192, +0.355] | +0.98 | < 0.001 | supported |
| V3 SliceNet replaces address rules (margin −0.02) | `slicenet` vs `rules` | mean_class_sla | -0.007 [-0.015, +0.001] | -0.36 | n/a (CI rule) | supported |
| V4 RL improves on the rules | `full` vs `slicenet` | mean_class_sla | -0.001 [-0.006, +0.003] | -0.20 | 0.321 | unsupported |
| V5 RL reduces persistent violation | `full` vs `slicenet` | persistent_ticks | +2.675 [-0.374, +5.724] | +0.66 | 0.090 | unsupported |

V3 is decided by its confidence interval, as planned: the lower bound −0.015 clears the −0.02 margin. V5 points the
wrong way (2.7 more persistent ticks with RL), and that difference is not significant either.

**Requirements.** R5 safety holds. R6 chain holds.

## End-to-end chain

| Step | Runs required | Runs with evidence |
|---|---|---|
| 1 monitored | 40 | 40 |
| 2 identified | 40 | 40 |
| 3 mapped | 40 | 40 |
| 4 evaluated | 40 | 40 |
| 5 triggered | 17 | 17 |
| 6 decided | 17 | 17 |
| 7 applied+verified | 40 | 40 |
| 8 outcome measured | 17 | 17 |
| 9 autonomous | 40 | 40 |

Steps 5, 6 and 8 apply only to runs with a persistent violation. Steps 4 and 9 are weak checks: step 4 confirms that
the monitor produced a count, and step 9 confirms that a run with no operator input produced records.

**RL activity in the 40 `full` runs.** 173 proposals reached the safety gate: 81 accepted, 92 rejected by the
learned-plan rules. 96 adaptations were measured afterwards: 30 improved and 21 restored the class. All 633 rate
decisions were read back from the kernel and matched. That gate is separate from the validator, which rejected
nothing.

**Self-healing in `full`.** In all 15 fault runs, every recovery action was verified. The backup path took over
within 0.034 s of a fiber cut (control time). Under backhaul degradation it switched before the cut, 5 s after the
trend was detected. Core switch failure was diagnosed and escalated in all 5 runs.

## SliceNet in the loop

Share of flows whose final class matches the generator's ground truth, in `full`:

| Scenario | healthcare | education | agriculture | general |
|---|---|---|---|---|
| normal | 0.833 | 0.900 | 1.000 | 0.725 |
| school | 1.000 | 0.775 | 1.000 | 0.675 |
| harvest | 1.000 | 0.850 | 0.950 | 0.700 |
| disaster | 1.000 | 0.950 | 1.000 | 0.650 |
| medical_emergency | 1.000 | 0.875 | 0.975 | 0.675 |
| fiber_cut | 0.960 | 0.850 | 1.000 | 0.700 |
| backhaul_degradation | 0.950 | 0.775 | 1.000 | 0.675 |
| core_switch_failure | 0.950 | 0.775 | 1.000 | 0.650 |

Overall 0.902 by final class across 1 860 flows, against 0.933 offline on held-out seed 32 (the two score different
units: flows here, flow windows there). The median decision took 1.5 s. General is the weakest class, at 0.65–0.73 in
each scenario and 0.681 overall; education follows at 0.844. These are the classes that share the `web_tcp` traffic
model.

## Void runs

**First run (seeds 40–44), void.** A UERANSIM radio link failure at 19:00 IST left the healthcare slice dead for that
run and all 56 later ones, because the gNB refused the reattach and the harness only checked the tunnel's address.
The monitor reported the dead slice as healthy, which was a real defect. Both were fixed, and the plan requires fresh
seeds after a fix. The first run's numbers are not used. They are kept in `results/evidence/v32_run1_void/`.

**Second run, one void run.** `harvest / no_slicing / s51` lost the agriculture radio link. The run was moved to
`results/evidence/v32b_void/` and repeated on the same seed, under the rule written before the run. The radio failed
twice in about 320 runs, both times mid-run. Both failures come from the simulated radio, not from the system under
test.

## Limits of these results

* Five seeds per cell, so a cell's confidence interval can be wide: up to ±0.12 for `full`.
* One UE per slice, so the classes have no per-UE contention.
* N3 and the simulated radio add no propagation delay, so latencies here are not comparable with the Mininet results.
* All slices use 5QI 9, and rate changes never reach the 5G core's policy functions.
