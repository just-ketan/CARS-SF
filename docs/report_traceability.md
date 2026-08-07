# Internship Report Traceability Matrix

Updated: 2026-08-07

| Report Chapter | Repository Module | Status |
|---|---|---|
| **Chapter 4 - Experimental Environment** | `topology/`, `traffic/`, `telemetry/`, `run_experiment.py` | Implemented |
| **Chapter 5 - Dataset Engineering** | `features/`, `dataset/`, `validation/`, `RSNSD/` (bootstrap) | Implemented |
| **Chapter 6 - AI Model (SliceNet)** | `classification/`, `slicing/` | Implemented |
| **Chapter 7 - Experimental Evaluation** | `experiments/`, `scheduler/`, `monitoring/` | Implemented |
| **Self-Healing** | `self_healing/`, `monitoring/` | Implemented |
| **Deployment** | `deployment/` | Config ready |

## Pipeline Traceability

| Vision Component | Implementation | Entry Point |
|---|---|---|
| Telemetry Collection | `telemetry/collector.py` | `run_experiment.py` |
| Feature Extraction | `features/extractor.py` | `core/orchestrator.py` |
| SliceNet Classification | `classification/slicenet.py` | `classification/train.py` |
| Context Engine | `slicing/context_engine.py`, `scenario/engine.py` | `registries/scenarios.yaml` |
| RL Scheduler | `scheduler/agent.py` | `scheduler/train.py` |
| QoS Enforcement | `slicing/qos_enforcer.py` | `--apply-qos` flag |
| Monitoring | `monitoring/monitor.py` | Integrated in orchestrator |
| Self-Healing | `self_healing/recovery.py` | `self_healing/injector.py` |

## Legacy Note

RSNSD v1 (`RSNSD/`) remains as synthetic bootstrap data. The canonical data path is now the Mininet pipeline producing `generated/datasets/cars_sf_dataset.csv`.
