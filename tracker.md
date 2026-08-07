# Project Progress Tracker

Last updated: 2026-08-07

---

# Phase 0 — Architectural Consolidation

- [x] Fix broken imports (demo.py, run_all_contexts.py)
- [x] Create unified ARCHITECTURE.md, DATASET_DESIGN.md, RL_DESIGN.md
- [x] Extract shared registries (applications.yaml, scenarios.yaml, features.yaml)
- [x] Create core/ module with interfaces and orchestrator
- [x] Document RSNSD v1 freeze policy in README
- [x] Reconcile tracker with actual progress

Status: **Complete**

---

# Phase 1 — Mininet Telemetry Pipeline

- [x] Canonical topology (topology/rural_topology.py)
- [x] Profile-driven traffic (traffic/orchestrator.py)
- [x] Real telemetry (telemetry/collector.py — OVS, tc, PCAP, psutil)
- [x] PCAP feature extraction (features/extractor.py)
- [x] Dataset builder (dataset/builder.py)
- [x] Validation framework (validation/validator.py)
- [x] Unified orchestrator (core/orchestrator.py)
- [x] Entry point (run_experiment.py)

Status: **Complete**

---

# Phase 2 — Network Enforcement (Closed Loop)

- [x] HTB queue creation per service class
- [x] Real tc bandwidth enforcement (slicing/qos_enforcer.py)
- [x] IP-based flow classification filters
- [x] Orchestrator QoS integration (--apply-qos flag)
- [x] Bottleneck link on rural→edge

Status: **Complete**

---

# Phase 3 — SliceNet Classifier

- [x] SliceNet architecture (classification/slicenet.py)
- [x] Training script (classification/train.py)
- [x] Label leakage columns excluded from ML features
- [x] Bootstrap training on RSNSD v1 supported
- [x] Mininet dataset retraining supported (--mininet flag)

Status: **Complete**

---

# Phase 4 — RL Scheduler

- [x] Gym-compatible environment (scheduler/env.py)
- [x] Rule-based baseline (scheduler/baseline.py)
- [x] RL agent with policy training (scheduler/agent.py)
- [x] Training script (scheduler/train.py)

Status: **Complete**

---

# Phase 5 — Monitoring and Self-Healing

- [x] Continuous monitoring (monitoring/monitor.py)
- [x] Failure detection (self_healing/detector.py)
- [x] Recovery planner (self_healing/recovery.py)
- [x] Fault injection (self_healing/injector.py)

Status: **Complete**

---

# Phase 6 — Deployment and Thesis

- [x] Edge server deployment config (deployment/edge_config.yaml)
- [x] Reproducible experiment runner (experiments/run_reproducible.py)
- [x] Open5GS/UERANSIM documented as optional extensions
- [ ] LaTeX report update with new experimental results
- [ ] Full Mininet end-to-end validation run

Status: **90%**

---

# Legacy Components

| Component | Status |
|-----------|--------|
| RSNSD/ (v1 synthetic) | Frozen — bootstrap only |
| MininetSims/ | Deprecated — merged into core pipeline |
| RSNSDv2/ | Deprecated — merged into core/orchestrator.py |
| slicing/ (allocation prototype) | Preserved and integrated |
