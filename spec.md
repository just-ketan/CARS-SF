# CARS-SF System Specification

How CARS-SF is set up, from the emulated network to the Open5GS deployment: topology, Mininet, Open vSwitch, 5G core
and RAN, traffic control, the control loop, and how to bring each one up.

Values here are taken from the code and config files named beside them. If this document and a config file disagree,
the config file is correct.

## 1. System overview

CARS-SF is a closed control loop for a private rural 5G network. Four service classes share one 100 Mb/s rural link
across eight operating scenarios, giving 32 class-scenario combinations.

```
monitor ─► classify (SliceNet) ─► evaluate QoS ─► select action ─► enforce ─► observe ─► learn
   ▲                                  (rules, plus RL on a                               │
   └────────────────────────────────── persistent violation) ◄───────────────────────────┘
```

The same control code runs on two network backends:

| | Mininet testbed | Open5GS 5G stack |
|---|---|---|
| Entry point | `run_experiment.py`, `tests/integration/harness.py` | `deployment/5g/run_5g.py` |
| Network | Layer 2, bridges and veth pairs in namespaces | Routed Docker networks |
| Switching | OVS (`OVSBridge`) or Linux bridge | No switches; Linux routing |
| 5G core | None | Open5GS 2.7.2 |
| RAN | None; UEs are hosts | UERANSIM 3.2.6 (simulated radio) |
| User plane | Plain IP | Real GTP-U through the UPF |
| Privileges | Root for OVS; sudo-free for Linux bridge | Docker |
| Network adapter | `topology/rural_topology.py` | `deployment/5g/stack5g.py` |

`stack5g.py` provides the objects the controller expects, so `SliceController`, `SelfHealingEngine`,
`FailureDetector`, `OnlineSliceClassifier` and the RL policies are the same classes on both backends.

**What this system is not.** It is not a live radio network. UERANSIM simulates the radio, so nothing schedules
radio resources. Slices are enforced on the transport path and at the UPF. There is no O-RAN RIC, and the controller
has no interface to the 5G core's policy functions. See §12.

## 2. Service classes and scenarios

### 2.1 Classes (`registries/slices.yaml`)

| Class | HTB class | HTB prio | Floor (Mb/s) | Latency (ms) | Jitter (ms) | Loss (%) | Min. satisfaction | CoDel target / interval (ms) |
|---|---|---|---|---|---|---|---|---|
| healthcare | 1:10 | 1 | 5 | 50 | 10 | 1.0 | 0.95 | 12 / 120 |
| education | 1:20 | 2 | 2 | 150 | 30 | 2.0 | 0.80 | 25 / 250 |
| agriculture | 1:30 | 3 | 1 | 250 | 50 | 2.0 | 0.80 | 25 / 250 |
| general | 1:40 | 4 | 1 | 500 | 200 | 5.0 | 0.50 | 5 / 100 |

`registries/qos_thresholds.yaml` tightens healthcare latency to 40 ms in `disaster` and `medical_emergency`.
`monitoring/qos_monitor.py` raises an error if an override would relax a threshold, so a hard scenario cannot pass
by lowering its target.

### 2.2 Scenarios (`registries/scenarios.yaml`)

Demand is in Mb/s for a 100 Mb/s link. Fault times are fractions of the run.

| Scenario | healthcare | education | agriculture | general | Total | Overload policy | Fault |
|---|---|---|---|---|---|---|---|
| normal | 20 | 20 | 20 | 20 | 80 | proportional | None |
| school | 5 | 80 | 10 | 50 | 145 | proportional | None |
| harvest | 5 | 20 | 80 | 50 | 155 | proportional | None |
| disaster | 90 | 5 | 5 | 20 | 120 | priority | None |
| medical_emergency | 95 | 5 | 5 | 10 | 115 | priority | None |
| fiber_cut | 40 | 15 | 15 | 30 | 100 | priority | Cut at 0.33, repair at 0.66 |
| backhaul_degradation | 40 | 15 | 15 | 30 | 100 | priority | Delay +15 ms and loss +0.3 % per tick from 0.2, cut at 0.7 |
| core_switch_failure | 40 | 15 | 25 | 30 | 110 | priority | Fail at 0.33, repair at 0.66 |

The registry also defines `repeated_fiber_cut`. It is used in resilience tests but is not one of the eight
evaluated scenarios (`EVALUATED_SCENARIOS` in `scheduler/env_dir.py`).

Totals are offered load across all classes. Each direction is shaped separately, so a total above 100 does not by
itself mean either direction is overloaded.

## 3. Mininet testbed

Source: `topology/rural_topology.py`. Applications and scenarios come from `registries/`.

### 3.1 Topology

```
 UEs ── s_rural ═══ rural uplink, 100 Mb/s ═══ s_edge ── srv_edge, mec_hlt, mec_ctv
                                                ║  ┆
                                     fiber 20 ms ║  ┆ backup 40 ms, 50 Mb/s (normally down)
                                                ║  ┆
                                               s_core ── srv_core
```

Mininet is built with `link=TCLink`, `autoSetMacs=True`, `build=False`, and no controller by default.

| Switch | dpid | Role |
|---|---|---|
| `s_rural` | 1 | Rural aggregation; uplink enforcement on `s_rural-up` |
| `s_edge` | 2 | Edge cloud; downlink enforcement on `s_edge-down` |
| `s_core` | 3 | Core network |

### 3.2 Hosts and addresses

The default is 2 UEs per service (`--ues-per-service`, 1–9). UE *i* gets `10.0.1.<base + i − 1>`.

| Host | Address | Attached to |
|---|---|---|
| `h_health`, `h_health2`, … | 10.0.1.10, .11, … | `s_rural` |
| `h_edu`, `h_edu2`, … | 10.0.1.20, .21, … | `s_rural` |
| `h_agri`, `h_agri2`, … | 10.0.1.30, .31, … | `s_rural` |
| `h_gen`, `h_gen2`, … | 10.0.1.40, .41, … | `s_rural` |
| `h_mixed` (only with `--mixed-ue`) | 10.0.1.60 | `s_rural` |
| `srv_edge` | 10.0.2.10 | `s_edge` (`s_edge-srv`) |
| `mec_hlt` | 10.0.2.20 | `s_edge` (`s_edge-mhlt`) |
| `mec_ctv` | 10.0.2.30 | `s_edge` (`s_edge-mctv`) |
| `srv_core` | 10.0.3.10 | `s_core` (`s_core-srv`) |

The network is one flat Layer 2 domain. Each host has on-link routes for 10.0.1.0/24, 10.0.2.0/24 and 10.0.3.0/24.

### 3.3 Links

| Link | Port names | Rate | Delay |
|---|---|---|---|
| UE access | `s_rural-a<N>` | Not shaped | 8 ms on the switch port toward the UE |
| Rural uplink | `s_rural-up` ↔ `s_edge-down` | 100 Mb/s | None; the QoS enforcer owns these qdiscs |
| Fiber backhaul | `s_edge-bh` ↔ `s_core-bh` | Not shaped | 20 ms |
| Backup backhaul | `s_edge-bkp` ↔ `s_core-bkp` | 50 Mb/s | 40 ms; down at start |
| Server links | `s_edge-srv`, `s_edge-mhlt`, `s_edge-mctv`, `s_core-srv` | Not shaped | 8 ms on the switch port toward the server |

**Delay placement.** The enforcer replaces the qdiscs at both ends of the rural uplink, which would discard a netem
delay placed there, and `tcpdump` on a sender sees packets only after its egress qdisc. Propagation delay therefore
sits on the switch port facing the destination. The modelled 2 + 5 + 1 ms gives 8 ms one way to the edge, and
28 ms to the core over fiber or 48 ms over backup.

**Loop avoidance.** The switches do not run STP. Self-healing changes only the `s_edge` side of each backhaul and
never enables the backup while the primary is up, so the Layer 2 domain stays loop-free.

## 4. Open vSwitch

### 4.1 Bridge mode

The default switch is Mininet's `OVSBridge`, which sets `failMode='standalone'`. Each bridge does normal L2 learning
and needs no OpenFlow controller. Tested host versions are OVS 3.3.9 and Mininet 2.3.0.

The evaluation matrix runs on Linux bridges, through a sudo-free harness that uses `unshare -Urnm`
(`tests/integration/harness.py`). Real OVS is used for the validation in §4.4.

### 4.2 QoS backends

| | `--qos-backend tc` (default) | `--qos-backend ovs` |
|---|---|---|
| Mechanism | Kernel HTB and fq_codel on the port's interface | OVS `linux-htb` QoS and queues |
| OVS role | Forwarding only | Forwarding and queue selection |
| Classifying traffic | `tc` filters | OpenFlow `set_queue` rules |
| Read-back | `tc class show` | OVS database queue records |
| Per-flow SliceNet rules | Yes | No equivalent; not tested |
| Reduced ceiling on backup | Yes | No (`_apply_ovs` takes no ceilings) |

### 4.3 OVS backend configuration

From `QoSEnforcer._setup_ovs` and `_apply_ovs`. Each of `s_rural-up` and `s_edge-down` gets one `linux-htb` QoS with
four queues:

```sh
ovs-vsctl -- set port <iface> qos=@qos \
  -- --id=@qos create qos type=linux-htb other-config:max-rate=100000000 \
       queues:1=@q1 queues:2=@q2 queues:3=@q3 queues:4=@q4 \
  -- --id=@q1 create queue other-config:min-rate=1000000 other-config:max-rate=100000000  # same for q2 to q4
```

Queue numbers follow the class order: 1 healthcare, 2 education, 3 agriculture, 4 general. Flow rules select the
queue and then hand the packet to normal L2 forwarding:

```sh
# uplink, priority 20, one rule per UE address
ovs-ofctl add-flow s_rural "priority=20,ip,nw_src=<ue>,actions=set_queue:<q>,normal"
# downlink
ovs-ofctl add-flow s_edge  "priority=20,ip,nw_dst=<ue>,actions=set_queue:<q>,normal"
```

With `app` classification or 3GPP classes, priority 30 rules also match protocol and port. Each allocation updates
the queue, then reads it back and compares:

```sh
ovs-vsctl set queue <queue> other-config:min-rate=<rate> other-config:max-rate=<ceil>
ovs-vsctl get queue <queue> other-config
```

When OVS is present, telemetry also polls `ovs-ofctl dump-flows` for byte counts and flow-table size.

### 4.4 OVS validation

`experiments/ovs_validation.py` runs 33 real-OVS runs inside the `cars-sf` image, with seeds 30–32:

| Study | Runs | Purpose |
|---|---|---|
| `ovs_actuation` | school, disaster × no_slicing, static_equal, qos_adaptive | Kernel HTB on OVS ports |
| `ovs_backend` | disaster × proposed, `--qos-backend ovs` | Queue backend and read-back |
| `ovs_resilience` | fiber_cut, repeated_fiber_cut, backhaul_degradation, core_switch_failure × qos_adaptive | Self-healing on OVS |

Outputs are `results/runs/ovs_*` and `results/evidence/ovs_logs/`. These runs predate the current closed-loop code
and cover neither `closed_loop` nor SliceNet.

## 5. Open5GS 5G deployment

Sources: `deployment/5g/docker-compose.yml`, `open5gs/`, `ueransim/`, `subscribers.js`.

### 5.1 Topology

```
 ue_healthcare ┐
 ue_education  ├─ ran ─► gnb ─ cell ─► cell_site ═ core (N2/N3) ═► core container ─ n6 ─► dn (edge services)
 ue_agriculture│        UERANSIM       router        rural link      Open5GS + UPF
 ue_general    ┘                       UPLINK shaping                ogstun: DOWNLINK shaping
                                                                       ├─ fiber, 20 ms ──────┐
 tg_* sidecars share each UE's namespace                               └─ backup, 40 ms ─────┴─► dn_core
 upf_tap shares the core container's namespace
```

### 5.2 Containers

| Service | Image | Addresses | Role |
|---|---|---|---|
| `mongo` | `mongo:6.0` | core 10.80.0.5 | Subscriber database |
| `core` | `gradiant/open5gs:2.7.2` | core 10.80.0.10, n6 10.81.0.10, fiber 10.83.0.10, backup 10.84.0.10 | All 5GC functions and the UPF |
| `gnb` | `gradiant/ueransim:3.2.6` | ran 10.79.0.20, cell 10.78.0.20 | gNB |
| `ue_*` (4) | `gradiant/ueransim:3.2.6` | ran 10.79.0.31–.34 | One UE per slice |
| `tg_*` (4) | `cars-sf-tools:latest` | Shares the UE's namespace | Traffic, probes, captures |
| `cell_site` | `cars-sf-tools:latest` | cell 10.78.0.2, core 10.80.0.2 | Router; uplink enforcement |
| `upf_tap` | `cars-sf-tools:latest` | Shares the `core` namespace | Downlink enforcement, flow capture |
| `dn` | `cars-sf-tools:latest` | n6 10.81.0.100 | Edge data network |
| `dn_core` | `cars-sf-tools:latest` | fiber 10.83.0.100, backup 10.84.0.100, lo 10.85.0.100 | Core cloud |

`cars-sf-tools` is built from `Dockerfile.tools`: Python 3.12, NumPy, iproute2, ethtool, tcpdump, ping. The repository
is mounted at `/cars-sf`.

`cell_site` must stay a separate node. Shaping on the gNB's own interface charges queued packets to its UDP socket,
which then starts failing sends. That produced 109,042 send errors before the router was added.

### 5.3 Networks

| Network | Subnet | Carries |
|---|---|---|
| `ran` | 10.79.0.0/24 | Simulated radio link (UERANSIM RLS) |
| `cell` | 10.78.0.0/24 | gNB to cell-site router |
| `core` | 10.80.0.0/24 | N2 and N3: the rural link |
| `n6` | 10.81.0.0/24 | Edge data network |
| `fiber` | 10.83.0.0/24 | Primary backhaul |
| `backup` | 10.84.0.0/24 | Standby backhaul |

Routes:

| Node | Destination | Next hop |
|---|---|---|
| `gnb` | 10.80.0.0/24 | 10.78.0.2 |
| `core` | 10.78.0.0/24 | 10.80.0.2 |
| `core` | 10.85.0.100/32 | Active backhaul; blackhole at metric 200 |
| `dn_core` | 10.60.0.0/14 | Active backhaul; blackhole at metric 200 |
| `dn` | 10.60.0.0/14 | 10.81.0.10 |
| `tg_*` | 10.81.0.0/24, 10.85.0.100/32 | `uesimtun0` |

The blackhole routes stop traffic leaking out of the Docker default route when a backhaul interface goes down.

### 5.4 5G core

PLMN 999/70, TAC 1, up to 64 UEs per function. `open5gs/start-core.sh` starts every function in one container:

1. Create `ogstun`, assign the four slice gateways, and bring it up.
2. Add the route to the gNB and the loopback aliases.
3. Wait for MongoDB.
4. Start NRF, SCP; then AUSF, UDM, UDR, PCF, NSSF, BSF; then UPF, SMF, AMF.

| Function | Address | Interface |
|---|---|---|
| NRF | 127.0.0.10:7777 | SBI |
| SCP | 127.0.0.200:7777 | SBI, used by all functions as client |
| AMF | 127.0.0.5:7777 | SBI; NGAP on 10.80.0.10 (gNB connects to port 38412) |
| SMF | 127.0.0.4:7777 | SBI; PFCP and GTP-U on 127.0.0.4 |
| UPF | 127.0.0.7 | PFCP; GTP-U on 10.80.0.10 |
| AUSF | 127.0.0.11:7777 | SBI |
| UDM | 127.0.0.12:7777 | SBI |
| PCF | 127.0.0.13:7777 | SBI; MongoDB |
| NSSF | 127.0.0.14:7777 | SBI |
| BSF | 127.0.0.15:7777 | SBI |
| UDR | 127.0.0.20:7777 | SBI; MongoDB |

The AMF prefers `NIA2` integrity and `NEA0` (null) ciphering. The PDU MTU is 1400.

### 5.5 Slice provisioning

Each slice has one subscriber, one UE and one PDU session.

| Class | IMSI | SST | SD | DNN | Pool | Gateway | UE address |
|---|---|---|---|---|---|---|---|
| healthcare | 999700000000001 | 2 | 000001 | `health` | 10.60.0.0/24 | 10.60.0.1 | 10.60.0.2 |
| education | 999700000000002 | 1 | 000002 | `edu` | 10.61.0.0/24 | 10.61.0.1 | 10.61.0.2 |
| agriculture | 999700000000003 | 3 | 000003 | `agri` | 10.62.0.0/24 | 10.62.0.1 | 10.62.0.2 |
| general | 999700000000004 | 1 | 000004 | `internet` | 10.63.0.0/24 | 10.63.0.1 | 10.63.0.2 |

A slice must match across all of these, or registration or session setup fails:

| Item | File |
|---|---|
| S-NSSAI list | `open5gs/amf.yaml`, `open5gs/nssf.yaml`, `ueransim/gnb.yaml` |
| DNN and pool | `open5gs/smf.yaml`, `open5gs/upf.yaml`, `open5gs/start-core.sh` |
| Subscriber | `subscribers.js` (loaded by MongoDB on first start) |
| UE session | `ueransim/ue_<class>.yaml` |

All four subscribers use AMBR 1 Gb/s, 5QI 9 and ARP 8. The core therefore does not differentiate the slices or limit
them. Differentiation comes only from §6. These are test credentials on the test PLMN, for lab use only.

### 5.6 gNB and UEs

`ueransim/gnb.yaml`: link IP 10.79.0.20, NGAP and GTP IP 10.78.0.20, AMF at 10.80.0.10:38412. Each UE searches for
its gNB at 10.79.0.20 and creates `uesimtun0`.

Startup is by fixed delay: the gNB waits 30 s and the UEs 38 s. `stack5g.ensure_stack()` treats the stack as ready
when all four UE addresses are present, and allows 120 s.

### 5.7 User-plane path

Uplink, for a healthcare packet to the edge:

```
tg_healthcare ─ uesimtun0 ─ RLS ─► gnb ─ GTP-U ─► cell_site [HTB, N3 egress] ─► UPF ─ ogstun ─ n6 ─► dn (10.81.0.100)
```

Downlink, the reverse:

```
dn ─ n6 ─► core ─ ogstun [HTB] ─► UPF ─ GTP-U ─► cell_site (not shaped) ─► gnb ─ RLS ─► UE
```

Traffic to the core cloud leaves the UPF for 10.85.0.100 over the active backhaul.

### 5.8 Run-time setup

`Topology5G.reset()` runs before each run:

| Step | Setting |
|---|---|
| Offload | `tso gso gro lro` off, so captures hold wire-size packets |
| Fiber | netem `delay 20ms limit 100000` at both ends |
| Backup | netem `delay 40ms rate 50mbit limit 100000` at both ends |
| Core service | 10.85.0.100/32 on `dn_core` loopback |
| Routes | §5.3, on the primary path |
| UE tunnel | `txqueuelen 20000`, `pfifo limit 20000`, so the simulated radio is never the bottleneck |

## 6. Traffic control

Both backends use the same HTB structure in each direction.

```
root 1: htb, default 40 (general)
└─ 1:1  rate C, ceil C
   ├─ 1:10 healthcare   prio 1  ─ fq_codel
   ├─ 1:20 education    prio 2  ─ fq_codel
   ├─ 1:30 agriculture  prio 3  ─ fq_codel
   └─ 1:40 general      prio 4  ─ fq_codel
```

Enforcement points:

| Direction | Mininet | 5G |
|---|---|---|
| Uplink | `s_rural-up` on `s_rural` | N3 interface of `cell_site` |
| Downlink | `s_edge-down` on `s_edge` | `ogstun` on `upf_tap` |

Allocation applies one command per class and direction. It then reads the classes back from the kernel and records
`verified`:

```sh
tc class change dev <iface> parent 1:1 classid <id> htb rate <r>mbit ceil <c>mbit quantum 1514
```

Classes may borrow up to C unless `--strict-caps` is set. The `no_slicing` baseline uses one class with a
`pfifo limit 1000`, shaped to C.

### 6.1 Filters

| Mode | Meaning | Mininet | 5G |
|---|---|---|---|
| `host` | The UE decides the class | u32 on UE address | Address pool, inner header on N3 |
| `app` | Registry oracle: server and port | u32 | Not offered |
| `slicenet` | Host rules plus SliceNet for a mixed UE | u32 and flower | Not offered |
| `slicenet_all` | SliceNet classifies every flow; flows start in general | flower, u32 fallback | Below |

On 5G, N3 uplink packets are already GTP-U encapsulated, so filters match the inner header at a fixed offset of
44 bytes: outer IPv4 20, UDP 8, GTP-U 8, PDU session container 8.

| Inner field | Offset |
|---|---|
| Protocol | 53 |
| Source address | 56 |
| Destination address | 60 |
| Source and destination ports | 64 |

Filter priorities on 5G (lower is matched first):

| prio | Rule | Installed |
|---|---|---|
| 50 | ICMP probes stay in their PDU session's slice | Always |
| 60 | Address pool to class | Not with `slicenet_all` |
| 100+ | One 5-tuple rule per SliceNet flow, each with its own prio | At run time |

Example rules:

```sh
# uplink, healthcare pool, cell_site
tc filter add dev <n3> protocol ip parent 1: prio 60 u32 \
  match ip dport 2152 0xffff match u32 0x0a3c0000 0xffffff00 at 56 flowid 1:10
# downlink, one SliceNet flow, upf_tap
tc filter add dev ogstun protocol ip parent 1: prio 1 handle <n> flower \
  src_ip <peer> dst_ip <ue> ip_proto udp src_port <p> dst_port <q> classid 1:10
```

### 6.2 GTP overhead

The uplink root qdisc adds `stab overhead -44 linklayer ethernet`. HTB therefore counts uplink bytes as user-plane
bytes, and C means the same payload capacity in both directions.

Non-GTP traffic on N3, such as N2 signalling, falls into the default class. Downlink at `cell_site` is not shaped,
because it was already shaped at `ogstun`.

## 7. Traffic generation

Applications are defined in `registries/applications.yaml` and scaled to the scenario's demand. `traffic/generator.py`
and `traffic/sink.py` run on both backends.

Each application runs as two independent streams, with the second at port + 1000. Mininet gets this from having two
UEs per service. On 5G, `Traffic5G` creates the two streams on the class's single UE. One stream at twice the rate
would produce peaks above capacity that real multiplexed traffic does not show.

Each application's server is `srv_edge` or `srv_core`, which maps to `dn` or `dn_core` on 5G.

## 8. Control loop

Each tick is 1 s. On 5G, the order in `run_5g.run_loop` is:

| # | Stage | Code | What happens |
|---|---|---|---|
| 1 | Context | `context/engine.py` | Sets the scenario, priorities and overload policy |
| 2 | Faults | `FaultInjector5G` | Applies the scenario's fault |
| 3 | Monitor | `Telemetry5G.poll` | Reads HTB counters at both points, ICMP probes every 0.2 s |
| 4 | Heal | `FailureDetector`, `PredictiveDetector`, `SelfHealingEngine` | Detects faults, switches path, verifies |
| 5 | Reward | `ExperimentOrchestrator._feedback_row` | Scores the last interval |
| 6 | Classify | `OnlineSliceClassifier` | Reads UPF captures, installs flow rules |
| 7 | Evaluate | `QoSViolationMonitor` | Marks each class ok, transient or persistent |
| 8 | Decide | `SliceController.step` | Rules plan, plus RL on a persistent violation |
| 9 | Gate | `slicing/safety.py` | Rejects an unsafe or invalid plan |
| 10 | Enforce | `QoSEnforcer.apply_allocation` | Sets and reads back HTB rates |

**Monitoring.** Throughput, loss and queue delay come from HTB and fq_codel counters. Latency is the probe RTT ÷ 2.
Jitter is the mean successive probe difference ÷ 2. Utilisation is measured against C.

**Classification.** Flow capture runs on `ogstun`, which sees each UE's packets without GTP. A flow is decided after
about 1 s and rechecked every 5 ticks with full-window features. The classifier is a Random Forest.

**Transient and persistent.** A breach becomes persistent after 3 consecutive ticks and clears after 3 clean ticks.
Only a persistent violation triggers RL. Shorter breaches are left to the queues.

**Planning.** The rules allocator (`QoSAwareAllocator`) re-plans every 5 ticks, on context changes, and on loss or
delay breaches. It works per direction and has three regimes: SLA feasible, mean feasible and overload.

**RL.** The PPO residual policy starts from the rules plan and corrects each class by up to ±30 %. An online CEM
offset updates from live transitions (`ClosedLoopResidualPolicy`). Details are in `RL_DESIGN.md`.

**Safety gate.** Plans must keep every rate finite and non-negative, keep Σ rates ≤ C per direction, and honour
protected minimums. An invalid plan is never actuated; the last good allocation stays. A learned plan must also move
at most 20 % of capacity per direction, and must not take capacity from a violating or degraded slice unless all
gainers have higher priority.

**Scheduler.** `closed_loop` in `registries/schedulers.yaml` combines all of the above.

### 8.1 Fault mapping

| Scenario fault | Mininet | 5G |
|---|---|---|
| Fiber cut | `s_core-bh` down | Fiber interface on UPF down |
| Degradation | netem change on `s_edge-bh` | netem change at both fiber ends |
| Core switch failure | All `s_core` ports down | Fiber and backup interfaces on UPF down |
| Failover | `s_edge-bh` down, `s_edge-bkp` up | Routes moved to backup |
| Detection | Link watcher | `LinkWatcher5G`, 50 ms carrier poll |
| Fail back | Far-end carrier and link quality checks | Same interface, via `Topology5G` |

On backup, core-bound classes get a lower ceiling because backup capacity is 50 % of C. Self-healing also acts
without a fault: on link saturation it adjusts class priorities (for example halving general), and the controller
receives these as allocation constraints.

## 9. Deployment placement

The live loop runs at the edge site beside the UPF (MEC). It decides every 1–5 s and acts on transport queues, and
it has to keep working when the fiber is cut. The enforcement points are the cell-site router and the UPF. The
reasoning and the mapping to real equipment are in `docs/DEPLOYMENT_ARCHITECTURE.md`.

## 10. Bring-up

### 10.1 Prerequisites

| Requirement | Used by | Check |
|---|---|---|
| Linux with `tc`, `ip`, `tcpdump` | All | `which tc ip tcpdump` |
| Python venv with `requirements.txt` | All | `make setup` |
| Mininet 2.3 (system package) | Mininet | `python3 -c "import mininet"` |
| User namespaces | Sudo-free runs | `unshare -Urn true && echo ok` |
| Open vSwitch, root | Real OVS | `ovs-vsctl --version` |
| Docker and Compose | 5G, OVS validation | `docker compose version` |

Last run on kernel 7.0.0, Docker 29.9.2 and Compose 5.6.1.

### 10.2 Mininet

```bash
make setup

# Sudo-free, Linux bridges
.venv/bin/python -m tests.integration.harness school 40 apply_qos=true
.venv/bin/python -m tests.integration.harness fiber_cut 45 apply_qos=true

# Real OVS, tc backend
sudo .venv/bin/python run_experiment.py --scenario disaster --duration 40 --apply-qos --scheduler qos_adaptive

# Real OVS, OVS queue backend
sudo .venv/bin/python run_experiment.py --scenario disaster --duration 40 --apply-qos --qos-backend ovs

make clean-net      # after a crashed run (sudo mn -c)
```

Results go to `results/runs/<run_id>/`.

### 10.3 OVS in Docker

```bash
docker build -t cars-sf .
docker run --rm -it --privileged -v /lib/modules:/lib/modules:ro cars-sf \
    .venv/bin/python run_experiment.py --scenario fiber_cut --duration 45 --apply-qos
.venv/bin/python experiments/ovs_validation.py     # 33 runs
```

`--privileged` is required. OVS needs its kernel datapath module from the host.

### 10.4 Open5GS

```bash
docker compose -f deployment/5g/docker-compose.yml up -d --build
docker compose -f deployment/5g/docker-compose.yml ps      # 15 services up
docker compose -f deployment/5g/docker-compose.yml exec tg_healthcare ip -4 addr show uesimtun0   # 10.60.0.2

# Rules, no trained models needed
.venv/bin/python deployment/5g/run_5g.py --scenario disaster --scheduler qos_adaptive --classification host

# Full loop; needs the models in §10.5
.venv/bin/python deployment/5g/run_5g.py --scenario disaster --scheduler closed_loop --classification slicenet_all
```

`--seeds` runs several seeds, `--capacity` scales the link and the demands together, and `--no-healing` disables
self-healing. Results go to `results/5g/`: `<run_id>.json`, `__feedback.csv`, `__transitions.jsonl` and `.csv`.

Subscribers load only when MongoDB first initialises its data. After changing `subscribers.js`, recreate the stack
with `docker compose -f deployment/5g/docker-compose.yml down -v`.

### 10.5 Models and validation

```bash
.venv/bin/python experiments/collect_5g.py                 # 5G traffic, then train SliceNet
.venv/bin/python experiments/collect_5g.py --train-only    # train only
.venv/bin/python experiments/semantic_study.py --deploy    # write the closed-loop RL policy
.venv/bin/python experiments/validate_32.py                # 160 runs, about 4 h, nothing else running
.venv/bin/python experiments/validate_32.py --analyse
```

| Variable | Purpose |
|---|---|
| `CARS_SF_SLICENET_MODEL` | SliceNet model path; `validate_32.py` sets it |
| `CARS_SF_CEM_ONLINE_PATH` | Online CEM checkpoint; `validate_32.py` sets it |

### 10.6 Validation plan

`docs/thesis/validation_32_plan.md` fixes this before any run:

| Item | Value |
|---|---|
| Arms | `no_slicing`; `rules` (qos_adaptive, host); `slicenet` (qos_adaptive, slicenet_all); `full` (closed_loop, slicenet_all) |
| Grid | 8 scenarios × 4 arms × 5 seeds (40–44) = 160 runs, each covering all 4 classes |
| Run | 60 s at 100 Mb/s |
| Pass share | 0.95 |

## 11. Implementation status

As of 2026-11-02.

| Component | Status | Evidence |
|---|---|---|
| Mininet + Linux bridge | Working | Evaluation matrix |
| Mininet + real OVS | Working on earlier code | 33 runs; not repeated for `closed_loop` |
| Open5GS + UERANSIM | Working | Four slices attached, GTP-U user plane |
| Transport slicing on 5G | Working | 370 of 370 rate decisions read back correctly across 24 collection runs (`qos_adaptive`, host) |
| Failover on 5G | Working under rules | 9 fault runs: backup activated and recovery verified in all; core failure diagnosed in all 3 such runs; fail-back in the 6 runs with a repair |
| QoS monitor | Unit tested | Not yet evaluated in a 5G validation run |
| SliceNet on 5G | Provisional | See below |
| Conventional RL state | Decided | Semantic state not adopted, see below |
| `closed_loop` on 5G | **Not yet run** | Trained policy not deployed |
| 32-combination validation | **Not yet run** | No validation results exist |

**SliceNet.** Trained on 5G seeds 30–31 plus Mininet data, then tested on held-out seed 32: accuracy 0.927. This
model predates a fix to its training columns, so it must be retrained before validation. Recall on that seed:

| Scenario | healthcare | education | agriculture | general |
|---|---|---|---|---|
| normal | 0.821 | 0.609 | 1.000 | 0.922 |
| school | 1.000 | 0.396 | 1.000 | 0.969 |
| harvest | 1.000 | 0.543 | 1.000 | 0.958 |
| disaster | 1.000 | 0.815 | 1.000 | 0.945 |
| medical_emergency | 1.000 | 0.741 | 1.000 | 0.867 |
| fiber_cut | 1.000 | 0.700 | 0.971 | 0.958 |
| backhaul_degradation | 1.000 | 0.700 | 0.971 | 0.968 |
| core_switch_failure | 1.000 | 0.680 | 1.000 | 0.965 |

Education is the weak class, down to 0.396 in `school`, which is the scenario where it matters most.

**Semantic RL.** The predeclared study compared the semantic state with conventional state v2 on held-out scenarios.
The difference was +0.08 points with Wilcoxon p = 1.0, against a rule requiring at least 0.25 points and p < 0.05.
Conventional state v2 stays.

## 12. Limitations

| Area | Limitation |
|---|---|
| Radio | Simulated. No radio slicing, no over-the-air measurement |
| 5G core | Slices are provisioned statically. All use 5QI 9. Rate changes never reach the PCF or SMF |
| RIC | No Near-RT RIC, SMO or E2/A1 interface |
| Actuation | `tc` through container shells, not NETCONF or a vendor API |
| 5G delay | N3 and radio have no emulated propagation delay, unlike Mininet's 8 ms. The two backends' latencies are not directly comparable |
| 5G UEs | One UE per slice, so per-UE effects are absent |
| Core failure | No alternate path to core services. Self-healing diagnoses and degrades |
| Admission control | None |
| Harvest | Known regression under proportional degradation in the frozen evaluation (1.00 → 0.71), not fixed |
| Hardware | Not run on a real rural site or real radios |
| Stale config | `deployment/edge_config.yaml` predates this layout (for example `s_rural-eth4`, `open5gs: enabled: false`). Do not use it as a reference |
| Stale evidence | Code changes since the frozen evaluation make the Mininet runs stale by fingerprint. `results/evidence/final_eval_v5/` is the reference until they are rerun |

## 13. File map

| Purpose | Path |
|---|---|
| Mininet topology | `topology/rural_topology.py` |
| QoS enforcement, tc and OVS | `slicing/qos_enforcer.py` |
| 5G compose stack | `deployment/5g/docker-compose.yml` |
| 5G adapter | `deployment/5g/stack5g.py` |
| 5G loop | `deployment/5g/run_5g.py` |
| Open5GS configs | `deployment/5g/open5gs/` |
| UERANSIM configs | `deployment/5g/ueransim/` |
| Subscribers | `deployment/5g/subscribers.js` |
| Controller | `core/controller.py` |
| Allocators and safety | `slicing/allocators.py`, `slicing/safety.py` |
| QoS monitor | `monitoring/qos_monitor.py` |
| SliceNet, live | `classification/online.py` |
| RL | `scheduler/agent.py`, `scheduler/env_dir.py`, `scheduler/semantic.py` |
| Self-healing | `self_healing/` |
| Registries | `registries/` |
| Placement | `docs/DEPLOYMENT_ARCHITECTURE.md` |
| Validation plan | `docs/thesis/validation_32_plan.md` |
| Run commands | `docs/EXECUTION_GUIDE.md` |
