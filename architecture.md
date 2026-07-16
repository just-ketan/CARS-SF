# Architecture.md

# RuralSliceAI
## System Architecture Document

Version: 1.0

Status: Active Development

---

# 1. Vision

## Goal

Design and implement an AI-driven Context-Aware Rural Service Slicing Framework for 5G Private Networks capable of dynamically allocating scarce network resources among socially important services while maintaining resilience through autonomous network management.

The project aims to bridge the digital divide by introducing service-aware networking tailored for rural deployments instead of traditional technology-centric network slicing.

---

# 2. Design Philosophy

The architecture follows four core principles.

## Principle 1

Context before Intelligence

Instead of immediately introducing AI, the system first understands the operating context.

Examples

- School Hours
- Harvest Season
- Disaster
- Normal Operation

---

## Principle 2

Demand before Allocation

Resources are allocated based on actual demand rather than fixed reservations.

---

## Principle 3

Service before Technology

Traditional 5G

- eMBB
- URLLC
- mMTC

Proposed

- Healthcare
- Education
- Agriculture
- Public Services
- General Internet

---

## Principle 4

Modular Evolution

Every module can be independently replaced without affecting the remaining architecture.

Example

Priority Engine

↓

RL Scheduler

without modifying any other component.

---

# 3. High-Level Architecture

```
                           +----------------------+
                           |    User Context      |
                           +----------+-----------+
                                      |
                                      v
                           +----------------------+
                           |   Context Engine     |
                           +----------+-----------+
                                      |
                                      v
                           +----------------------+
                           | Demand Generator     |
                           +----------+-----------+
                                      |
                                      v
                           +----------------------+
                           | Priority Engine      |
                           +----------+-----------+
                                      |
                                      v
                           +----------------------+
                           | Allocation Engine    |
                           +----------+-----------+
                                      |
                                      v
                           +----------------------+
                           | QoS Enforcer         |
                           +----------+-----------+
                                      |
                                      v
                           +----------------------+
                           | 5G Network / OVS     |
                           +----------+-----------+
                                      |
                                      v
                           +----------------------+
                           | Monitoring Module    |
                           +----------+-----------+
                                      |
                                      v
                           +----------------------+
                           | Self-Healing Engine  |
                           +----------+-----------+
                                      |
                                      v
                           +----------------------+
                           | Learning Engine      |
                           +----------------------+
```

---

# 4. Module Descriptions

---

## 4.1 Context Engine

### Responsibility

Determine the current operational context.

### Inputs

- Time
- Season
- Disaster Alerts
- Administrative Policies

### Outputs

```
Current Context
```

Example

```
School Hours
```

---

## 4.2 Demand Generator

### Responsibility

Estimate service demand.

Example

```
Healthcare

5 Mbps

Education

80 Mbps

Agriculture

10 Mbps
```

Future

Replace synthetic generator with

- Real traces
- Traffic prediction
- ML forecasting

---

## 4.3 Priority Engine

### Responsibility

Generate the Priority Matrix.

Example

```
Healthcare : 5

Education : 5

Agriculture : 2

General : 1
```

Future

Dynamic priorities generated using AI.

---

## 4.4 Allocation Engine

### Responsibility

Allocate bandwidth.

Current Version

Priority

+

Demand

+

Surplus Redistribution

Future

RL-based Scheduler

---

## 4.5 QoS Enforcer

### Responsibility

Translate scheduler decisions into network policies.

Current

Simulated

Future

Open vSwitch

Traffic Control

SDN

---

## 4.6 Monitoring Engine

Responsibilities

Collect

- Throughput
- Packet Loss
- Latency
- Queue Occupancy
- Link Utilization

---

## 4.7 Self-Healing Engine

Responsibilities

Detect

- Congestion
- Link Failure
- Switch Failure

Recover

- Rerouting
- Backup Activation
- Load Balancing

---

## 4.8 Learning Engine

Future module.

Responsibilities

Learn

- Better priorities
- Better scheduling
- Better recovery

using

- Reinforcement Learning
- Deep Learning

---

# 5. Current Repository Structure

```
MajorProject

├── topology

├── slicing

├── traffic

├── monitoring

├── visualization

├── experiments

├── reports

├── results

└── Literature
```

---

# 6. Data Flow

```
Context

↓

Demand

↓

Priority Matrix

↓

Allocation

↓

QoS Policies

↓

Network

↓

Monitoring

↓

Feedback

↓

Learning
```

---

# 7. Control Flow

```
Application Request

↓

Identify Service

↓

Determine Context

↓

Estimate Demand

↓

Generate Priorities

↓

Allocate Resources

↓

Apply QoS

↓

Monitor Performance

↓

Feedback
```

---

# 8. Component Dependency Graph

```
Context Engine

↓

Demand Generator

↓

Priority Engine

↓

Allocation Engine

↓

QoS Enforcer

↓

Network

↓

Monitoring
```

Self-Healing

↓

Network

Learning

↓

Priority Engine

↓

Allocation Engine

---

# 9. Current Development Status

| Module | Status |
|----------|--------|
| Context Engine | ✅ |
| Demand Generator | ✅ |
| Priority Engine | ✅ |
| Allocation Engine | ✅ |
| QoS Enforcer | ✅ Prototype |
| Monitoring | 🚧 |
| Visualization | 🚧 |
| Self-Healing | ❌ |
| Learning Engine | ❌ |

---

# 10. Planned Evolution

Prototype V1

↓

Demand-Aware Scheduler

↓

QoS Enforcement

↓

Real Traffic

↓

Experimental Evaluation

↓

Self-Healing

↓

Predictive Self-Healing

↓

AI Scheduler

↓

Final Thesis

---

# 11. Research Contributions

Contribution 1

Context-Aware Rural Service Slicing

Contribution 2

Demand-Aware Dynamic Scheduler

Contribution 3

Surplus Redistribution Algorithm

Contribution 4

Autonomous QoS Enforcement

Contribution 5

Self-Healing Rural 5G Network

Contribution 6

AI-Driven Adaptive Network Slicing

---

# 12. Future Extensibility

Future researchers can replace

- Context Engine

- Scheduler

- QoS Layer

- Monitoring Layer

- Self-Healing Layer

without modifying the remaining architecture.

This ensures the framework remains modular and extensible for future M.Tech, Ph.D., and sponsored research projects.

---

# 13. Long-Term Vision

Prototype

↓

Research Prototype

↓

Institute Testbed

↓

Sponsored Project

↓

Patent

↓

Open-Source Framework

↓

Industry Deployment