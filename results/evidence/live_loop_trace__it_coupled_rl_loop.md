# Live coupled-loop trace: `it_coupled_rl_loop`

Scheduler `rl_online`, scenario `school`, data source `pcap`, 205 measured flow windows; contract: True.
Enforcement: {"decisions_applied": 12, "verified": 12, "failed": 0, "unverifiable": 0}.
Transitions: {"transitions": 11, "learnable": 11, "unverified": 0, "failed_enforcement": 0, "mean_reward": 84.8789}.
Policy learning: {"algorithm": "online CEM on live transitions", "checkpoint": "/tmp/pytest-of-ketan/pytest-13/test_coupled_rl_loop_on_live_n0/cem_online.json", "samples_this_run": 11, "updates_this_run": 2}.

| decision tick → next | reason | action (log10 mult.) | allocation Mb/s (h/e/a/g) | kernel read-back | measured Mb/s per tick (h/e/a/g) | per-tick reward | transition reward |
|---|---|---|---|---|---|---|---|
| 0 → 2 | initial | [-0.12, -0.16, 0.50, -0.42] | 5.0/75.8/10.0/9.2 | verified=True, mismatches=0 | 1.6/17.1/3.2/5.6; 5.6/71.4/9.5/28.8 | 22.5, 91.8 | 57.16 |
| 2 → 4 | healing normal (boosts generalx0.5) | [-0.28, -0.04, 0.67, -0.21] | 5.0/78.8/10.0/6.2 | verified=True, mismatches=0 | 5.9/73.1/10.6/23.1; 6.1/72.3/10.1/18.4 | 92.3, 91.4 | 91.85 |
| 4 → 8 | control interval | [-0.33, -0.45, 0.19, -0.44] | 12.4/56.2/24.8/6.5 | verified=True, mismatches=0 | 5.6/73.0/10.3/22.6; 5.2/62.9/9.3/22.5; 5.0/59.7/10.9/23.1; 5.8/61.5/9.9/27.3 | 90.2, 86.5, 86.0, 87.5 | 87.56 |
| 8 → 12 | healing normal (boosts none) | [-0.73, -0.18, 0.03, -0.63] | 7.0/74.0/12.8/6.2 | verified=True, mismatches=0 | 6.0/59.2/11.0/19.4; 4.4/60.0/9.1/21.2; 5.5/60.4/11.1/25.6; 6.3/65.5/9.8/28.9 | 83.3, 79.4, 86.8, 89.5 | 84.75 |
| 12 → 14 | control interval | [-0.29, -0.21, 0.44, -0.19] | 7.3/57.1/9.7/25.9 | verified=True, mismatches=0 | 5.7/63.9/10.6/31.4; 5.5/64.5/10.3/32.8 | 87.4, 89.9 | 88.64 |
| 14 → 16 | healing normal (boosts generalx0.5) | [-0.31, 0.03, 0.27, -0.28] | 6.0/66.7/11.7/15.7 | verified=True, mismatches=0 | 4.6/58.1/11.0/34.6; 4.7/53.5/9.6/32.1 | 82.9, 81.8 | 82.32 |
| 16 → 20 | control interval | [-0.26, -0.22, 0.25, -0.43] | 4.5/55.0/11.7/28.8 | verified=True, mismatches=0 | 4.9/61.6/10.9/29.9; 5.0/59.5/10.0/35.2; 4.2/58.9/10.4/37.4; 4.7/59.0/9.3/32.6 | 86.0, 87.5, 81.7, 84.1 | 84.81 |
| 20 → 24 | healing normal (boosts none) | [-0.33, -0.20, 0.18, -0.35] | 5.7/69.6/9.6/15.2 | verified=True, mismatches=0 | 5.9/64.1/10.9/31.4; 6.3/65.1/11.1/30.1; 6.5/64.9/12.8/29.9; 5.2/67.9/10.5/30.2 | 87.9, 89.8, 89.6, 91.1 | 89.61 |
| 24 → 28 | healing normal (boosts generalx0.5) | [-0.31, -0.13, 0.48, -0.28] | 7.5/74.0/12.4/6.1 | verified=True, mismatches=0 | 4.8/77.8/10.3/19.0; 5.4/68.8/10.0/16.8; 4.7/67.5/11.9/27.4; 5.1/63.0/9.4/24.8 | 91.9, 89.5, 88.1, 87.0 | 89.13 |
| 28 → 30 | control interval | [-0.34, -0.21, 0.42, -0.15] | 4.6/74.7/11.3/9.4 | verified=True, mismatches=0 | 5.5/66.7/10.2/21.7; 5.4/69.5/9.9/22.4 | 88.9, 90.6 | 89.73 |
| 30 → 32 | healing normal (boosts none) | [-0.37, -0.13, 0.49, -0.20] | 5.4/72.0/9.8/12.8 | verified=True, mismatches=0 | 4.6/71.2/11.2/24.1; 5.1/62.9/10.3/25.3 | 88.2, 88.0 | 88.09 |

Observation chaining: every transition's `next_obs` equals the next transition's `obs`: **True**. First observation (tick 0): [0.000, 1.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.050, 0.800, 0.100, 0.500, 0.000, 0.000, 0.000, 0.000, 0.250, 0.250, 0.250, 0.250, 0.000]. Final transition done = True.

