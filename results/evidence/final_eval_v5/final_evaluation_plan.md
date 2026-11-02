# Final Evaluation Plan (predeclared)

This plan was written and frozen **before** the final evaluation was run, after the changes made under the "close
the research objective" mandate (see `docs/RUNTIME_PATH.md` §3). It supersedes the contended-regime studies v1–v4,
which are preserved under `results/evidence/qos_eval_v1/`–`v3/` and `results/evidence/baseline_v4/`.

* **Seeds.** 20–24 for every `final_*` study. These have never been used for development or tuning. Development
  checks used seeds ≥ 90; the OVS validation uses 30–32.
* **Configuration.** `configs/experiments/thesis.yaml` (`final_*` studies), `registries/*.yaml`, frozen at the commit
  and staged-diff hash recorded in the final pipeline manifest.
* **Command.** `.venv/bin/python run_pipeline.py --mode full`.

## Studies

| Study | Conditions | Schedulers | Runs |
|---|---|---|---|
| `final_contended` | disaster, medical_emergency, disaster ×1.5, school ×1.5, harvest @ 50 Mb/s, school @ 50 Mb/s, timelines rural_day and medical_night | static_equal, proportional, proposed, qos_blind, qos_aware, qos_reactive, qos_adaptive, rl_residual, rl_residual_safe | 8 × 9 × 5 = 360 |
| `final_feasible` | normal, school, harvest @ 100 Mb/s | static_equal, proposed, qos_blind, qos_adaptive | 3 × 4 × 5 = 60 |
| `final_prediction` | timelines load_ramp, load_surge, emergency_ramp, rural_day | qos_aware, qos_reactive, qos_adaptive, qos_oracle (upper bound) | 4 × 4 × 5 = 80 |
| `final_slicenet` | school, disaster | qos_adaptive × classification host / slicenet_all | 2 × 2 × 5 = 20 |
| `final_rl_online`, `final_rl_online_nolearn` | disaster, medical_emergency (sequential, shared checkpoint for the learner) | rl_residual_online / rl_residual_online_nolearn | 2 × 2 × 5 = 20 |
| `resilience` (extended) | + repeated_fiber_cut | full / reactive_only / no_healing | +9 |
| OVS validation (`experiments/ovs_validation.py`) | real Open vSwitch; actuation, OVS-native queues, 4 fault types | see the script | 33 |

## Metrics

* **Class SLA share.** The share of a class's 5 s flow windows meeting the application's SLA (delay, jitter, loss).
* **Mean / worst class SLA.** The mean / minimum of the four class SLA shares in a run.
* **Healthcare SLA.** The critical class's SLA share.
* **Transient SLA.** Mean class SLA in the windows overlapping 10 s after each context or load change (timelines
  only).
* **Safety.** Per run:
  * safety-validator rejections;
  * failed kernel verifications;
  * any planned per-direction allocation with Σ > C or a slice below its protected minimum (read from the
    controller history);
  * starvation = an active class with SLA share < 0.1 while another class in the same direction has SLA share ≥ 0.9.
* **Reconfiguration.** Allocation changes applied per run.

## Requirements (pass/fail)

* **R1 (feasible SLAs).** In `final_feasible`, in every run where every recorded planning decision was in the
  `sla_feasible` regime in both directions, all four classes have SLA share ≥ 0.95, for `qos_adaptive`.
* **R2 (safety).** In every `final_*` run: 0 failed verifications, 0 planned capacity or protected-minimum
  violations, 0 safety-validator rejections of heuristic plans.
* **R3 (starvation-resistant degradation).** In every `final_contended` run of the QoS-targeted schedulers: no
  starvation as defined above, and every overload decision recorded with its regime, policy and degraded classes.

## Predeclared comparisons

All comparisons are paired by (condition, seed). The statistics are:

* two-sided Wilcoxon signed-rank test;
* mean paired difference with a 95 % t-interval;
* effect size as the matched-pairs rank-biserial correlation.

The **primary family** is corrected together with **Holm** (α = 0.05):

| ID | Claim | Comparison | Metric | Study | Supported if |
|---|---|---|---|---|---|
| C1 | QoS-targeted allocation protects the critical class | qos_adaptive vs proposed | healthcare SLA | final_contended | difference > 0 and Holm-significant |
| C2 | It does so without hurting the worst-off class | qos_adaptive vs proposed | worst class SLA | final_contended | difference ≥ −0.01 (not significantly negative) |
| C3 | Context awareness helps where context is informative | qos_aware vs qos_blind | healthcare SLA (emergencies, timelines) and transient SLA (timelines) | final_contended | either difference > 0, Holm-significant, and the other not significantly negative |
| C4 | Context is redundant where demand fits (expected: no difference) | qos_adaptive vs qos_blind | mean class SLA | final_feasible | \|difference\| ≤ 0.01 (equivalence by CI) |
| C5 | Reactive control helps | qos_reactive vs qos_aware | transient SLA | final_prediction | > 0, Holm-significant |
| C6 | Prediction helps beyond reaction | qos_adaptive vs qos_reactive | transient SLA and mean class SLA | final_prediction | either > 0, Holm-significant |
| C7 | RL improves on the heuristic | rl_residual vs qos_adaptive | mean class SLA | final_contended | > 0, Holm-significant, and no safety regression |
| C8 | The safe hybrid improves on the heuristic | rl_residual_safe vs qos_adaptive | mean class SLA | final_contended | > 0, Holm-significant |
| C9 | Online learning helps | rl_residual_online vs nolearn | mean class SLA | final_rl_online* | > 0, Holm-significant |
| C10 | SliceNet on every flow is non-inferior to address rules | slicenet_all vs host | mean class SLA | final_slicenet | difference ≥ −0.02 by the lower CI bound |
| C11 | Self-healing reduces outage | full vs no_healing | core-bound outage | resilience | < 0, significant |

**Secondary and descriptive analyses** (not part of the Holm family):

* qos_adaptive vs static_equal and vs proportional (simple baselines);
* qos_oracle as the prediction upper bound;
* forecast quality (`experiments/forecast_eval.py`) on `final_prediction` runs;
* RL learning curves, seeds, reward-weight sensitivity (sla_x2, loss_x4) and held-out generalisation (simulation);
* OVS validation outcomes;
* per-class tables.

**Rule.** No algorithm or evaluation definition is changed after this plan. If a defect is found, it is reported
and the affected claims are marked accordingly; any fix would need a new recorded evaluation on fresh seeds.
