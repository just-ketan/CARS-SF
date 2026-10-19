# Execution Guide

Every command below exists in this repository and was run during the October 2026
audit. Commands that need root are marked; everything else runs as a normal user.

## 1. Prerequisites

| Requirement | Needed for | Check |
|---|---|---|
| Linux, Python 3.12 | everything | `python3 --version` |
| Mininet 2.3 (system package; the venv sees it through `--system-site-packages`) | Mininet modes | `python3 -c "import mininet"` |
| `tc`, `ip` (iproute2), `tcpdump`, `mnexec` | Mininet modes | `which tc ip tcpdump mnexec` |
| Unprivileged user namespaces **or** root | sudo-free Mininet runs / real OVS | `unshare -Urn true && echo ok` |
| Open vSwitch | only real-OVS runs (root) | `ovs-vsctl --version` |
| Docker + compose | only the Open5GS/UERANSIM deployment | `docker compose version` |

`run_pipeline.py` checks the prerequisites of the chosen mode before doing anything else.
It stops with exit code 2 and lists what is missing.

## 2. Installation

```bash
make setup                      # .venv with system site-packages + requirements.txt
.venv/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu   # if torch is missing
```

## 3. One command per mode

```bash
.venv/bin/python run_pipeline.py --mode unit        # unit, contract, reward, transition tests (~5 s)
.venv/bin/python run_pipeline.py --mode synthetic   # + RSNSD generation/validation, SliceNet baseline, RL training + evaluation (~5 min)
.venv/bin/python run_pipeline.py --mode mininet     # + all emulated-network integration tests (~8 min)
.venv/bin/python run_pipeline.py --mode rl          # RL training + coupled live-loop test
.venv/bin/python run_pipeline.py --mode full        # everything incl. Mininet collection and the thesis matrix (~3–4 h)
.venv/bin/python run_pipeline.py --mode full --dry-run   # environment check + stage list only
make pipeline MODE=synthetic                         # same through make
```

Each run writes `results/pipeline/<timestamp>_<mode>/manifest.json`, which records:

* every stage's command, exit code, duration and log;
* code and model fingerprints;
* dataset manifests (schema version, seed, rows, sha256);
* model hashes and the environment.

The first failing stage stops the pipeline.

## 4. Synthetic path (path A)

```bash
.venv/bin/python -m dataset.rsnsd --per-scenario 6000 --seed 42     # = make data
```

This writes:

* `RSNSD/dataset/raw/rsnsd_v1.0.csv` (108 000 rows, 18 scenarios);
* `rsnsd_v1.0.manifest.json`, with the seed, config, class counts, sha256, the
  `rsnsd-contract-2.0` validation result and RSNSD's statistical validation score.

The same seed gives a byte-identical file; `tests/test_contract.py` checks this across
processes.

## 5. Dataset validation

```bash
.venv/bin/python -m pytest -q tests/test_contract.py
.venv/bin/python -c "
import pandas as pd
from features.contract import validate
print(validate(pd.read_csv('RSNSD/dataset/raw/rsnsd_v1.0.csv', low_memory=False), 'synthetic_rsnsd').as_dict())
print(validate(pd.read_csv('generated/datasets/mininet_full_dataset.csv', low_memory=False), 'mininet_measured').as_dict())"
.venv/bin/python -c "from features.contract import data_dictionary; print(data_dictionary('mininet_measured').to_string())"
```

## 6. SliceNet

```bash
.venv/bin/python experiments/run_slicenet_pipeline.py --baseline-only   # RF on RSNSD, whole scenarios held out
.venv/bin/python experiments/collect_dataset.py --seeds 0 1 2           # Mininet-measured dataset (6 scenarios × 3 seeds, ~25 min)
.venv/bin/python experiments/collect_dataset.py --merge-only            # re-merge + contract validation + manifest
.venv/bin/python experiments/run_slicenet_pipeline.py                   # baseline, RF + 1D-CNN on measured data, transfer study
```

Metrics are written to `results/slicenet_*_metrics.json`. They include per-class
precision, recall and F1, the confusion matrix, and the abstention rate and accepted
accuracy at the 0.5 confidence threshold.

## 7. RL

```bash
.venv/bin/python scheduler/train.py --algo all --seeds 0 1 2    # CEM + PPO (3 seeds) on SequentialSlicingEnv (~3 min)
.venv/bin/python scheduler/train.py --evaluate-only             # deployed models on held-out test seeds, paired vs rule-based
.venv/bin/python scheduler/calibrate.py                         # optional: recalibrate the simulator from live feedback.csv
```

Outputs:

* `results/rl_training.json`;
* `scheduler/models/ppo_runs/seed*/learning_curve.csv` and the checkpoints;
* the deployed models `scheduler/models/rl_agent.pkl` and `ppo_slicing.zip`.

## 8. Mininet / OVS (path B, closed loop)

Sudo-free, on Linux bridges in a user + network namespace:

```bash
.venv/bin/python -m tests.integration.harness school 40 apply_qos=true                         # proposed scheduler
.venv/bin/python -m tests.integration.harness school 40 apply_qos=true scheduler=context_unaware
.venv/bin/python -m tests.integration.harness school 60 apply_qos=true scheduler=rl_online control_interval=4
.venv/bin/python -m tests.integration.harness fiber_cut 45 apply_qos=true                      # self-healing
.venv/bin/python -m pytest -q -m integration tests/integration                                 # all integration tests (= make integration)
.venv/bin/python -m pytest -q -m integration tests/integration/test_pipeline.py -k coupled     # coupled RL loop only
```

On real Open vSwitch (**root**; use the venv interpreter):

```bash
sudo .venv/bin/python run_experiment.py --scenario school --duration 40 --apply-qos --scheduler rl_ppo
sudo .venv/bin/python run_experiment.py --scenario fiber_cut --duration 45 --apply-qos
```

Each run writes `results/runs/<run_id>/`:

| File | Contents |
|---|---|
| `summary.json` | KPIs, enforcement and telemetry-health summaries, contract report, transition summary, controller history with enforcement read-back |
| `dataset.csv` | Stamped `mininet_measured` records |
| `feedback.csv` | Per-tick reward and its terms |
| `rl_transitions.jsonl` | One (s, a, r, s′) record per controller decision |
| `slice_monitor.csv`, `validation_report.txt` | Per-slice SLA monitoring; dataset validation |

## 9. Evaluation matrix

```bash
.venv/bin/python experiments/run_matrix.py --list                         # state of every run: missing / current / stale
.venv/bin/python experiments/run_matrix.py --rerun-stale --workers 3      # all studies except online_rl
.venv/bin/python experiments/run_matrix.py --rerun-stale --workers 1 --study online_rl   # sequential: shared online checkpoint
.venv/bin/python experiments/aggregate.py                                 # results/tables/*.csv, provenance.json
.venv/bin/python experiments/plots/plot_thesis.py                         # docs/figures/thesis/
.venv/bin/python experiments/report.py                                    # docs/thesis/results.md (hypothesis verdicts)
```

A run is *stale* when its recorded code or model fingerprint differs from the current
one. Stale runs are never reused silently. `--rerun-stale` moves them to
`results/runs_archive/<old fingerprint>/` and re-runs them.

## 10. Real 5G core (Docker)

```bash
docker compose -f deployment/5g/docker-compose.yml up -d     # ~60 s until PDU sessions are up
.venv/bin/python deployment/5g/run_5g.py --scenario disaster --capacity 10 --mode both --seeds 0 1 2
docker compose -f deployment/5g/docker-compose.yml down
```

## 11. Cleanup and troubleshooting

| Symptom | Action |
|---|---|
| A real-OVS run was killed with SIGKILL | `make clean-net` (= `sudo mn -c`). SIGTERM is handled: teardown runs. |
| A sudo-free run timed out | Nothing to clean. The harness signals the whole process group and the namespace disappears with it. |
| `Environment check failed` | Install what the message lists. In mininet/rl/full modes, check `unshare -Urn true`. |
| `RuntimeError: no application flows were captured` | tcpdump or traffic failed. Check `generated/logs/<run_id>/`. The run refuses to substitute fabricated records. |
| `ContractViolation` | The dataset breaks `rsnsd-contract-2.0`; the message lists each violated rule. |
| `ModelNotTrained` | Train SliceNet first (§6). |
| Aggregator warns about stale runs | `run_matrix.py --rerun-stale` |
| `rl_cem` / `rl_ppo` run reports `policy_fallback_to_rule: true` | The model file is missing: run §7. |
