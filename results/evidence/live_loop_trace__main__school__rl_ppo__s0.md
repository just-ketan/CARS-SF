# Live coupled-loop trace: `main__school__rl_ppo__s0`

Scheduler `rl_ppo`, scenario `school`, data source `pcap`, 237 measured flow windows; contract: True.
Enforcement: {"decisions_applied": 13, "verified": 13, "failed": 0, "unverifiable": 0}.
Transitions: {"transitions": 12, "learnable": 12, "unverified": 0, "failed_enforcement": 0, "mean_reward": 86.2862}.
Policy learning: {}.

| decision tick → next | reason | action (log10 mult.) | allocation Mb/s (h/e/a/g) | kernel read-back | measured Mb/s per tick (h/e/a/g) | per-tick reward | transition reward |
|---|---|---|---|---|---|---|---|
| 0 → 3 | initial | [-0.00, 0.01, 0.11, -0.19] | 5.0/75.0/10.0/10.0 | verified=True, mismatches=0 | 1.5/18.3/3.1/3.5; 5.5/65.6/9.6/26.2; 5.9/70.0/10.5/26.8 | 1.9, 88.7, 91.6 | 60.75 |
| 3 → 5 | healing normal (boosts generalx0.5) | [0.03, 0.00, 0.11, -0.20] | 5.0/79.2/10.0/5.8 | verified=True, mismatches=0 | 6.1/68.2/10.0/19.3; 5.7/77.5/10.3/15.7 | 89.2, 93.5 | 91.35 |
| 5 → 9 | control interval | [0.03, -0.00, 0.12, -0.22] | 11.5/61.0/22.9/4.6 | verified=True, mismatches=0 | 5.2/63.0/9.4/18.9; 4.9/61.4/10.9/18.0; 5.9/70.0/9.9/24.2; 5.9/73.6/11.0/15.0 | 84.0, 85.2, 91.1, 91.5 | 87.94 |
| 9 → 10 | healing normal (boosts none) | [0.02, -0.00, 0.11, -0.18] | 6.5/71.4/11.9/10.2 | verified=True, mismatches=0 | 4.4/74.7/9.1/18.9 | 85.3 | 85.34 |
| 10 → 15 | control interval | [0.03, -0.01, 0.11, -0.18] | 5.2/74.2/10.0/10.6 | verified=True, mismatches=0 | 5.5/72.2/11.2/18.3; 6.3/69.5/9.7/11.8; 5.7/70.3/10.6/20.4; 5.5/72.1/10.4/19.6; 4.6/59.9/10.9/22.2 | 91.0, 88.5, 90.8, 91.5, 83.0 | 88.97 |
| 15 → 20 | control interval | [0.03, -0.00, 0.10, -0.18] | 5.4/71.6/12.7/10.3 | verified=True, mismatches=0 | 4.7/56.3/9.6/24.3; 4.9/64.6/10.9/26.1; 4.9/67.1/9.9/22.7; 4.1/72.1/10.5/24.1; 4.8/70.6/9.4/23.7 | 81.2, 88.4, 88.8, 85.7, 88.7 | 86.57 |
| 20 → 25 | control interval | [0.03, -0.01, 0.11, -0.19] | 4.7/75.4/9.2/10.7 | verified=True, mismatches=0 | 5.9/60.1/10.8/22.8; 6.3/62.0/11.0/27.7; 6.4/60.9/12.9/31.8; 5.2/64.9/10.5/22.5; 4.9/74.6/10.5/19.7 | 85.8, 87.9, 88.0, 88.5, 91.7 | 88.40 |
| 25 → 30 | control interval | [0.03, -0.01, 0.11, -0.18] | 6.1/71.6/12.1/10.2 | verified=True, mismatches=0 | 5.3/67.6/9.9/19.6; 4.8/65.6/12.1/23.6; 5.1/60.4/9.3/30.5; 5.5/65.7/10.2/25.2; 5.5/66.8/9.9/25.8 | 88.8, 87.4, 86.5, 89.3, 89.8 | 88.36 |
| 30 → 32 | control interval | [0.03, -0.01, 0.11, -0.19] | 5.3/74.4/9.8/10.5 | verified=True, mismatches=0 | 4.5/71.4/11.2/22.7; 5.1/72.6/10.4/24.2 | 87.2, 92.5 | 89.86 |
| 32 → 35 | healing normal (boosts generalx0.5) | [0.03, -0.01, 0.11, -0.19] | 5.8/76.5/11.8/5.9 | verified=True, mismatches=0 | 5.7/79.4/11.0/18.9; 6.0/77.6/10.0/15.9; 6.4/53.8/11.2/24.1 | 94.5, 93.6, 83.2 | 90.43 |
| 35 → 38 | control interval | [0.02, -0.00, 0.11, -0.18] | 7.7/72.5/13.8/6.0 | verified=True, mismatches=0 | 6.2/57.9/9.0/24.1; 5.6/67.9/11.1/26.3; 5.2/68.8/9.1/21.9 | 83.4, 90.5, 88.8 | 87.58 |
| 38 → 40 | healing normal (boosts none) | [0.03, -0.00, 0.11, -0.18] | 5.5/74.5/9.4/10.6 | verified=True, mismatches=0 | 5.2/70.0/10.8/22.1; 5.2/68.6/9.6/22.0 | 90.3, 89.5 | 89.89 |

Observation chaining: every transition's `next_obs` equals the next transition's `obs`: **True**. First observation (tick 0): [0.000, 1.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.050, 0.800, 0.100, 0.500, 0.000, 0.000, 0.000, 0.000, 0.250, 0.250, 0.250, 0.250, 0.000]. Final transition done = True.

