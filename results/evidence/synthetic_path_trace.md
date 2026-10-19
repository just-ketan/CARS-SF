# Synthetic path trace (2026-10-19T00:14:35)

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
* a_t [-0.249, 0.080, 0.115, -0.123] → multipliers [0.56, 1.20, 1.30, 0.75]
* allocation (Mb/s) {"healthcare": 79.1, "education": 5.0, "agriculture": 5.0, "general": 10.9}
* delay (ms) {"healthcare": 108.0, "education": 28.0, "agriculture": 8.0, "general": 128.0}, satisfaction {"healthcare": 0.8788, "education": 1.0, "agriculture": 1.0, "general": 0.5455}
* r_t = 70.339 = satisfaction +87.179 + sla -10.000 + loss -6.840 + starvation -0.000 + reallocation -0.000 + idle -0.000
* s_t+1 demand/C [0.857, 0.046, 0.063, 0.259], backlog [0.791, 0.000, 0.000, 0.109], alloc/C [0.791, 0.050, 0.050, 0.109]

### step 1
* s_t demand/C [0.857, 0.046, 0.063, 0.259], backlog [0.791, 0.000, 0.000, 0.109], alloc/C [0.791, 0.050, 0.050, 0.109], on_backup 0
* a_t [-0.369, 0.134, 0.163, -0.099] → multipliers [0.43, 1.36, 1.46, 0.80]
* allocation (Mb/s) {"healthcare": 75.0, "education": 4.6, "agriculture": 6.3, "general": 14.1}
* delay (ms) {"healthcare": 108.0, "education": 28.0, "agriculture": 8.0, "general": 128.0}, satisfaction {"healthcare": 0.876, "education": 1.0, "agriculture": 1.0, "general": 0.5426}
* r_t = 69.258 = satisfaction +86.947 + sla -10.000 + loss -7.248 + starvation -0.000 + reallocation -0.441 + idle -0.000
* s_t+1 demand/C [0.700, 0.049, 0.059, 0.215], backlog [0.750, 0.000, 0.000, 0.141], alloc/C [0.750, 0.046, 0.063, 0.141]

### step 2
* s_t demand/C [0.700, 0.049, 0.059, 0.215], backlog [0.750, 0.000, 0.000, 0.141], alloc/C [0.750, 0.046, 0.063, 0.141], on_backup 0
* a_t [-0.346, 0.128, 0.151, -0.094] → multipliers [0.45, 1.34, 1.42, 0.81]
* allocation (Mb/s) {"healthcare": 70.0, "education": 4.9, "agriculture": 5.9, "general": 19.2}
* delay (ms) {"healthcare": 108.0, "education": 28.0, "agriculture": 10.7, "general": 128.0}, satisfaction {"healthcare": 1.0, "education": 1.0, "agriculture": 0.9995, "general": 0.8933}
* r_t = 87.343 = satisfaction +99.175 + sla -10.000 + loss -1.291 + starvation -0.000 + reallocation -0.541 + idle -0.000
* s_t+1 demand/C [0.894, 0.039, 0.063, 0.168], backlog [0.700, 0.000, 0.002, 0.192], alloc/C [0.700, 0.049, 0.059, 0.192]

### step 3
* s_t demand/C [0.894, 0.039, 0.063, 0.168], backlog [0.700, 0.000, 0.002, 0.192], alloc/C [0.700, 0.049, 0.059, 0.192], on_backup 0
* a_t [-0.360, 0.128, 0.157, -0.098] → multipliers [0.44, 1.34, 1.44, 0.80]
* allocation (Mb/s) {"healthcare": 75.9, "education": 3.9, "agriculture": 6.3, "general": 14.0}
* delay (ms) {"healthcare": 108.0, "education": 28.0, "agriculture": 12.1, "general": 128.0}, satisfaction {"healthcare": 0.8485, "education": 1.0, "agriculture": 0.9997, "general": 0.832}
* r_t = 72.367 = satisfaction +87.052 + sla -10.000 + loss -4.055 + starvation -0.000 + reallocation -0.629 + idle -0.000
* s_t+1 demand/C [0.776, 0.037, 0.059, 0.163], backlog [0.759, 0.000, 0.003, 0.140], alloc/C [0.759, 0.039, 0.063, 0.140]

### step 4
* s_t demand/C [0.776, 0.037, 0.059, 0.163], backlog [0.759, 0.000, 0.003, 0.140], alloc/C [0.759, 0.039, 0.063, 0.140], on_backup 0
* a_t [-0.356, 0.129, 0.154, -0.092] → multipliers [0.44, 1.35, 1.42, 0.81]
* allocation (Mb/s) {"healthcare": 76.3, "education": 3.6, "agriculture": 5.9, "general": 14.1}
* delay (ms) {"healthcare": 108.0, "education": 30.7, "agriculture": 14.3, "general": 128.0}, satisfaction {"healthcare": 0.9834, "education": 0.9995, "agriculture": 0.9996, "general": 0.8654}
* r_t = 85.733 = satisfaction +97.680 + sla -10.000 + loss -1.886 + starvation -0.000 + reallocation -0.061 + idle -0.000
* s_t+1 demand/C [0.991, 0.038, 0.060, 0.128], backlog [0.763, 0.001, 0.004, 0.141], alloc/C [0.763, 0.036, 0.059, 0.141]

### step 5
* s_t demand/C [0.991, 0.038, 0.060, 0.128], backlog [0.763, 0.001, 0.004, 0.141], alloc/C [0.763, 0.036, 0.059, 0.141], on_backup 1
* a_t [-0.389, 0.142, 0.185, -0.119] → multipliers [0.41, 1.39, 1.53, 0.76]
* allocation (Mb/s) {"healthcare": 77.4, "education": 3.8, "agriculture": 6.0, "general": 12.8}
* delay (ms) {"healthcare": 108.0, "education": 31.4, "agriculture": 10.6, "general": 128.0}, satisfaction {"healthcare": 0.7814, "education": 0.9998, "agriculture": 1.0, "general": 1.0}
* r_t = 70.299 = satisfaction +83.181 + sla -10.000 + loss -2.751 + starvation -0.000 + reallocation -0.131 + idle -0.000
* s_t+1 demand/C [1.058, 0.043, 0.052, 0.181], backlog [0.774, 0.001, 0.002, 0.128], alloc/C [0.774, 0.038, 0.060, 0.128]

