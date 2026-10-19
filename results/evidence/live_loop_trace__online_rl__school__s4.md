# Live coupled-loop trace: `online_rl__school__s4`

Scheduler `rl_online`, scenario `school`, data source `pcap`, 353 measured flow windows; contract: True.
Enforcement: {"decisions_applied": 22, "verified": 22, "failed": 0, "unverifiable": 0}.
Transitions: {"transitions": 21, "learnable": 21, "unverified": 0, "failed_enforcement": 0, "mean_reward": 86.806}.
Policy learning: {"algorithm": "online CEM on live transitions", "checkpoint": "/home/ketan/Desktop/CARS-SF/scheduler/models/cem_online.json", "samples_this_run": 21, "updates_this_run": 5}.

| decision tick → next | reason | action (log10 mult.) | allocation Mb/s (h/e/a/g) | kernel read-back | measured Mb/s per tick (h/e/a/g) | per-tick reward | transition reward |
|---|---|---|---|---|---|---|---|
| 0 → 5 | initial | [-0.39, -0.12, 0.83, 0.17] | 5.0/61.2/10.0/23.8 | verified=True, mismatches=0 | 1.7/15.0/3.4/7.0; 5.3/58.4/9.6/36.9; 6.1/57.8/10.3/24.0; 5.4/66.9/9.5/24.0; 5.0/63.7/10.5/25.4 | 22.6, 86.9, 85.3, 89.0, 88.4 | 74.41 |
| 5 → 6 | control interval | [-0.42, -0.09, 0.86, 0.22] | 11.3/46.6/22.6/19.4 | verified=True, mismatches=0 | 5.1/62.3/9.8/34.6 | 87.0 | 86.98 |
| 6 → 10 | healing normal (boosts generalx0.5) | [-0.43, -0.17, 0.77, 0.16] | 9.4/58.9/18.4/13.4 | verified=True, mismatches=0 | 6.0/57.9/11.0/26.8; 5.9/49.7/9.6/31.8; 5.7/55.6/10.8/38.9; 5.1/66.1/9.5/21.7 | 84.6, 81.8, 86.6, 88.2 | 85.30 |
| 10 → 15 | control interval | [-0.51, -0.12, 0.73, 0.11] | 5.6/71.4/10.1/12.9 | verified=True, mismatches=0 | 4.6/70.9/10.7/24.8; 6.0/72.0/9.6/25.0; 5.0/73.8/9.9/23.9; 5.7/51.6/10.1/24.6; 6.0/50.0/10.8/20.3 | 87.4, 91.7, 92.5, 82.0, 80.3 | 86.80 |
| 15 → 18 | control interval | [-0.47, -0.08, 0.82, 0.29] | 6.8/53.9/12.8/19.5 | verified=True, mismatches=0 | 6.0/57.0/9.5/25.6; 6.0/60.1/10.0/33.0; 6.9/61.6/9.2/34.1 | 82.9, 87.8, 87.4 | 86.05 |
| 18 → 20 | healing normal (boosts none) | [-0.44, 0.00, 0.74, 0.26] | 7.8/60.9/9.0/22.4 | verified=True, mismatches=0 | 6.5/58.3/10.9/32.0; 5.2/58.0/9.5/33.3 | 86.1, 86.1 | 86.08 |
| 20 → 25 | control interval | [-0.39, -0.06, 0.73, 0.20] | 6.1/60.9/10.6/22.4 | verified=True, mismatches=0 | 5.2/59.1/11.4/29.5; 5.4/73.1/10.7/19.5; 4.4/67.9/11.2/25.6; 5.7/54.8/10.2/31.9; 5.1/62.5/9.9/24.0 | 86.7, 92.0, 85.6, 85.1, 87.5 | 87.38 |
| 25 → 28 | control interval | [-0.46, -0.06, 0.71, 0.23] | 5.6/57.9/13.9/22.7 | verified=True, mismatches=0 | 4.9/62.6/9.7/20.9; 4.9/62.8/11.3/31.4; 4.5/63.4/10.3/34.3 | 85.4, 88.3, 86.0 | 86.59 |
| 28 → 30 | healing normal (boosts generalx0.5) | [-0.46, -0.07, 0.74, 0.17] | 4.5/72.0/10.2/13.3 | verified=True, mismatches=0 | 6.1/58.8/10.2/30.4; 6.1/60.3/10.0/23.4 | 85.4, 86.4 | 85.86 |
| 30 → 34 | control interval | [-0.49, -0.10, 0.77, 0.23] | 5.8/59.2/12.3/22.7 | verified=True, mismatches=0 | 6.2/62.1/10.2/29.6; 6.7/63.1/10.7/20.4; 6.5/64.8/11.0/22.9; 6.4/62.0/10.1/34.1 | 87.0, 87.3, 88.5, 88.9 | 87.94 |
| 34 → 35 | healing normal (boosts none) | [-0.52, -0.02, 0.80, 0.19] | 7.8/61.7/10.2/20.4 | verified=True, mismatches=0 | 6.2/62.0/11.5/32.6 | 88.2 | 88.24 |
| 35 → 37 | control interval | [-0.43, -0.11, 0.81, 0.25] | 7.1/55.7/11.6/25.6 | verified=True, mismatches=0 | 6.0/62.1/9.7/28.5; 5.8/63.6/11.4/33.7 | 87.0, 89.6 | 88.32 |
| 37 → 40 | healing normal (boosts generalx0.5) | [-0.41, 0.01, 0.80, 0.15] | 6.0/70.6/12.9/10.5 | verified=True, mismatches=0 | 6.0/60.7/9.9/30.1; 5.0/68.4/11.1/25.4; 5.5/69.9/9.6/23.0 | 85.8, 90.7, 90.4 | 88.96 |
| 40 → 43 | control interval | [-0.51, -0.03, 0.72, 0.23] | 6.6/70.0/10.1/13.2 | verified=True, mismatches=0 | 6.5/69.3/11.2/23.3; 7.0/70.6/9.4/25.4; 6.9/70.1/11.0/25.0 | 90.4, 90.7, 91.4 | 90.85 |
| 43 → 45 | healing normal (boosts none) | [-0.48, -0.02, 0.73, 0.18] | 8.7/59.3/12.8/19.2 | verified=True, mismatches=0 | 6.5/64.7/9.4/22.1; 6.3/62.4/10.4/33.4 | 86.4, 89.0 | 87.71 |
| 45 → 46 | control interval | [-0.53, -0.12, 0.87, 0.19] | 6.8/59.0/10.4/23.9 | verified=True, mismatches=0 | 5.4/61.0/9.9/35.6 | 88.0 | 88.04 |
| 46 → 50 | healing normal (boosts generalx0.5) | [-0.44, -0.02, 0.84, 0.26] | 5.7/68.8/11.8/13.7 | verified=True, mismatches=0 | 5.6/68.4/10.9/27.1; 4.7/64.4/9.7/24.2; 4.4/62.8/11.6/29.0; 4.6/69.9/9.6/23.9 | 89.8, 85.5, 84.1, 87.4 | 86.69 |
| 50 → 55 | control interval | [-0.43, -0.12, 0.77, 0.22] | 4.0/68.9/11.4/15.7 | verified=True, mismatches=0 | 5.2/72.0/10.7/25.1; 5.3/74.1/9.9/25.0; 4.3/56.4/10.8/27.8; 5.6/59.2/9.7/31.0; 5.0/62.7/10.1/27.6 | 92.1, 93.2, 79.9, 86.7, 88.2 | 88.01 |
| 55 → 58 | control interval | [-0.41, -0.04, 0.85, 0.12] | 5.1/71.7/10.2/13.0 | verified=True, mismatches=0 | 6.2/65.2/9.4/22.9; 5.3/70.1/11.0/22.7; 5.1/66.8/9.2/25.7 | 87.5, 91.1, 88.7 | 89.07 |
| 58 → 59 | healing normal (boosts none) | [-0.49, 0.04, 0.77, 0.29] | 6.7/59.2/12.7/21.4 | verified=True, mismatches=0 | 5.3/65.5/10.9/31.3 | 88.9 | 88.90 |
| 59 → 60 | healing normal (boosts generalx0.5) | [-0.46, -0.11, 0.85, 0.10] | 6.0/70.2/11.7/12.1 | verified=True, mismatches=0 | 5.2/59.2/9.2/30.9 | 84.8 | 84.76 |

Observation chaining: every transition's `next_obs` equals the next transition's `obs`: **True**. First observation (tick 0): [0.000, 1.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.050, 0.800, 0.100, 0.500, 0.000, 0.000, 0.000, 0.000, 0.250, 0.250, 0.250, 0.250, 0.000]. Final transition done = True.

