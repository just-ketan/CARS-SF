# RSNSD v2 — Real-Time Dataset Generation Framework
**Software Requirements Specification (SRS) & Architecture Design Document (ADD)**

## Executive Summary
RSNSD v2 is a registry-driven, digital-twin-based network telemetry dataset generator. It eschews static synthetic generation in favor of executing real application logic over a Mininet-based SDN environment, capturing empirical ground truth for ML-driven self-healing 5G networks.

---

## Layer 1 — Research Objectives

The generated dataset directly targets the following networking challenges:
* **Traffic Classification:** Distinguishing exact service types (e.g., *ECG Streaming* vs *Soil Sensors*) from raw telemetry without DPI.
* **Slice Allocation:** Deciding dynamically whether to map a flow to URLLC, eMBB, or mMTC queues.
* **QoS Prediction:** Predicting SLA violations (latency spikes, packet drops) before they affect the end user.
* **Congestion Prediction:** Forecasting queue saturation based on temporal traffic accumulation.
* **Failure Prediction:** Recognizing the early signature of a dying link or failing switch.
* **Root Cause Analysis (RCA):** Differentiating between congestion-induced packet loss and hardware-failure-induced packet loss.
* **RL State Representation:** Providing a dense, Markovian state vector of the network for Reinforcement Learning agents.
* **Network Self-Healing:** Training agents to autonomously reroute traffic or adjust queue weights when anomalies are detected.

---

## Layer 2 — Dataset Philosophy

The dataset is governed by a **Zero-Synthetic Assumption Policy**.
For every feature:
* **Why does this feature exist?** To expose network dynamics (queuing, routing, transport behaviors) to ML models.
* **Can Mininet measure it?** Yes, the majority of features (byte counts, queue drops, packet inter-arrival) are directly extracted from Mininet, OVS, and Linux `tc`.
* **If not, how is it derived?** End-to-end metrics (like packet loss rate) are derived by correlating ingress PCAP traces with egress PCAP traces.
* **If not derivable, why must it be estimated?** Environmental contexts (e.g., weather, disaster states) cannot be measured from a local PCAP. They must be synthetically provided as independent variables to observe their dependent effects on the network.
* **Why would an ML model benefit from it?** Complex relationships (e.g., how "Rain" correlates with "Link Degradation" which causes "TCP Retransmissions") allow ML to learn causal structures for RCA and prediction.

---

## Layer 3 — Complete Dataset Schema (Feature Registry)

Features are dynamically generated from a `FeatureRegistry`. Below are representative examples defining the rigorous schema contract:

### Example: `queue_drop_rate_pps`
```yaml
Feature ID: F_QUE_001
Feature Name: queue_drop_rate_pps
Description: Number of packets dropped per second by the OVS queue due to congestion.
Units: Packets per second (pps)
Datatype: Float32
Expected Range: [0.0, 10000.0]
Sampling Interval: 1000ms
Source Module: TelemetryEngine
Origin: Measured
Dependencies: QueueCollector
Applicable Applications: All
Importance Score: High (Critical for RCA)
Related Features: [queue_occupancy_bytes, link_utilization_pct]
Validation Rule: Must be >= 0.
Storage Format: Parquet Float32
Normalization Strategy: Min-Max Scaling per link capacity.
```

### Example: `tcp_retransmissions`
```yaml
Feature ID: F_TCP_042
Feature Name: tcp_retransmissions
Description: Total TCP retransmissions observed in the flow window.
Units: Count
Datatype: Int32
Expected Range: [0, 500]
Sampling Interval: Flow-duration dependent
Source Module: FeatureExtractionEngine
Origin: Measured
Dependencies: PCAPAnalyzer (scapy/tshark)
Applicable Applications: TCP-based flows (eMBB, General)
Importance Score: High (Congestion indicator)
Related Features: [tcp_window_size, mean_iat_ms]
Validation Rule: Must be >= 0, cannot exceed total packet count.
Storage Format: Parquet Int32
Normalization Strategy: Z-Score standardization.
```

---

## Layer 4 — Complete Class Catalogue (Application Registry)

Applications are instantiated dynamically via an `ApplicationRegistry`.

### 1. Healthcare (URLLC / eMBB)
* **Classes:** `ECG Streaming`, `Remote Diagnosis`, `Medical Imaging`, `Ambulance Video`, `Telemedicine Voice`, `ICU Monitoring`, `Drug Dispensing`.
* **Why it exists:** High priority, life-critical traffic requiring strict SLA enforcement.
* **Traffic characteristics:** High burstiness (Imaging), continuous UDP stream (Video), periodic small TCP (ECG).
* **QoS / Protocol:** TCP/UDP, Latency < 10ms, Loss < 0.001%.
* **Priority / Slice:** Critical / URLLC.

### 2. Agriculture (mMTC)
* **Classes:** `Soil Sensors`, `Drone Imaging`, `Livestock Tracking`, `Weather Station`, `Irrigation Controller`, `Crop Analytics`.
* **Why it exists:** Massive numbers of devices sending tiny payloads; highly tolerant to delay but prone to causing signaling storms.
* **Traffic characteristics:** Periodic, synchronized bursts, tiny packet sizes (64-128 bytes).
* **QoS / Protocol:** UDP/CoAP/MQTT, Latency < 1000ms, Loss < 1%.
* **Priority / Slice:** Low / mMTC.

### 3. Education (eMBB)
* **Classes:** `Live Lecture Video`, `Assignment Download`, `Interactive Whiteboard`, `VR Field Trip`.
* **Why it exists:** High bandwidth demands, heavily correlated with time-of-day (School Hours).
* **Traffic characteristics:** Long-lived TCP flows, heavy asymmetric downstream.

### 4. General Internet / Smart Village (Best Effort)
* **Classes:** `Web Browsing`, `Social Media`, `Smart Streetlights`, `CCTV Surveillance`, `VoIP Calls`.
* **Why it exists:** Background noise; absorbs available bandwidth but drops priority during congestion.

---

## Layer 5 — Complete Network Topology

* **Architecture:** 3-Tier Hierarchical SDN Topology.
* **Entities:**
  * **Village Edge:** `h_home`, `h_school`, `h_hospital`, `h_farm`. Connect to Rural Aggregation switches.
  * **Rural Aggregation:** `s_rural_1`, `s_rural_2`. OpenFlow 1.3 OVS instances. Bandwidth: 1Gbps, Propagation Delay: 2ms.
  * **Edge Cloud:** `s_edge`. Hosts MEC servers (`srv_mec_health`, `srv_mec_cctv`). Bandwidth: 10Gbps, Delay: 1ms.
  * **5G Core / Internet Gateway:** `s_core`. Hosts internet services (`srv_internet`). Bandwidth: 40Gbps, Delay: 10ms.
  * **Controller:** Remote ONOS/Ryu instance `c0` handling routing and slicing policy.
* **Queues:** HTB configured via Linux `tc`. 
  * Q0 (URLLC): Strict Priority, minimal buffer.
  * Q1 (eMBB): Guaranteed Bandwidth, large buffer.
  * Q2 (mMTC): Rate limited, moderate buffer.
  * Q3 (Best Effort): Uncapped but lowest priority.

---

## Layer 6 — Traffic Behaviour Catalogue

* **Arrival Process:** Modeled explicitly (e.g., Poisson for IoT, Markov-Modulated Poisson Process for Burst traffic).
* **Packet Size Distribution:** Fixed (64B IoT), Bimodal (TCP ACKs vs 1500B MTU payloads).
* **Flow & Session Duration:** Lognormal distributions representing human interaction times (e.g., 5-minute video watch times).
* **Transport Behaviour:** Explicit use of Linux TCP congestion control algorithms (CUBIC, BBR) generated natively by the `iperf3` and socket binaries in Mininet.

---

## Layer 7 — Time Evolution

The simulation runs a virtual clock that evolves the scenario context dynamically:
* **00:00 - 05:00 (Night):** Minimal traffic, mostly CCTV and background IoT.
* **08:00 - 09:00 (Morning Rush):** Spike in General Internet and VoIP.
* **09:00 - 15:00 (School Hours):** Massive eMBB traffic on the School links.
* **16:00 - 18:00 (Harvest):** Spike in Agriculture drone imaging and tractor telemetry.
* **Random Events:** Rain (degrades link capacity), Power Failure (knocks out specific switch domains).

---

## Layer 8 — Scenario Catalogue (Scenario Registry)

Scenarios mutate the base topology and traffic demands.
* **Scenario: Backhaul Failure**
  * **Trigger:** Random fault injector targeting `s_edge` -> `s_core` link.
  * **Duration:** 120 seconds.
  * **Network Effects:** Link bandwidth drops to 10%, Delay spikes to 200ms.
  * **Application Effects:** TCP windows collapse, video streams buffer, IoT packets drop.
  * **Recovery Pattern:** Step-function recovery (instant fix) or linear recovery (re-routing convergence).

* **Scenario: Festival**
  * **Trigger:** Scheduled time event.
  * **Network Effects:** Massive localized spike in `h_home` UE active connections.
  * **QoS Changes:** URLLC unaffected, Best Effort starves.

---

## Layer 9 — Feature Provenance

Every dataset feature has a strict auditable lineage:

```text
Packet Delay Pipeline
  ↓
iperf3 / UDP ping generated by Application Emulator
  ↓
Passes through OVS HTB Queue (Subject to physics/congestion)
  ↓
PCAP captured at Ingress Switch (T1) & Egress Switch (T2)
  ↓
FlowAnalyzer script computes (T2 - T1)
  ↓
Recorded as `end_to_end_latency_ms` (Measured)
```

---

## Layer 10 — Mininet Mapping

How dataset features are practically harvested from the Linux OS:
* **Flow Bytes/Packets:** `ovs-ofctl dump-flows s1`
* **Queue Drops/Backlog:** `tc -s class show dev s1-eth1`
* **End-to-End Latency / TCP Retransmissions:** `tshark -r capture.pcap -T fields -e tcp.analysis.retransmission`
* **Link Status:** `ip link show`
* **Application Throughput:** `iperf3 -J` JSON logs.
* **Host CPU/Mem:** `psutil` in Python querying `/proc`.

---

## Layer 11 — Sampling Engine

* **Frequency:** 1000ms global tick rate.
* **Synchronization:** A master orchestrator loop dispatches polling threads to all collectors (OVS, `tc`, OS) concurrently.
* **Aggregation:** Telemetry occurring between ticks (e.g., PCAP packet timestamps) are aggregated using sliding windows into 1-second rolling statistics (mean, std, min, max).
* **Jitter Handling:** Timestamps are strictly aligned to the orchestrator's epoch. Late polls are marked as `NaN` and interpolated during Phase 10.

---

## Layer 12 — Label Generation

Labels are automatically derived from Ground Truth simulation physics.
* **Congestion:** `True` if `queue_occupancy > 80%`.
* **Failure:** `True` if `FaultInjector` currently has an active `link_down` event.
* **QoS Violation:** `True` if `measured_latency > SLA_latency` (looked up from Application Registry).
* **Root Cause:** A categorical string mapped from the Scenario Engine (e.g., "FIBER_CUT", "DDOS", "NORMAL").

---

## Layer 13 — Validation

Every feature undergoes strict DataFrame validation before export:
* **Range Checks:** `packet_loss_rate` ∈ [0, 1].
* **Consistency:** `forward_bytes` + `backward_bytes` == `total_bytes`.
* **Outlier Detection:** Z-score > 5 flagged for review (to catch simulation glitches).
* **Correlation Constraints:** `queue_occupancy` must have a positive Pearson correlation with `end_to_end_latency`. If negative, the dataset generation is flagged as physically invalid.

---

## Layer 14 — Dataset Statistics

Expected outputs for a standard release:
* **Rows:** ~10,000,000 (representing seconds of active flows across multiple scenarios).
* **Columns:** Derived from registries (approx 100-150 columns).
* **Class Balance:** Enforced via `DatasetBalancer` sampling logic in the traffic orchestrator.
* **Missing Values:** 0%. All features are strictly imputed or dropped during Phase 10 time-alignment.

---

## Layer 15 — Folder Structure

```text
RSNSDv2/
├── registries/          # JSON/YAML defs for Features, Apps, Scenarios
├── simulation/          # Mininet topologies and SDN controllers
├── traffic/             # D-ITG/iperf3 application emulators
├── scenario/            # FSM and time evolution
├── context/             # Weather, mobility state managers
├── telemetry/           # OpenFlow, TC, and OS collectors
├── features/            # PCAP processing and feature aggregation
├── qos/                 # SLA evaluation
├── labeling/            # Ground truth derivation
├── failure_injection/   # Netem and link manipulation
├── dataset/             # Builder and time-synchronization
├── validation/          # Statistical integrity checks
├── export/              # CSV/Parquet dumping
└── release/             # Final packaged datasets
```

---

## Layer 16 — APIs

* **`ScenarioOrchestrator.subscribe(callback)`**: Allows Telemetry and Traffic engines to react to phase changes.
* **`TelemetryCollector.poll()`**: Asynchronous coroutine fetching state from Linux/OVS.
* **`ApplicationEmulator.spawn(app_id, dst_ip, bw)`**: Creates a subprocess on a specific Mininet `Host` object.

---

## Layer 17 — UML

```mermaid
graph TD
    subgraph Control Plane
        SCENARIO[Scenario Engine] --> CONTEXT[Context Engine]
        SCENARIO --> FAULT[Failure Injector]
        SCENARIO --> TRAFFIC[Traffic Orchestrator]
    end

    subgraph Data Plane (Mininet)
        TRAFFIC --> HOSTS[Mininet Hosts]
        FAULT --> LINKS[Mininet Links]
        HOSTS --> OVS[OVS Switches]
    end

    subgraph Telemetry & Pipeline
        OVS --> TC[tc / OpenFlow]
        LINKS --> PCAP[tcpdump PCAP]
        TC --> TELEMETRY[Telemetry Engine]
        PCAP --> EXTRACTOR[Feature Extraction]
        TELEMETRY --> BUILDER[Dataset Builder]
        EXTRACTOR --> BUILDER
        CONTEXT --> BUILDER
        BUILDER --> LABELER[Label Engine]
        LABELER --> VALIDATOR[Validation Engine]
        VALIDATOR --> EXPORT[Export Engine]
    end
```

---

## Layer 18 — Pipeline

```text
Mininet Initialization
  ↓
Scenario Evolves (e.g. Disaster)
  ↓
Traffic Generator Spawns Real Linux Sockets
  ↓
Packets Traverse Configured Bandwidth/Delay Links
  ↓
OVS Processes Flows (Queuing / Drops occur)
  ↓
Telemetry Engine Polls `tc` & `ovs-ofctl`
  ↓
Feature Extraction parses PCAPs for exact inter-arrival times
  ↓
Dataset Builder merges arrays on Timestamp
  ↓
Label Engine calculates SLA violations based on measured data
  ↓
Validator asserts physical consistency
  ↓
Exporter outputs Parquet/CSV
```

---

## Layer 19 — Future Extensions

* **Real SDR Integration:** Bridging Mininet host interfaces to USRPs/OAI to pipe physical 5G radio traffic into the virtual OVS data plane.
* **Open5GS & UERANSIM:** Replacing static routing with a full 5G Core control plane, generating authentic GTP-U encapsulated traffic.
* **Reinforcement Learning:** Replacing the `Export` engine with an OpenAI `Gym` environment, allowing RL agents to query the state vector in real-time and apply self-healing OpenFlow rules.
