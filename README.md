# Context Aware Rural Service Slice Framework

### AI-Driven Context-Aware Rural Service Slicing Framework for Resilient 5G Private Networks

**AI-Driven Context-Aware Rural Service Slicing and Autonomous Self-Healing Framework for Private 5G Networks**

## Vision

An end-to-end AI-native private 5G control plane that dynamically allocates scarce rural bandwidth across socially meaningful service classes: **Healthcare**, **Education**, **Agriculture**, and **General Internet**.

## Quick Start

```bash
pip install -r requirements.txt
python3 demo.py
```

## Experiments

### 1. Rule-Based Allocation (no Mininet)

```bash
# Single context demo
python3 demo.py

# All scenarios → results/allocation_results.csv
python3 experiments/run_all_contexts.py

# Extended reproducible batch with metadata
python3 experiments/run_reproducible.py
```

### 2. Mininet Network Simulation (requires sudo)

All live experiments run inside Mininet. Each experiment captures PCAP, OVS/tc telemetry, and extracts the full **89-column** feature schema.

```bash
# Single scenario (30 seconds)
sudo python3 run_experiment.py --scenario normal --duration 30

# School hours with QoS enforcement
sudo python3 run_experiment.py --scenario school --duration 60 --apply-qos

# Disaster scenario with HTB bandwidth shaping
sudo python3 run_experiment.py --scenario disaster --duration 45 --apply-qos

# Available scenarios: normal, school, harvest, disaster, medical_emergency, fiber_cut
```

Output: `generated/datasets/cars_sf_dataset.csv` + `generated/datasets/validation_report.txt`

### 3. SliceNet Training Pipeline

The training workflow follows a **baseline → Mininet → compare** methodology:

```
Step 1: Train baseline on RSNSD v1 synthetic dataset (108K rows, 89 features)
           ↓
Step 2: Collect Mininet-measured data across all scenarios (PCAP/OVS/tc)
           ↓
Step 3: Train SliceNet on Mininet empirical dataset
           ↓
Step 4: Compare synthetic baseline vs Mininet-trained model
```

```bash
# Full pipeline (baseline + Mininet collection + train + compare + plots)
sudo python3 experiments/run_slicenet_pipeline.py

# Without Mininet (uses mock schema data for steps 2-3)
python3 experiments/run_slicenet_pipeline.py --skip-collect

# Step 1 only: synthetic baseline metrics
python3 experiments/run_slicenet_pipeline.py --baseline-only

# Step 4 only: compare existing results
python3 experiments/run_slicenet_pipeline.py --compare-only

# Individual steps
python3 classification/train.py                                          # baseline on RSNSD v1
sudo python3 run_experiment.py --scenario school --duration 60           # collect Mininet data
python3 classification/train.py --mininet                                  # train on Mininet data
python3 experiments/plots/plot_slicenet_evaluation.py                      # generate comparison plots
```

**Pipeline outputs:**

| File | Description |
|------|-------------|
| `classification/models/slicenet_baseline.pkl` | Model trained on RSNSD v1 synthetic |
| `classification/models/slicenet_mininet.pkl` | Model trained on Mininet-measured data |
| `results/slicenet_baseline_metrics.json` | Baseline F1 scores |
| `results/slicenet_mininet_metrics.json` | Mininet F1 scores |
| `results/slicenet_comparison.json` | Side-by-side comparison with per-class F1 |
| `generated/datasets/mininet_full_dataset.csv` | Merged Mininet data (all scenarios) |
| `docs/figures/slicenet_*.png` | Comparison plots |

### 4. RL Scheduler

```bash
# Train RL agent (50-200 episodes)
python3 scheduler/train.py --episodes 200

# Rule-based baseline is always available via scheduler/baseline.py
```

### 5. Self-Healing and Monitoring

Monitoring and failure detection are integrated into the Mininet experiment loop. Fault injection activates automatically on `fiber_cut` scenarios.

```bash
sudo python3 run_experiment.py --scenario fiber_cut --duration 45 --apply-qos
```

### 6. Generate Report Figures

```bash
python3 experiments/plots/plot_dataset_analysis.py
python3 experiments/plots/plot_simulation_performance.py
python3 experiments/plots/plot_slicenet_evaluation.py
python3 experiments/plots/generate_tables.py
```

## Architecture

```
Network (Mininet) → Telemetry → Feature Extraction (89 cols) → Dataset
                                ↓
                           SliceNet (Classification)
                                ↓
              Context Engine → RL Scheduler → Allocation → QoS → Network
                                ↓
                         Monitoring → Self-Healing
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for full system design.

## Repository Structure

```
CARS-SF/
├── core/              # Orchestrator and shared interfaces
├── registries/        # Applications, scenarios, feature schema (YAML)
├── topology/          # Canonical rural 5G Mininet topology
├── traffic/           # Profile-driven traffic generation
├── telemetry/         # OVS, tc, PCAP, psutil collectors
├── features/          # PCAP → 89-column schema extraction
├── dataset/           # Time-aligned dataset builder
├── validation/        # Statistical dataset validation
├── slicing/           # Context, priority, allocation, QoS
├── classification/    # SliceNet training pipeline
├── scheduler/         # RL agent and Gym environment
├── monitoring/        # SLA violation detection
├── self_healing/      # Failure detection and recovery
├── deployment/        # Edge server configs
├── experiments/       # Experiment runners and plots
├── RSNSD/             # FROZEN: v1 synthetic bootstrap dataset
└── run_experiment.py  # Main Mininet entry point
```

## RSNSD v1 Freeze Policy

`RSNSD/` is **frozen** as a synthetic bootstrap dataset. It provides baseline metrics for SliceNet architecture validation. All production training uses Mininet-measured data. Do not extend RSNSD v1 synthetic generation.

## Legacy Components (Deprecated)

| Component | Status |
|-----------|--------|
| `MininetSims/` | Merged into `topology/`, `traffic/`, `telemetry/` |
| `RSNSDv2/` | Merged into `core/orchestrator.py` |
| `traffic_models/` | Preserved for demand tables |

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture
- [DATASET_DESIGN.md](DATASET_DESIGN.md) — Dataset philosophy and 89-column schema
- [RL_DESIGN.md](RL_DESIGN.md) — RL scheduler design
- [tracker.md](tracker.md) — Implementation progress

## Requirements

- Python 3.10+
- Mininet + Open vSwitch (for live experiments)
- Root privileges (for Mininet experiments)
