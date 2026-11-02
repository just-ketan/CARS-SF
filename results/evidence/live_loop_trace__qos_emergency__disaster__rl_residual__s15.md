# Live coupled-loop trace: `qos_emergency__disaster__rl_residual__s15`

Scheduler `rl_residual`, scenario `disaster`, data source `pcap`, 225 measured flow windows; contract: True.
Enforcement: {"decisions_applied": 13, "verified": 13, "failed": 0, "unverifiable": 0}.
Transitions: {"transitions": 13, "learnable": 13, "unverified": 0, "failed_enforcement": 0, "mean_reward": 79.6852}.
Policy learning: {}.

| decision tick → next | reason | action (priority: log10 multipliers; residual: rate corrections) | allocation Mb/s (h/e/a/g) | kernel read-back | measured Mb/s per tick (h/e/a/g) | per-tick reward | transition reward |
|---|---|---|---|---|---|---|---|
| 0 → 2 | initial | [0.11, 0.03, -0.01, -0.02] | 97.0/41.6/2.0/57.4 | verified=True, mismatches=0 | 19.2/3.3/1.4/16.0; 98.1/4.6/3.2/9.5 | 26.7, 82.0 | 54.34 |
| 2 → 3 | healing normal (boosts generalx0.5) | [0.17, 0.17, 0.06, -0.12] | 94.2/55.8/4.8/43.2 | verified=True, mismatches=0 | 94.1/4.7/5.7/46.4 | 87.3 | 87.28 |
| 3 → 5 | healing normal (boosts generalx0.5,healthcarex2) | [0.17, 0.18, 0.06, -0.14] | 94.2/56.0/4.8/43.0 | unchanged (< 1 Mb/s) | 94.0/4.5/6.6/1.7; 91.6/4.4/5.4/28.7 | 61.4, 99.1 | 80.24 |
| 5 → 8 | control interval | [0.18, 0.18, 0.05, -0.14] | 89.3/55.1/9.7/43.9 | verified=True, mismatches=0 | 93.3/4.4/5.1/3.4; 94.3/4.5/5.1/27.5; 81.5/4.9/4.8/0.3 | 80.4, 99.2, 64.2 | 81.28 |
| 8 → 9 | healing normal (boosts healthcarex2) | [0.18, 0.18, 0.06, -0.14] | 93.8/47.5/5.2/51.5 | verified=True, mismatches=0 | 79.8/4.5/5.6/29.2 | 89.4 | 89.37 |
| 9 → 10 | healing normal (boosts none) | [0.18, 0.17, 0.04, -0.14] | 94.0/44.4/5.0/54.6 | verified=True, mismatches=0 | 89.0/4.7/4.9/0.1 | 70.5 | 70.51 |
| 10 → 15 | control interval | [0.18, 0.17, 0.04, -0.13] | 94.1/47.7/4.9/51.3 | verified=True, mismatches=0 | 82.5/4.5/5.6/42.1; 74.8/6.1/5.1/2.0; 74.7/5.4/5.5/29.3; 80.0/5.0/5.1/3.5; 89.8/4.5/5.5/27.0 | 92.5, 59.5, 86.9, 84.7, 99.0 | 84.55 |
| 15 → 20 | healing normal (boosts generalx0.5) | [0.18, 0.17, 0.04, -0.14] | 92.9/55.0/6.1/44.0 | verified=True, mismatches=0 | 95.7/4.5/5.0/3.2; 93.1/4.5/5.3/29.8; 85.2/4.5/4.8/8.4; 94.0/4.6/5.3/32.8; 96.1/4.4/4.9/7.5 | 91.9, 99.2, 90.4, 99.3, 94.0 | 94.96 |
| 20 → 24 | healing normal (boosts generalx0.5,healthcarex2) | [0.18, 0.18, 0.04, -0.14] | 94.1/58.5/4.9/40.5 | verified=True, mismatches=0 | 94.7/4.9/5.6/34.8; 92.8/20.3/4.7/4.9; 94.5/5.0/5.6/30.9; 96.3/4.3/4.9/5.7 | 99.2, 93.7, 99.9, 82.9 | 93.91 |
| 24 → 25 | sla risk: healthcare loss 1.35% | [0.18, 0.18, 0.05, -0.14] | 98.0/59.6/1.0/39.4 | verified=True, mismatches=0 | 99.4/4.5/2.9/27.0 | 74.5 | 74.47 |
| 25 → 30 | control interval | [0.17, 0.18, 0.07, -0.14] | 98.0/56.3/1.0/42.7 | verified=True, mismatches=0 | 100.5/23.4/1.9/2.7; 98.1/4.5/1.5/38.1; 98.3/4.6/2.2/2.4; 99.0/4.4/1.9/27.1; 99.0/5.9/2.2/8.2 | 65.8, 81.1, 75.5, 79.9, 77.1 | 75.87 |
| 30 → 35 | control interval | [0.16, 0.18, 0.07, -0.13] | 98.0/60.6/1.0/38.4 | verified=True, mismatches=0 | 99.0/4.5/2.4/30.7; 98.6/4.5/2.3/22.0; 99.7/4.4/2.9/29.4; 99.7/6.4/3.0/2.2; 99.9/4.4/2.9/29.8 | 79.5, 79.2, 79.8, 64.4, 69.0 | 74.37 |
| 35 → 40 | control interval | [0.16, 0.18, 0.07, -0.13] | 98.0/53.4/1.0/45.6 | verified=True, mismatches=0 | 98.6/5.2/3.0/1.2; 92.4/4.6/8.9/28.0; 87.8/4.7/12.0/11.0; 87.9/5.8/12.9/35.1; 94.7/5.3/4.9/1.1 | 52.8, 87.5, 83.6, 87.9, 62.0 | 74.76 |

Observation chaining: every transition's `next_obs` equals the next transition's `obs`: **True**. First observation (tick 0): [0.000, 0.000, 0.000, 1.000, 0.000, 0.000, 0.000, 0.000, 0.900, 0.050, 0.050, 0.200, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000]. Final transition done = True.

