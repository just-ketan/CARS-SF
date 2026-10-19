# RL Scheduler Design (as implemented)

The learning engine never allocates bandwidth directly. Its action rescales the
context's **priority matrix**. The demand-aware allocator, the per-slice floors
and the self-healing constraints then compute the allocation, which the QoS
enforcer applies. As a result, no learned policy can break a guaranteed floor or
oversubscribe the link.

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
