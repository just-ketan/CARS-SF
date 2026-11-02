# Live coupled-loop trace: `it_residual_online`

Scheduler `rl_residual_online`, scenario `disaster`, data source `pcap`, 165 measured flow windows; contract: True.
Enforcement: {"decisions_applied": 16, "verified": 16, "failed": 0, "unverifiable": 0}.
Transitions: {"transitions": 16, "learnable": 16, "unverified": 0, "failed_enforcement": 0, "mean_reward": 88.4978}.
Policy learning: {"algorithm": "online CEM on residual actions (live transitions)", "checkpoint": "/tmp/pytest-of-ketan/pytest-12/test_residual_online_rl_closed0/residual_online.json", "samples_this_run": 16, "updates_this_run": 4}.

| decision tick → next | reason | action (priority: log10 multipliers; residual: rate corrections) | allocation Mb/s (h/e/a/g) | kernel read-back | measured Mb/s per tick (h/e/a/g) | per-tick reward | transition reward |
|---|---|---|---|---|---|---|---|
| 0 → 2 | initial | [0.04, -0.04, 0.19, 0.03] | 93.8/40.7/5.2/58.3 | verified=True, mismatches=0 | 22.5/2.7/1.6/10.2; 92.4/4.4/4.8/25.9 | 26.5, 98.7 | 62.63 |
| 2 → 3 | healing normal (boosts generalx0.5) | [-0.16, 0.11, 0.39, 0.28] | 89.5/51.9/9.5/47.1 | verified=True, mismatches=0 | 95.6/4.5/5.3/19.3 | 97.4 | 97.37 |
| 3 → 5 | healing normal (boosts generalx0.5,healthcarex2) | [-0.21, -0.38, -0.19, 0.01] | 93.8/47.7/5.1/51.3 | verified=True, mismatches=0 | 95.7/4.3/5.0/15.3; 96.2/4.5/5.2/19.1 | 86.1, 88.7 | 87.37 |
| 5 → 6 | sla risk: healthcare loss 1.54% | [-0.70, -0.07, -0.37, -0.22] | 93.0/56.0/5.6/42.9 | verified=True, mismatches=0 | 94.9/4.4/4.6/22.3 | 97.5 | 97.47 |
| 6 → 8 | control interval | [-0.16, -0.09, 0.12, 0.31] | 93.2/48.5/5.8/50.5 | verified=True, mismatches=0 | 94.2/4.4/5.5/24.7; 95.6/4.4/5.1/16.4 | 98.3, 97.5 | 97.92 |
| 8 → 9 | sla risk: healthcare queue rising 13.9→20.2 ms | [-0.46, 0.14, -0.25, 0.12] | 97.7/53.5/1.2/45.5 | verified=True, mismatches=0 | 99.8/4.6/2.7/17.8 | 73.3 | 73.26 |
| 9 → 12 | control interval | [-0.19, 0.03, -0.28, -0.20] | 97.9/55.5/1.1/43.5 | verified=True, mismatches=0 | 98.6/5.0/1.9/19.5; 96.9/4.5/3.0/21.4; 100.0/4.4/2.0/9.9 | 82.6, 84.6, 77.2 | 81.48 |
| 12 → 15 | sla risk: healthcare queue rising 12.9→19.4 ms | [-0.55, 0.04, -0.38, -0.02] | 97.6/56.1/1.2/42.9 | unchanged (< 1 Mb/s) | 98.5/4.3/1.9/17.7; 98.3/4.8/2.5/13.1; 89.1/4.5/10.2/23.9 | 78.6, 78.4, 87.6 | 81.52 |
| 15 → 18 | control interval | [-0.47, 0.07, 0.09, 0.12] | 84.1/54.3/14.9/44.7 | verified=True, mismatches=0 | 81.0/4.3/17.2/10.7; 85.1/4.9/5.5/23.8; 87.4/4.5/5.0/10.5 | 85.9, 95.7, 93.4 | 91.66 |
| 18 → 20 | control interval | [-0.48, -0.04, 0.07, 0.40] | 77.7/50.6/21.3/48.4 | verified=True, mismatches=0 | 72.4/4.7/5.2/18.8; 78.7/4.4/4.7/12.8 | 83.0, 86.2 | 84.61 |
| 20 → 21 | healing normal (boosts healthcarex2) | [-0.60, 0.08, 0.21, 0.28] | 74.3/42.3/24.7/56.7 | verified=True, mismatches=0 | 94.0/4.3/5.4/20.6 | 97.8 | 97.75 |
| 21 → 22 | healing normal (boosts generalx0.5) | [-0.31, -0.05, 0.24, 0.47] | 84.6/48.2/14.3/50.8 | verified=True, mismatches=0 | 94.8/4.8/5.6/12.4 | 95.0 | 95.01 |
| 22 → 24 | healing normal (boosts generalx0.5,healthcarex2) | [-0.01, 0.06, -0.04, -0.06] | 93.9/57.9/5.1/41.1 | verified=True, mismatches=0 | 96.4/4.6/6.3/15.9; 96.1/4.3/5.3/12.6 | 85.6, 75.4 | 80.48 |
| 24 → 27 | sla risk: healthcare loss 2.13% | [-0.46, 0.05, 0.16, 0.41] | 84.5/54.4/14.4/44.6 | verified=True, mismatches=0 | 94.8/5.7/5.2/20.4; 95.0/4.5/5.0/7.4; 93.7/4.8/6.0/22.1 | 88.5, 94.4, 99.7 | 94.21 |
| 27 → 28 | control interval | [-0.39, 0.06, 0.16, 0.31] | 86.4/54.0/12.6/45.0 | verified=True, mismatches=0 | 95.2/4.4/4.7/12.6 | 95.5 | 95.52 |
| 28 → 30 | healing normal (boosts generalx0.5) | [-0.52, -0.06, 0.31, 0.33] | 82.7/52.7/16.3/46.3 | verified=True, mismatches=0 | 94.5/5.0/5.1/18.9; 95.3/5.1/4.9/10.9 | 99.0, 96.4 | 97.69 |

Observation chaining: every transition's `next_obs` equals the next transition's `obs`: **True**. First observation (tick 0): [0.000, 0.000, 0.000, 1.000, 0.000, 0.000, 0.000, 0.000, 0.900, 0.050, 0.050, 0.200, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000]. Final transition done = True.

