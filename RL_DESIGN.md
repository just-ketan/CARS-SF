# RL Scheduler Design (as implemented)

The learning engine never allocates bandwidth directly. Its action rescales the
context's **priority matrix**. The demand-aware allocator, the per-slice floors
and the self-healing constraints then compute the allocation, which the QoS
enforcer applies. As a result, no learned policy can break a guaranteed floor or
oversubscribe the link.

## Two generations of learned policy

| | Priority policies (first design) | Residual policy (current) |
|---|---|---|
| Acts on | Priority multipliers fed to the demand-aware allocator | Per-slice rates of the QoS-aware, direction-aware allocation (±30 %) |
| State | 21 floats: context, demand, backlog, allocation, on-backup | 25 floats (state v2): adds measured loss and queueing delay relative to each SLA |
| Simulator | `SequentialSlicingEnv`: one pipe, no bursts, no AQM | `DirectionalSlicingEnv`: both directions, 100 ms bursts, HTB borrowing, CoDel tolerance, TCP back-off; calibrated against live loss |
| Schedulers | `rl_cem`, `rl_ppo`, `rl_online` | `rl_residual`, `rl_residual_online` |
| Result | Simulation +3–4 % (after module A's reward change); live: marginal PPO edge, not robust | Simulation +0.3–0.5 %; live = heuristic |

The priority-policy sections below are kept because those schedulers remain in the study.

## Modes

| Mode | Environment | What learns | Code |
|---|---|---|---|
| Simulation training | `SequentialSlicingEnv` (Gymnasium) | CEM (per-context multipliers) and PPO (state-dependent) | `scheduler/agent.py`, `scheduler/train.py` |
| Mininet inference | The live control loop | Nothing: the trained CEM or PPO policy is queried at every decision | schedulers `rl_cem`, `rl_ppo` |
| Mininet online learning | The live control loop | Online CEM, updated only from verified live transitions | scheduler `rl_online` (`OnlineCEMPolicy`) |
| Offline evaluation | `SequentialSlicingEnv` with fixed test seeds | — | `scheduler/train.py --evaluate-only` |

Every live run, whatever the scheduler, writes `rl_transitions.jsonl`: one
(s, a, r, s′) record per controller decision. Rule-based schedulers log the
action 0 (all multipliers 1).

## State (21 floats, `SequentialSlicingEnv._obs` / `observation_from_live`)

| Index | Signal | Units / normalisation | Live source |
|---|---|---|---|
| 0–7 | Context one-hot (normal, school, harvest, disaster, medical_emergency, fiber_cut, backhaul_degradation, core_switch_failure) | {0,1} | Context engine |
| 8–11 | Demand per slice | Mb/s ÷ capacity (100) | Demand estimator (measured offered load, Holt forecast; design prior until warmed up) |
| 12–15 | Backlog per slice | Mbit ÷ (capacity × 0.1 s), capped at 10 | HTB class backlog bytes, both directions (`queue_bytes`) |
| 16–19 | Current allocation per slice | Mb/s ÷ capacity | Allocation in force before the decision |
| 20 | On backup / degraded | {0,1} | Self-healing state |

Missing values: a missing backlog counts as 0. A missing allocation counts as
capacity/4. An unknown context leaves the one-hot all zero. Timing: the
observation is built at the decision tick from the snapshot just polled.

## Action (4 floats in [−1, 1])

The action is a log10 priority multiplier per slice: `multiplier = 10^a`, in
[0.1, 10]. The effective priority is the context weight × multiplier, times any
boost from self-healing. Out-of-range actions are clipped. The allocation is
recomputed and applied only if some slice changes by ≥ 1 Mb/s. The applied
allocation is read back from the kernel; on a mismatch or a failed command
(`verified: False`) the controller keeps the last good allocation.

## Reward (`scheduler/reward.py`, one function for simulator, live log and transitions)

```
r = R_sat + R_sla + R_loss + R_starve + R_realloc + R_idle
R_sat     = 100 · Σ w̃_s · min(1, delivered_s / demand_s)     (context weights, normalised)
R_sla     = −10 per slice whose one-way delay exceeds its SLA (missing delay = violation)
R_loss    = −0.5 · mean loss %
R_starve  = −20 per slice with demand ≥ 0.5 Mb/s receiving < 10 % of it
R_realloc = −5 · Σ|a_s − a'_s| / capacity
R_idle    = −5 · idle capacity share, only while some slice is unsatisfied
```

SLA delay targets come from `registries/slices.yaml`: healthcare 50 ms,
education 150 ms, agriculture 250 ms, general 500 ms.

**Live mapping** (`outcomes_from_snapshot`):

| Reward input | Live measurement |
|---|---|
| Delivered | Uplink + downlink interface throughput of the slice's hosts |
| Delay | Probe RTT / 2 |
| Loss | Δdropped / (Δsent + Δdropped) on the slice's HTB classes |
| Reallocation | Allocation change from the previous tick |

**Credit assignment.** Each tick's snapshot measures the interval that just
ended. Its reward is therefore credited to the decision in force during that
interval, *before* the controller decides again. A transition's reward is the
mean per-tick reward from the decision to the next decision. A decision on the
final tick has no measured interval and yields no transition. Transitions whose
enforcement failed are logged as not learnable.

Known semantic differences between the simulator and the live network:

* The simulator models one pipe of capacity C. The live uplink is full-duplex
  and delivered counts both directions, so the live idle term is a lower bound.
* Live delay is RTT/2 from probes rather than a modelled queue.
* Live reallocation is measured per tick.

## Training and evaluation

| Seed set | Used for |
|---|---|
| Training seeds (CEM: 0…; PPO: VecEnv seeds) | Training |
| Validation seeds (2000…) | Model selection and checkpoint choice |
| Test seeds (1000…) | All reported comparisons |

**CEM.** 30 iterations × 16 samples per context, scored on fixed-context
episodes with common random numbers. A context keeps the rule-based priorities
when CEM does not beat them on validation.

**PPO.** 200k steps × 3 seeds. Every 20k steps the policy is evaluated on the
validation seeds and checkpointed (`scheduler/models/ppo_runs/seed*/`, with
`learning_curve.csv`). The best checkpoint per seed is kept. The deployed model
is the seed with the best validation score, and it is reloaded from disk before
evaluation.

**Reporting.** The mean ± SD over test episodes, plus a paired comparison against
rule-based on the same episodes (mean difference, 95 % CI, Wilcoxon p). Numbers
are in `results/rl_training.json` and `docs/thesis/results.md`.

**Online CEM.**

* It starts from the simulator CEM policy and samples an action from N(mean, σ)
  at each decision.
* After 4 learnable live transitions of a context, the mean moves to the top 2
  actions and σ shrinks (floor 0.05).
* The checkpoint `scheduler/models/cem_online.json` carries over between runs.
  `CARS_SF_CEM_ONLINE_PATH` redirects it, as the tests do.

## Verification

| Test | What it proves |
|---|---|
| `tests/test_reward.py` | Every reward term and edge case; the live snapshot mapping |
| `tests/test_transitions.py` | Transitions chain (next_obs of t = obs of t+1); interval rewards; failed enforcement never learned; online CEM converges toward a better action and resumes from its checkpoint |
| `tests/integration/test_pipeline.py::test_coupled_rl_loop_on_live_network` | On a real emulated network: ≥ 5 consecutive transitions, actions in bounds, every changed allocation read back from the kernel with no mismatch, rewards recomputed from `feedback.csv`, and online-CEM updates from exactly the learnable live transitions |


## Residual policy (`scheduler/residual.py`, `scheduler/env_dir.py`)

**Why.** Live, priority multipliers barely change the allocation: HTB borrowing redistributes idle capacity anyway, and
PPO learned near-identity multipliers. The measured failure was loss in the emergency contexts, which the controller
could not even see before module A. The residual policy acts on rates directly, starting from a strong heuristic:
`QoSAwareAllocator` allocates demands first, degrades in explicit priority order, and adds burst headroom.

**State v2 (25 floats).**

| Index | Signal |
|---|---|
| 0–7 | Context one-hot |
| 8–11 | Demand in the slice's dominant direction / C |
| 12–15 | Allocation in that direction / C |
| 16–19 | Interval loss / SLA loss target, clipped at 5, scaled to [0, 1] |
| 20–23 | Interval queueing delay / SLA delay, clipped at 2, scaled to [0, 1] |
| 24 | On backup |

Loss and queueing delay come from the bottleneck's HTB and fq_codel leaf counters (`slice_qos`), averaged since the
previous decision.

**Action.**

* a ∈ [−1, 1]⁴. Each slice's rate in its dominant direction is scaled by (1 + 0.3 aₛ).
* Each direction is then renormalised to C. A shortfall is taken from slices that did not ask for more, above their
  floors; freed capacity goes to slices that asked for more.
* Floors and Σ ≤ C always hold, and a = 0 is exactly the heuristic.

The residual replaces the hand-made loss→headroom loop, so `rl_residual` (no loop) vs `qos_adaptive` (with loop) is
a direct test of learned vs designed adaptation.

**Simulator.** Each 5 s step is fifty 100 ms sub-steps. In each sub-step:

* the offered rate is the mean demand × a mean-preserving lognormal factor (σₛ);
* each slice is served up to its rate;
* spare capacity is lent in HTB priority order, scaled by a borrowing efficiency β (kernel HTB at ~100 Mb/s does not
  lend instantly);
* a queue beyond rate × (CoDel target + interval) is dropped;
* TCP slices back off instead of dropping.

The base allocation is planned on the previous step's measured offered load, as the live estimator does. σ and β
were fitted by least squares to per-run mean loss of 720 live ticks (`python -m scheduler.calibrate_bursts`):
in the final pipeline run σ_healthcare = 0.05, σ_agriculture = 0.15 and β = 0.75, with per-run RMSE 1.7 and
2.6 percentage points (`scheduler/models/burst_calibration.json`, refitted by every pipeline run from the
`calibration_*` studies). Failures (on_backup) are not modelled.

**Training.**

* PPO, 300k steps × seeds 0, 1, 2, γ = 0.9.
* Validation (seeds 2000…) every 25k steps, keeping the best checkpoint.
* The deployed model is the seed with the best validation score.
* Test: 30 paired episodes on seeds 1000…, against a = 0.

Simulation result (final run): +0.3 to +0.5 % reward, significant for 2 of 3 seeds; SLA violations per episode
15.5 → 13.3–14.5. **On the network it equals its heuristic** (mean class SLA Δ 0.002, p = 0.20; H12 not supported).
`results/rl_training.json` (`residual`), `scheduler/models/ppo_residual_runs/seed*/learning_curve.csv`.

**Live.**

* `rl_residual` queries the deployed PPO at each decision.
* `rl_residual_online` runs CEM over the residual action, starting at a = 0. It samples each decision and learns only
  from kernel-verified transitions; its checkpoint (`cem_residual_online.json`) carries across runs.
* Both log state v2 and the residual action in `rl_transitions.jsonl`.

**Safety.** The residual cannot take a slice below the allocator's *protected* minimum (floor or anti-starvation
guard). Evaluation v3 showed that, without this bound, the policy learned to starve best-effort TCP, which the
simulator models as backing off cheaply; live, that slice's SLA collapsed to 0.04.
