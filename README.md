# CARS-SF — Context-Aware Rural Service Slicing Framework

**AI-driven, context-aware rural service slicing with autonomous self-healing for private 5G networks.**

Rural networks share one scarce uplink among socially critical services. CARS-SF
slices by *service* (Healthcare, Education, Agriculture, General Internet), not by
technology (eMBB/URLLC/mMTC). It decides *how much* each slice gets from the
operating context (school hours, harvest, disaster …) and measured demand,
enforces the decision in the network, monitors per-slice SLAs, heals backhaul and
core failures on its own, and learns: RL policies for priorities, and a traffic
classifier (SliceNet) that slices multi-service devices.

* Architecture as built: [ARCHITECTURE.md](ARCHITECTURE.md). The original vision is in [architecture.md](architecture.md).
* Research questions, hypotheses and method: [docs/thesis/research_design.md](docs/thesis/research_design.md)
* Measured results and hypothesis verdicts: [docs/thesis/results.md](docs/thesis/results.md)
* Evaluation report: [docs/EVALUATION_REPORT.md](docs/EVALUATION_REPORT.md) · implementation audit and acceptance checklist: [docs/AUDIT.md](docs/AUDIT.md)
* Every command: [docs/EXECUTION_GUIDE.md](docs/EXECUTION_GUIDE.md) · RL state/action/reward: [RL_DESIGN.md](RL_DESIGN.md)

## Quick start

```bash
make setup          # venv (system site-packages expose Mininet) + requirements
make data models    # RSNSD v1 synthetic dataset; SliceNet baseline + RL policies
make test           # unit tests
make integration    # end-to-end runs on an emulated network — no sudo needed
.venv/bin/python run_pipeline.py --mode full   # everything, reproducibly, with a manifest (modes: unit, synthetic, mininet, rl, full)
```

PyTorch is installed from the CPU wheel index:
`.venv/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu`.

System packages: `mininet`, `openvswitch-switch`, `tcpdump`, `iproute2`, `bridge-utils`.

## Running experiments

**Without sudo.** The pipeline runs unchanged inside a user and network namespace, with
Linux bridges standing in for OVS:

```bash
.venv/bin/python -m tests.integration.harness fiber_cut 45 apply_qos=true
.venv/bin/python -m tests.integration.harness school 40 apply_qos=true scheduler=tgpp
.venv/bin/python -m tests.integration.harness normal 40 apply_qos=true timeline=rural_day
```

**Real Open vSwitch (root).** Always use the venv interpreter: plain `sudo python3`
is the system Python, which lacks the dependencies.

```bash
sudo .venv/bin/python run_experiment.py --scenario fiber_cut --duration 45 --apply-qos
sudo .venv/bin/python run_experiment.py --timeline rural_day --duration 40 --apply-qos
sudo .venv/bin/python run_experiment.py --scenario disaster --apply-qos --scheduler rl_ppo
sudo .venv/bin/python run_experiment.py --scenario school --apply-qos --mixed-ue --classification slicenet
make clean-net      # `sudo mn -c` after an aborted run
```

| Option | Values |
|---|---|
| Scenarios | normal, school, harvest, disaster, medical_emergency, fiber_cut, backhaul_degradation, core_switch_failure |
| Timelines | rural_day, school_week, medical_night, admin_override |
| Schedulers | proposed, rl_cem, rl_ppo, no_surplus, proportional, static_equal, tgpp, no_slicing |

Each run writes `results/runs/<run_id>/`:

| File | Contents |
|---|---|
| `summary.json` | Allocations, per-slice KPIs, SLA monitoring, failures, healing actions, MTTD/MTTR/outage, SliceNet accuracy |
| `dataset.csv` + `sequences.npz` | Measured flow windows and packet sequences |
| `feedback.csv` | Per-tick allocation, demand, throughput, RTT and reward |
| `slice_monitor.csv` | Per-tick, per-slice SLA records |
| `validation_report.txt` | Dataset validation score |

## The thesis study

```bash
.venv/bin/python experiments/run_matrix.py --rerun-stale --workers 3  # 365 runs (configs/experiments/thesis.yaml)
.venv/bin/python experiments/run_matrix.py --rerun-stale --workers 1 --study online_rl
.venv/bin/python experiments/aggregate.py                           # tables, 95 % CIs, Wilcoxon tests
.venv/bin/python experiments/plots/plot_thesis.py                   # docs/figures/thesis/
.venv/bin/python experiments/report.py                              # docs/thesis/results.md
```

The matrix is resumable. Completed runs made with the current code and models are
skipped; stale ones are reported, or archived and re-run with `--rerun-stale`. The
studies are:

* main (8 schedulers × 5 contexts × 5 seeds);
* ablation;
* capacity and load sensitivity;
* scalability;
* resilience;
* timeline;
* in-loop SliceNet;
* online RL.

### SliceNet

```bash
.venv/bin/python experiments/run_matrix.py --config configs/experiments/dataset.yaml   # measured dataset
.venv/bin/python experiments/collect_dataset.py --merge-only
.venv/bin/python experiments/run_slicenet_pipeline.py    # synthetic baseline, RF + 1D-CNN, transfer study
```

### Learning engine

```bash
.venv/bin/python scheduler/calibrate.py                  # calibrate the simulator from run feedback
.venv/bin/python scheduler/train.py --algo all           # CEM (bandit) + PPO (sequential environment)
```

## Real 5G core

[Open5GS](https://open5gs.org) 5GC + [UERANSIM](https://github.com/aligungr/UERANSIM)
gNB, with one UE per service slice, each slice having its own S-NSSAI, DNN and address
pool. The CARS-SF controller enforces slices on the UPF.

```bash
docker compose -f deployment/5g/docker-compose.yml up -d     # ~60 s until PDU sessions are up
.venv/bin/python deployment/5g/run_5g.py --scenario disaster --capacity 10 --mode both --seeds 0 1 2
docker compose -f deployment/5g/docker-compose.yml down
```

## Repository layout

```
core/            orchestrator, closed-loop controller, stage interfaces, config
registries/      applications, scenarios, slices, timelines, schedulers, feature schema (YAML)
topology/        rural Mininet topology
traffic/         traffic models, generator, sink, orchestration
telemetry/       counters, HTB stats, RTT probes, link watcher, endpoint captures
context/         context inference engine
slicing/         demand estimation, priority engine, allocators, QoS enforcement
monitoring/      per-slice SLA monitoring
self_healing/    detection (reactive + predictive), injection, healing engine
scheduler/       RL environments, CEM / PPO agents, calibration
features/        packet matching, flow windows, shape features, schema
classification/  SliceNet (RF, 1D-CNN), training pipeline, in-loop classifier
validation/      dataset validator
analysis/        KPIs, fairness, outage
experiments/     matrix runner, aggregation, report, plots, dataset collection
deployment/5g/   Open5GS + UERANSIM deployment and driver
tests/           unit tests; integration/ = emulated-network end-to-end tests
RSNSD/           v1 synthetic dataset generator (frozen)
```

`MininetSims/` and `RSNSDv2/` are deprecated predecessors, merged into the root
pipeline and excluded from tests.

## Licence

MIT. See [LICENSE](LICENSE).
