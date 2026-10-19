# Project Progress Tracker

Status as of October 2026. Evidence for each item: [docs/thesis/results.md](docs/thesis/results.md).

## Phase 0 — Literature review
- [x] SliceNet paper
- [x] Rural slicing papers
- [ ] AI slicing papers (survey in `Literature/survey/`)
- [ ] Self-healing literature

## Phase 1 — Prototype
- [x] Python environment, Mininet, Open vSwitch, rural topology
- [x] Context, priority, demand, allocation (surplus redistribution), QoS enforcement
- [x] Visualisation (`experiments/plots/plot_thesis.py`)
- [x] Evaluation metrics (`analysis/metrics.py`)

## Phase 2 — Network enforcement
- [x] Single-bottleneck topology (100 Mbps rural uplink)
- [x] Per-slice HTB + fq_codel queues on both directions (tc); OVS linux-htb backend
- [x] Bandwidth limiting, work-conserving and strict
- [x] Model-driven traffic generation (replaces iperf3 automation)
- [x] Traffic capture at every endpoint; packet-matched one-way delay and loss

## Phase 3 — Context automation
- [x] Time-based context (clock, school hours)
- [x] Seasonal context (harvest calendar)
- [x] Event context (alerts, admin override, timelines)

## Phase 4 — Self-healing
- [x] Failure injection (fiber cut, backhaul degradation, core switch failure)
- [x] Failure detection (link watcher, congestion, latency, reachability)
- [x] Alternate path (standby backup backhaul, loop-free failover)
- [x] Automatic recovery and fail-back (hold-down, OAM check)
- [x] Predictive switchover (RTT trend forecasting)
- [ ] Load balancing across primary and backup (needs multipath/STP; future work)

## Phase 5 — AI enhancement
- [x] SliceNet traffic classification (RF + 1D-CNN, held-out evaluation, in-loop)
- [x] Demand prediction (Holt forecasting; ML forecasting is future work)
- [x] Failure prediction (predictive backhaul degradation)
- [x] RL scheduler (CEM bandit; PPO on a calibrated sequential environment)

## Phase 6 — Real 5G core
- [x] Open5GS + UERANSIM, one slice (S-NSSAI/DNN) per service, UPF enforcement

## Thesis
- [x] Research design (`docs/thesis/research_design.md`)
- [x] Experimental results (`docs/thesis/results.md`, generated)
- [ ] Methodology chapter prose
- [ ] Paper draft
- [ ] Real Open vSwitch confirmation run (`sudo`, see README)
