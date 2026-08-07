# RL Scheduler Design

## Role

The RL agent does **not** classify traffic. It observes the entire network state and modifies resource allocation. SliceNet provides service-class perception; the RL agent optimizes bandwidth distribution.

## Observation Space

| Signal | Source | Type |
|--------|--------|------|
| Current context | Scenario registry | Categorical (one-hot) |
| Slice demands | Traffic orchestrator | float[4] |
| Current allocations | Allocation engine | float[4] |
| Queue lengths | tc telemetry | float[4] |
| Packet loss | PCAP-derived | float |
| Latency | PCAP-derived | float |
| Throughput | PCAP-derived | float[4] |
| Link utilization | OVS telemetry | float |
| Available capacity | Topology config | float |
| Active flows | Flow registry | int |

## Action Space

| Action | Effect |
|--------|--------|
| Adjust slice priorities | Modify priority weights (4 values, normalized) |
| Modify bandwidth caps | Set per-slice Mbps limits via tc HTB |
| Modify QoS weights | Adjust HTB class weights |
| Reserve emergency bandwidth | Lock healthcare minimum bandwidth |
| Reallocate resources | Trigger allocation engine with new weights |

Action vector: 4-dimensional continuous (priority weight adjustments per service class).

## Reward Function

```
reward = Σ(service_weight[i] × qos_satisfaction[i]) - penalty × sla_violations
```

Where:
- `qos_satisfaction[i]` = measured throughput / demand, capped at 1.0
- `penalty` = 10 per SLA violation
- `service_weight` = context-dependent priority from scenario registry

## Baseline

Rule-based policy using existing `slicing/` modules:
- `ContextEngine` → priority weights
- `DemandGenerator` → demands
- `AllocationEngine` → bandwidth allocation

RL agent must achieve ≥ baseline QoS satisfaction to be considered successful.

## Environment

- Wrapper: `scheduler/env.py` (Gymnasium-compatible)
- Training: `scheduler/train.py` (PPO via stable-baselines3 when available)
- Inference: `scheduler/agent.py`
- Fallback: `scheduler/baseline.py` (rule-based, always available)

## Integration

```
Telemetry → State Vector → RL Agent → Allocation → QoS Enforcer → Mininet
                ↑                                              |
                └──────────── reward (measured QoS) ───────────┘
```

## Self-Healing Extension

Recovery actions (reroute, priority boost) can be added as additional action dimensions in Phase 5, consuming the same telemetry pipeline via `monitoring/` and `self_healing/`.
