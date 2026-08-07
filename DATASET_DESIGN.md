# Dataset Design

## Philosophy

The network is the source of truth. Every feature must originate from measurable network behaviour or be deterministically derived from measurements. Labels have deterministic ground truth from spawn metadata and measured SLA violations.

## Data Pipeline

```
Mininet Traffic → PCAP + OVS/tc/psutil → Flow Features → Labels → CSV/Parquet
```

## Feature Provenance

| Category | Source | Examples |
|----------|--------|----------|
| Flow statistics | PCAP (Scapy) | packet_count, byte_count, flow_duration_ms, IAT stats |
| QoS metrics | Derived from PCAP | latency, jitter, loss, throughput |
| Switch metrics | OVS (`ovs-ofctl`) | ovs_bytes, flow_entries |
| Queue metrics | Linux tc (`tc -s`) | queue_drops, queue_bytes |
| Host metrics | psutil | host_cpu_pct, host_mem_pct |
| Context | Scenario registry | network_load_pct, scenario_id |
| Radio metrics | Context-injected | signal_strength_dbm (simulated degradation) |
| Labels | Spawn metadata + QoS | service_class, application_id, sla_satisfied |

## Label Leakage Prevention

The following columns are **labels only** and must never be used as ML inputs:

- `service_class`, `application_id`, `slice_type_label`, `priority_level`
- `service_type`, `application_name`, `slice_type`, `service_priority` (RSNSD v1 leakage)

See `registries/features.yaml` for the canonical feature/label split.

## RSNSD v1 Positioning

RSNSD v1 (`RSNSD/dataset/raw/rsnsd_v1.0.csv`) is a **synthetic bootstrap dataset**:

- Use for SliceNet architecture prototyping only
- Do not claim empirical network telemetry
- Retrain on Mininet-measured data before publication

## Schema

- Full schema: **89 columns** (aligned with RSNSD v1, see `features/schema_mapper.py`)
- ML features: ~75 numeric columns (excludes labels and categorical context)
- Labels: 6 columns
- Output (Mininet): `generated/datasets/mininet_full_dataset.csv`

## Training Pipeline

```
Step 1: RSNSD v1 synthetic → baseline metrics (classification/models/slicenet_baseline.pkl)
Step 2: Mininet simulations  → 89-column empirical dataset (all scenarios)
Step 3: Mininet dataset      → SliceNet retraining (classification/models/slicenet_mininet.pkl)
Step 4: Compare              → results/slicenet_comparison.json + docs/figures/slicenet_*.png
```

Run: `python3 experiments/run_slicenet_pipeline.py`

## Validation

Dataset validation checks (see `validation/validator.py`):

1. Schema completeness
2. QoS consistency (goodput ≤ throughput, loss ∈ [0, 100])
3. Expected correlations (load ↑ → latency ↑)
4. Outlier ratio (IQR-based)
5. Pass threshold: score ≥ 85/100
