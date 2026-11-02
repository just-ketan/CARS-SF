# Synthetic path trace (2026-10-20T10:11:44)

## 1. Seeded RSNSD generation → contract

* `dataset.rsnsd.generate(30, seed=7)`: 540 rows × 94 columns, 18 scenarios; regenerated with the same seed → identical: **True**
* `features.contract.validate(df, 'synthetic_rsnsd')` (rsnsd-contract-2.0): ok = **True**, errors = []
* class counts: {'agriculture': 91, 'education': 109, 'general': 155, 'healthcare': 185}

## 2. SliceNet inference (synthetic baseline model, confidence gate 0.5)

Model `classification/models/slicenet_baseline.pkl`, 51 features in training order; rows from scenario `Congestion` (newly generated with seed 7, not the training file).

| flow | true class | predicted | confidence | abstained | reason |
|---|---|---|---|---|---|
| 3a1ed8f1 | agriculture | agriculture | 0.9855 | False |  |
| f2bcde3d | general | general | 0.9997 | False |  |
| 0944e14c | education | general | 0.9833 | False |  |
| 6694b89e | general | general | 0.9119 | False |  |
| 5214c96a | agriculture | agriculture | 0.945 | False |  |
| 1be917e5 | education | education | 1.0 | False |  |
| 0bf895d7 | healthcare | healthcare | 1.0 | False |  |
| dd986619 | healthcare | healthcare | 0.9544 | False |  |

## 3. RL loop in the simulator (deployed PPO, test seed 1000, context disaster)

Observation layout: 8 context one-hot · 4 demand/C · 4 backlog/(C·0.1 s) · 4 allocation/C · on_backup (21 floats). Action: log10 priority multipliers in [−1, 1].

### step 0
* s_t demand/C [0.900, 0.050, 0.050, 0.200], backlog [0.000, 0.000, 0.000, 0.000], alloc/C [0.250, 0.250, 0.250, 0.250], on_backup 0
* a_t [-0.533, 0.237, 0.229, -0.025] → multipliers [0.29, 1.73, 1.69, 0.94]
* allocation (Mb/s) {"healthcare": 70.0, "education": 5.0, "agriculture": 5.0, "general": 20.0}
* delay (ms) {"healthcare": 108.0, "education": 28.0, "agriculture": 8.0, "general": 28.0}, satisfaction {"healthcare": 0.7778, "education": 1.0, "agriculture": 1.0, "general": 1.0}
* r_t = 70.323 = satisfaction +82.906 + sla -10.000 + loss -2.583 + starvation -0.000 + reallocation -0.000 + idle -0.000
* s_t+1 demand/C [0.857, 0.046, 0.063, 0.259], backlog [0.700, 0.000, 0.000, 0.000], alloc/C [0.700, 0.050, 0.050, 0.200]

### step 1
* s_t demand/C [0.857, 0.046, 0.063, 0.259], backlog [0.700, 0.000, 0.000, 0.000], alloc/C [0.700, 0.050, 0.050, 0.200], on_backup 0
* a_t [-0.714, 0.320, 0.305, 0.026] → multipliers [0.19, 2.09, 2.02, 1.06]
* allocation (Mb/s) {"healthcare": 63.2, "education": 4.6, "agriculture": 6.3, "general": 25.9}
* delay (ms) {"healthcare": 108.0, "education": 28.0, "agriculture": 8.0, "general": 28.2}, satisfaction {"healthcare": 0.7377, "education": 1.0, "agriculture": 1.0, "general": 1.0}
* r_t = 65.808 = satisfaction +79.824 + sla -10.000 + loss -3.299 + starvation -0.000 + reallocation -0.717 + idle -0.000
* s_t+1 demand/C [0.700, 0.049, 0.059, 0.215], backlog [0.632, 0.000, 0.000, 0.001], alloc/C [0.632, 0.046, 0.063, 0.259]

### step 2
* s_t demand/C [0.700, 0.049, 0.059, 0.215], backlog [0.632, 0.000, 0.000, 0.001], alloc/C [0.632, 0.046, 0.063, 0.259], on_backup 0
* a_t [-0.662, 0.298, 0.281, 0.021] → multipliers [0.22, 1.99, 1.91, 1.05]
* allocation (Mb/s) {"healthcare": 67.7, "education": 4.9, "agriculture": 5.9, "general": 21.5}
* delay (ms) {"healthcare": 108.0, "education": 28.0, "agriculture": 10.7, "general": 29.1}, satisfaction {"healthcare": 0.9673, "education": 1.0, "agriculture": 0.9995, "general": 0.9998}
* r_t = 86.609 = satisfaction +97.478 + sla -10.000 + loss -0.393 + starvation -0.000 + reallocation -0.476 + idle -0.000
* s_t+1 demand/C [0.894, 0.039, 0.063, 0.168], backlog [0.677, 0.000, 0.002, 0.002], alloc/C [0.677, 0.049, 0.059, 0.215]

### step 3
* s_t demand/C [0.894, 0.039, 0.063, 0.168], backlog [0.677, 0.000, 0.002, 0.002], alloc/C [0.677, 0.049, 0.059, 0.215], on_backup 0
* a_t [-0.711, 0.315, 0.301, 0.030] → multipliers [0.19, 2.07, 2.00, 1.07]
* allocation (Mb/s) {"healthcare": 73.1, "education": 3.9, "agriculture": 6.3, "general": 16.8}
* delay (ms) {"healthcare": 108.0, "education": 28.0, "agriculture": 12.1, "general": 28.4}, satisfaction {"healthcare": 0.817, "education": 1.0, "agriculture": 0.9997, "general": 1.0}
* r_t = 73.069 = satisfaction +85.918 + sla -10.000 + loss -2.273 + starvation -0.000 + reallocation -0.576 + idle -0.000
* s_t+1 demand/C [0.776, 0.037, 0.059, 0.163], backlog [0.731, 0.000, 0.003, 0.001], alloc/C [0.731, 0.039, 0.063, 0.168]

### step 4
* s_t demand/C [0.776, 0.037, 0.059, 0.163], backlog [0.731, 0.000, 0.003, 0.001], alloc/C [0.731, 0.039, 0.063, 0.168], on_backup 0
* a_t [-0.701, 0.313, 0.296, 0.033] → multipliers [0.20, 2.05, 1.98, 1.08]
* allocation (Mb/s) {"healthcare": 74.1, "education": 3.6, "agriculture": 5.9, "general": 16.3}
* delay (ms) {"healthcare": 108.0, "education": 30.3, "agriculture": 14.1, "general": 28.0}, satisfaction {"healthcare": 0.9551, "education": 0.9995, "agriculture": 0.9997, "general": 1.0}
* r_t = 85.874 = satisfaction +96.538 + sla -10.000 + loss -0.558 + starvation -0.000 + reallocation -0.106 + idle -0.000
* s_t+1 demand/C [0.991, 0.038, 0.060, 0.128], backlog [0.741, 0.001, 0.004, 0.000], alloc/C [0.741, 0.036, 0.059, 0.163]

### step 5
* s_t demand/C [0.991, 0.038, 0.060, 0.128], backlog [0.741, 0.001, 0.004, 0.000], alloc/C [0.741, 0.036, 0.059, 0.163], on_backup 1
* a_t [-0.754, 0.323, 0.352, 0.028] → multipliers [0.18, 2.10, 2.25, 1.07]
* allocation (Mb/s) {"healthcare": 77.4, "education": 3.8, "agriculture": 6.0, "general": 12.8}
* delay (ms) {"healthcare": 108.0, "education": 31.1, "agriculture": 10.3, "general": 28.0}, satisfaction {"healthcare": 0.7814, "education": 0.9998, "agriculture": 1.0, "general": 1.0}
* r_t = 70.106 = satisfaction +83.181 + sla -10.000 + loss -2.725 + starvation -0.000 + reallocation -0.350 + idle -0.000
* s_t+1 demand/C [1.058, 0.043, 0.052, 0.181], backlog [0.774, 0.001, 0.001, 0.000], alloc/C [0.774, 0.038, 0.060, 0.128]

