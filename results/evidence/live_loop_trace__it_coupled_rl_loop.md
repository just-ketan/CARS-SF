# Live coupled-loop trace: `it_coupled_rl_loop`

Scheduler `rl_online`, scenario `school`, data source `pcap`, 205 measured flow windows; contract: True.
Enforcement: {"decisions_applied": 12, "verified": 12, "failed": 0, "unverifiable": 0}.
Transitions: {"transitions": 11, "learnable": 11, "unverified": 0, "failed_enforcement": 0, "mean_reward": 84.0151}.
Policy learning: {"algorithm": "online CEM on live transitions", "checkpoint": "/tmp/pytest-of-ketan/pytest-12/test_coupled_rl_loop_on_live_n0/cem_online.json", "samples_this_run": 11, "updates_this_run": 2}.

| decision tick → next | reason | action (priority: log10 multipliers; residual: rate corrections) | allocation Mb/s (h/e/a/g) | kernel read-back | measured Mb/s per tick (h/e/a/g) | per-tick reward | transition reward |
|---|---|---|---|---|---|---|---|
| 0 → 2 | initial | [-0.06, -0.36, 0.85, -0.64] | 5.0/76.2/10.0/8.8 | verified=True, mismatches=0 | 1.5/17.3/3.2/5.0; 5.6/73.3/9.5/25.3 | 1.5, 91.9 | 46.71 |
| 2 → 4 | healing normal (boosts generalx0.5,healthcarex2) | [-0.23, -0.23, 1.00, -0.43] | 5.0/79.1/10.0/5.9 | verified=True, mismatches=0 | 5.9/73.9/10.6/24.3; 6.2/71.3/10.1/15.4 | 92.7, 90.4 | 91.58 |
| 4 → 8 | control interval | [-0.27, -0.64, 0.53, -0.65] | 12.6/56.4/24.8/6.3 | verified=True, mismatches=0 | 5.7/76.3/10.3/17.4; 5.1/63.5/9.3/20.7; 5.0/61.4/10.9/21.4; 5.9/68.0/9.9/24.5 | 90.9, 86.4, 86.6, 90.2 | 88.51 |
| 8 → 12 | healing normal (boosts none) | [-0.68, -0.38, 0.37, -0.85] | 7.0/74.2/12.8/5.9 | verified=True, mismatches=0 | 6.0/69.2/11.0/13.4; 4.4/70.5/9.1/18.9; 5.5/68.3/11.1/25.6; 6.3/69.1/9.8/22.2 | 87.4, 84.5, 90.6, 90.2 | 88.17 |
| 12 → 16 | control interval | [-0.23, -0.40, 0.79, -0.40] | 5.7/70.0/9.7/14.6 | verified=True, mismatches=0 | 5.7/68.8/10.6/24.4; 5.5/70.0/10.3/24.7; 4.6/60.3/11.0/25.7; 4.7/56.1/9.6/25.2 | 89.8, 91.3, 84.0, 81.5 | 86.65 |
| 16 → 19 | control interval | [-0.26, -0.16, 0.61, -0.50] | 5.0/56.1/12.4/26.6 | verified=True, mismatches=0 | 4.9/59.7/10.9/26.7; 4.9/58.4/10.0/31.3; 4.2/57.8/10.4/39.7 | 84.6, 86.2, 81.3 | 84.04 |
| 19 → 20 | healing normal (boosts generalx0.5) | [-0.20, -0.42, 0.59, -0.64] | 4.8/63.9/10.2/21.1 | verified=True, mismatches=0 | 4.8/58.6/9.3/26.8 | 82.8 | 82.75 |
| 20 → 24 | control interval | [-0.27, -0.39, 0.53, -0.56] | 5.3/72.6/11.7/10.4 | verified=True, mismatches=0 | 5.8/62.3/10.9/29.1; 6.3/62.0/11.1/31.2; 6.5/61.9/12.8/22.8; 5.2/66.9/10.5/24.3 | 87.2, 88.5, 87.1, 89.7 | 88.11 |
| 24 → 25 | control interval | [-0.26, -0.33, 0.82, -0.50] | 7.0/74.4/12.8/5.8 | verified=True, mismatches=0 | 4.7/75.8/10.3/18.7 | 90.7 | 90.71 |
| 25 → 28 | healing normal (boosts none) | [-0.28, -0.40, 0.76, -0.36] | 5.7/67.8/11.1/15.4 | verified=True, mismatches=0 | 5.5/70.0/10.0/25.5; 4.6/68.7/11.9/27.6; 5.2/60.8/9.4/25.8 | 90.5, 88.2, 86.1 | 88.24 |
| 28 → 32 | control interval | [-0.32, -0.32, 0.83, -0.42] | 6.3/70.8/11.0/11.9 | verified=True, mismatches=0 | 5.5/63.7/10.2/21.9; 5.4/69.6/9.9/23.0; 4.5/70.0/11.2/24.9; 5.0/64.5/10.3/25.7 | 87.5, 90.6, 87.8, 88.8 | 88.69 |

Observation chaining: every transition's `next_obs` equals the next transition's `obs`: **True**. First observation (tick 0): [0.000, 1.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.050, 0.800, 0.100, 0.500, 0.000, 0.000, 0.000, 0.000, 0.250, 0.250, 0.250, 0.250, 0.000]. Final transition done = True.

