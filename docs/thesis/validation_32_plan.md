# 32-Combination Validation Plan (predeclared)

Written before any validation run. It evaluates the integrated closed loop on the 5G deployment
(Open5GS + UERANSIM, `deployment/5g/`), across 4 classes × 8 scenarios. It is separate from the emulated
and real-OVS final evaluation (`results/evidence/final_eval_v5/`), which is kept as evidence.

* **Environment.** Real 5G core signalling and GTP-U user plane in Docker, 100 Mb/s rural N3 link each
  way, simulated radio (UERANSIM). No radio resources are scheduled.
* **Scenarios.** normal, school, harvest, disaster, medical_emergency, fiber_cut, backhaul_degradation,
  core_switch_failure. 60 s each.
* **Seeds.** 40–44. Never used for development (dev runs used 80+; SliceNet data 30–32).
* **Command.** `.venv/bin/python experiments/validate_32.py`.

## Arms

| Arm | Controller | Classification | Purpose |
|---|---|---|---|
| `no_slicing` | one FIFO | none | Baseline |
| `rules` | `qos_adaptive` | PDU address pool | Rules with perfect slice identity |
| `slicenet` | `qos_adaptive` | SliceNet on every flow | Effect of classification |
| `full` | `closed_loop` (RL on persistent violation, online learning) | SliceNet on every flow | The complete system |

8 × 4 × 5 = 160 runs. `full` starts from an empty online checkpoint; the checkpoint carries across its runs
in seed order. All arms use self-healing except `no_slicing`.

## Per-combination result

For each of the 32 (scenario, class) cells and each arm: mean SLA-met share with 95 % CI over 5 seeds, from
packet-matched captures against each application's SLA. A cell **passes** at ≥ 0.95, the threshold of the final
evaluation. Thresholds are never relaxed; `registries/qos_thresholds.yaml` can only tighten them.

SliceNet is scored per cell: share of flows whose final class matches the generator's ground truth.

## End-to-end chain (per `full` run)

Each step needs evidence recorded in the run:

1. Monitored: telemetry on every tick, from real counters and probes.
2. Identified: SliceNet made decisions.
3. Mapped: flows steered into a class at both enforcement points (`flow_rules`), scored against truth.
4. Evaluated: the QoS monitor ran every tick and classified breaches.
5. Triggered: a persistent violation activated RL (where one occurred).
6. Decided: the agent produced an action.
7. Applied: the allocation was applied and read back from the kernel.
8. Measured: later measurements scored the adaptation (`improved`, `restored`).
9. Autonomous: the run finished all ticks with no manual step.

## Primary comparisons

Paired by (scenario, seed), two-sided Wilcoxon, mean difference with 95 % CI, rank-biserial r, Holm over V1–V5.

| ID | Claim | Comparison | Metric | Supported if |
|---|---|---|---|---|
| V1 | Slicing protects the critical class on 5G | `rules` vs `no_slicing` | healthcare SLA | > 0, Holm-significant |
| V2 | The full system beats no slicing on the worst-off class | `full` vs `no_slicing` | worst class SLA | > 0, Holm-significant |
| V3 | SliceNet replaces address rules | `slicenet` vs `rules` | mean class SLA | lower CI bound ≥ −0.02 (non-inferior) |
| V4 | RL improves on the rules | `full` vs `slicenet` | mean class SLA | > 0, Holm-significant |
| V5 | RL reduces persistent violation | `full` vs `slicenet` | persistent-violation ticks | < 0, Holm-significant |

**Requirements.** R5 safety: 0 failed verifications and 0 validator rejections in all runs. R6 chain: every `full`
run shows steps 1–4, 7 and 9; every run with a persistent violation also shows steps 5, 6 and 8.

**Rule.** No algorithm or threshold changes after this plan. A defect found during validation is reported, and
any fix needs a new run on fresh seeds.
