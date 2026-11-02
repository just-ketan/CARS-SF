# Live coupled-loop trace: `qos_emergency__medical_emergency__qos_adaptive__s15`

Scheduler `qos_adaptive`, scenario `medical_emergency`, data source `pcap`, 214 measured flow windows; contract: True.
Enforcement: {"decisions_applied": 13, "verified": 13, "failed": 0, "unverifiable": 0}.
Transitions: {"transitions": 15, "learnable": 15, "unverified": 0, "failed_enforcement": 0, "mean_reward": 74.4264}.
Policy learning: {}.

| decision tick → next | reason | action (priority: log10 multipliers; residual: rate corrections) | allocation Mb/s (h/e/a/g) | kernel read-back | measured Mb/s per tick (h/e/a/g) | per-tick reward | transition reward |
|---|---|---|---|---|---|---|---|
| 0 → 2 | initial | [0.00, 0.00, 0.00, 0.00] | 98.0/46.8/1.0/52.2 | verified=True, mismatches=0 | 18.7/3.2/1.4/9.7; 101.2/4.6/2.7/0.0 | 23.5, 60.6 | 42.06 |
| 2 → 3 | healing normal (boosts generalx0.5) + headroom {'agriculture': 1.265} | [0.00, 0.00, 0.00, 0.00] | 98.0/60.5/1.0/38.5 | verified=True, mismatches=0 | 97.4/4.7/2.0/18.7 | 83.3 | 83.35 |
| 3 → 5 | healing normal (boosts generalx0.5,healthcarex2) + headroom {'agriculture': 1.455} | [0.00, 0.00, 0.00, 0.00] | 98.0/60.5/1.0/38.5 | unchanged (< 1 Mb/s) | 98.6/4.5/2.0/3.6; 99.0/4.4/1.9/31.2 | 80.2, 82.1 | 81.18 |
| 5 → 7 | control interval + headroom {'agriculture': 1.6} | [0.00, 0.00, 0.00, 0.00] | 95.7/58.2/3.3/40.8 | verified=True, mismatches=0 | 96.8/4.5/3.8/1.6; 97.1/4.5/3.7/15.4 | 80.9, 85.5 | 83.17 |
| 7 → 9 | sla risk: agriculture loss 20.14% | [0.00, 0.00, 0.00, 0.00] | 98.0/57.1/1.0/41.9 | verified=True, mismatches=0 | 94.8/4.7/4.9/0.1; 82.4/4.7/18.0/17.1 | 61.1, 78.4 | 69.71 |
| 9 → 10 | healing normal (boosts generalx0.5) | [0.00, 0.00, 0.00, 0.00] | 95.0/58.1/4.0/40.9 | verified=True, mismatches=0 | 93.0/4.7/7.4/1.3 | 82.4 | 82.38 |
| 10 → 13 | control interval | [0.00, 0.00, 0.00, 0.00] | 97.5/62.4/1.5/36.6 | verified=True, mismatches=0 | 89.1/4.5/5.6/13.8; 78.8/5.9/5.1/0.0; 78.8/5.5/5.5/13.9 | 83.1, 59.6, 85.7 | 76.11 |
| 13 → 14 | sla risk: healthcare queue rising 7.6→18.8 ms | [0.00, 0.00, 0.00, 0.00] | 85.7/61.0/13.3/38.0 | verified=True, mismatches=0 | 84.6/5.0/5.1/0.1 | 63.8 | 63.75 |
| 14 → 15 | healing normal (boosts none) | [0.00, 0.00, 0.00, 0.00] | 93.3/49.1/5.7/49.9 | verified=True, mismatches=0 | 92.0/4.5/5.5/13.7 | 94.9 | 94.87 |
| 15 → 20 | healing normal (boosts generalx0.5) | [0.00, 0.00, 0.00, 0.00] | 93.1/61.7/5.8/37.3 | verified=True, mismatches=0 | 95.5/4.4/5.0/0.4; 94.7/4.7/5.3/15.4; 95.7/4.5/4.8/0.2; 94.1/4.6/5.3/13.7; 96.5/4.2/4.9/0.0 | 72.6, 99.3, 73.8, 98.8, 73.3 | 83.57 |
| 20 → 23 | healing normal (boosts generalx0.5,healthcarex2) + headroom {'agriculture': 1.552} | [0.00, 0.00, 0.00, 0.00] | 98.0/63.2/1.0/35.8 | verified=True, mismatches=0 | 98.6/5.0/2.8/27.0; 99.5/20.3/2.0/3.4; 100.0/4.9/1.0/13.7 | 86.3, 81.5, 72.9 | 80.23 |
| 23 → 25 | sla risk: healthcare loss 1.25% + headroom {'agriculture': 1.6} | [0.00, 0.00, 0.00, 0.00] | 98.0/60.3/1.0/38.7 | verified=True, mismatches=0 | 100.4/4.2/2.8/0.0; 101.6/4.7/1.9/15.6 | 57.5, 71.2 | 64.35 |
| 25 → 30 | control interval + headroom {'healthcare': 1.265} | [0.00, 0.00, 0.00, 0.00] | 98.0/60.0/1.0/39.0 | unchanged (< 1 Mb/s) | 99.2/18.8/1.9/0.0; 98.4/8.9/2.0/17.2; 98.6/4.6/3.1/0.2; 98.9/4.6/2.8/13.8; 99.4/5.9/2.2/2.6 | 46.2, 81.8, 57.7, 81.0, 77.6 | 68.85 |
| 30 → 35 | control interval | [0.00, 0.00, 0.00, 0.00] | 98.0/64.2/1.0/34.8 | verified=True, mismatches=0 | 100.4/4.4/3.8/13.7; 98.2/4.5/2.8/0.1; 100.2/4.5/2.9/16.2; 100.2/5.7/4.0/2.0; 99.1/5.1/3.7/14.0 | 71.0, 54.6, 70.1, 67.7, 71.0 | 66.87 |
| 35 → 40 | control interval + headroom {'healthcare': 1.455} | [0.00, 0.00, 0.00, 0.00] | 98.0/60.9/1.0/38.1 | verified=True, mismatches=0 | 98.8/4.2/3.0/10.9; 98.4/5.6/3.9/15.9; 98.3/4.7/4.7/0.2; 99.1/5.7/4.6/19.5; 98.4/5.3/4.2/3.3 | 79.4, 81.4, 57.6, 83.0, 78.5 | 75.96 |

Observation chaining: every transition's `next_obs` equals the next transition's `obs`: **True**. First observation (tick 0): [0.000, 0.000, 0.000, 0.000, 1.000, 0.000, 0.000, 0.000, 0.950, 0.050, 0.050, 0.100, 0.000, 0.000, 0.000, 0.000, 0.250, 0.250, 0.250, 0.250, 0.000]. Final transition done = True.

