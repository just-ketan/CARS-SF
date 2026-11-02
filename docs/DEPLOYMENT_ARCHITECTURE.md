# Deployment Architecture

Where each part of the closed loop runs in a private 5G network, what is implemented in this repository, and what
would change on real equipment.

## Short answer

The feedback loop runs at the **edge site, next to the UPF (MEC)**, not in the backhaul itself and not in a RIC.
Its decisions take 1–5 s and act on transport queues, which is what the system controls. The backhaul is
where the congestion is, so that is where rates are *enforced*; the agent only needs to reach those enforcement
points.

## Placement options

| Location | Timescale | Fit | Decision |
|---|---|---|---|
| Near-RT RIC (xApp) | 10 ms–1 s | Radio control. Needs an O-RAN gNB with E2. UERANSIM has no E2 interface and no radio scheduler, so nothing here could act on it. | The right home for radio slicing later; not used today |
| SMO / Non-RT RIC (rApp) | > 1 s | Policy and offline work: scenario priorities, degradation policies, retraining. | Offline functions map here; not a separate component in this repository |
| **UPF / MEC** | 1–5 s | Sees decapsulated user traffic, one hop from both enforcement points, keeps working if the fiber to the core is cut. | **Chosen for the live loop** |
| Backhaul link | — | Carries the congestion but has no compute or user-plane visibility, and is the thing that fails. | Enforcement only |

The placement also matters for resilience: a controller beyond the fiber would be cut off by the fault it must heal.

## Topology

```
 UEs ──ran──► gNB ──cell──► cell-site router ═══ N3, 100 Mb/s rural link ═══► UPF + MEC ──N6──► edge services
 (4 slices)  (UERANSIM)     UPLINK enforcement                                 │   DOWNLINK enforcement,
                                                                               │   monitoring, control loop
                                                                               ├── fiber 20 ms ───────► core cloud
                                                                               └── backup 40 ms, 50 Mb/s ─┘
 Open5GS 5GC (AMF, SMF, NRF, PCF, …) runs at the edge site with the UPF.
```

## Components

| Component | Runs at | Implementation | Inputs | Outputs |
|---|---|---|---|---|
| Traffic monitor | UPF tap (`ogstun`) | `Telemetry5G.start_flow_capture` | Decapsulated packets per UE | Flow records for SliceNet |
| QoS telemetry | Both enforcement points, UE probes | `Telemetry5G.poll` | HTB + fq_codel counters, ICMP probes in each PDU session | Per-class throughput, loss, queue delay, RTT, jitter, utilisation |
| SliceNet | Edge server | `classification/online.py`, Random Forest | Flow features over the first ~1 s, then rolling 5 s | Class per flow, confidence |
| Flow mapper | Cell-site router, UPF | `Transport5GQoS.classify_flow` | SliceNet decision | u32 rule on inner GTP-U headers (uplink), flower rule (downlink) |
| Context engine | Edge server | `context/engine.py` | Scenario, alerts | Priorities, degradation policy |
| QoS violation monitor | Edge server | `monitoring/qos_monitor.py` | Telemetry, `registries/qos_thresholds.yaml` | Per-class ok / transient / persistent |
| Rules allocator | Edge server | `QoSAwareAllocator`, `SliceController` | Demand per direction, context | Per-direction rates |
| RL agent | Edge server | `ClosedLoopResidualPolicy` | State (below) | Bounded correction to the rules' rates |
| Safety gate | Edge server | `slicing/safety.py` | Rules plan, RL proposal | Accepted plan; invalid plans never actuated |
| Actuator | Cell-site router, UPF | `Transport5GQoS.apply_allocation` | Rates per direction | HTB rates, read back from the kernel |
| Self-healing | Edge server, UPF, core cloud | `SelfHealingEngine`, `Topology5G` | Carrier state, probes | Route to backup, verified recovery, escalation |

### Agent inputs and limits

* **State:** classified per-class demand, current slicing rates, utilisation per direction, loss and delay against
  SLA, persistent-violation flags, context descriptors, classifier confidence, backup state.
* **Action:** ±30 % correction per class on the rules' rate, in that class's main direction.
* **Limits:** per-direction Σ ≤ C, minimum bandwidth, starvation protection, slice isolation through separate HTB
  classes, at most 20 % of capacity moved per decision.

## Interfaces

| Between | In this repository | On real equipment |
|---|---|---|
| Controller → enforcement | `tc` through a management shell on each node | NETCONF/gNMI to a cell-site router; a UPF QoS API |
| Controller → 5G core | None. Slices are provisioned statically (S-NSSAI, DNN). | NEF/PCF for policy, SMF N4 for QoS rules |
| Controller → RAN | None | A1 to a Near-RT RIC, E2 to the gNB |
| Telemetry | `tc` counters, probes, packet capture at the UPF | NWDAF and UPF event exposure, Y.1731 on the transport |

Allocation changes reach the **transport path and UPF**, not the 5G core's control plane or the radio. Live slices
are not re-negotiated with the core.

## Implemented vs not

Implemented and run: real Open5GS core, real GTP-U user plane, per-slice PDU sessions, transport slicing at both
ends of N3, SliceNet, RL, self-healing, all in Docker.

Simulated or absent: radio (UERANSIM), so no radio-resource slicing and no over-the-air measurement; no O-RAN RIC;
no 5G core policy integration; a real rural site has not been used.
