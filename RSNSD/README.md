# Rural Service-aware Network Slice Dataset (RSNSD)

> **Submodule of SliceNet**
>
> A research-grade dataset generation framework for intelligent service-aware network slicing in rural 5G networks.

---

# Version

**Current Version:** RSNSD v1.0

**Status:** Design Phase

---

# Overview

The **Rural Service-aware Network Slice Dataset (RSNSD)** is a synthetic yet realistic network traffic dataset specifically designed for AI-driven service-aware network slicing.

Unlike existing public network traffic datasets that classify traffic using application protocols or transport-layer characteristics, RSNSD is designed around **service semantics**.

The dataset enables machine learning models to answer the following question:

> **"What service is this traffic serving, and therefore what network slice should it receive?"**

instead of merely

> "Which protocol generated this traffic?"

This distinction makes the dataset directly applicable to intelligent 5G/6G slicing systems where service requirements, rather than application signatures alone, determine resource allocation.

---

# Motivation

## Problem with Existing Datasets

Most existing traffic datasets such as

- CICIDS
- UNSW-NB15
- CICFlowMeter datasets
- MAWI
- CAIDA
- KDD99

were designed for

- intrusion detection
- anomaly detection
- protocol identification
- malware classification

rather than service-aware resource allocation.

Typical labels are

```
HTTP
FTP
SSH
DNS
VoIP
Video
Email
```

These labels provide little information about **network intent**.

For example,

A telemedicine consultation and a YouTube video may both appear as encrypted video streams.

However,

- Telemedicine requires ultra-low latency and high reliability.
- YouTube can tolerate buffering.

Traditional datasets cannot distinguish between them.

---

# Research Gap

Current datasets generally lack

- rural application diversity
- service intent
- QoS requirements
- contextual information
- slice labels
- network state information

Consequently, they are unsuitable for training AI models for

- intelligent scheduling
- slice admission
- traffic prioritization
- QoS-aware resource allocation

---

# Proposed Solution

Develop a completely new dataset where each network flow represents an actual rural service.

Instead of protocol labels,

traffic is classified into

```
Healthcare
Education
Agriculture
General Internet
```

Future versions will also support

```
Emergency Services
Government Services
Industrial IoT
Public Safety
Smart Village Infrastructure
```

---

# Research Objectives

## Primary Objective

Create a reproducible service-aware network traffic dataset capable of training machine learning models for intelligent network slice classification.

---

## Secondary Objectives

- Model realistic rural network usage.
- Capture flow-level statistics.
- Include QoS characteristics.
- Include contextual information.
- Support supervised learning.
- Support reinforcement learning.
- Support future real-world deployment.

---

## Success Criteria

The dataset should

- represent realistic traffic behavior
- be reproducible
- be balanced across service classes
- contain sufficient statistical diversity
- generalize to unseen traffic
- support multiple ML architectures

---

# Dataset Philosophy

The fundamental unit of the dataset is

> **One Network Flow**

NOT

> One Packet

Reasons

- packet classification is computationally expensive
- SDN controllers classify flows
- network slicing decisions occur at flow granularity
- flow statistics provide richer information

Therefore

```
Packets
      ↓

Network Flow
      ↓

Feature Extraction
      ↓

One Dataset Row
```

---

# Dataset Architecture

```
Applications
        │
        ▼
Traffic Generation
        │
        ▼
Network Emulation
        │
        ▼
Packet Capture
        │
        ▼
Flow Extraction
        │
        ▼
Feature Engineering
        │
        ▼
Automatic Label Assignment
        │
        ▼
CSV Dataset
        │
        ▼
SliceNet AI Models
```

---

# Service Classes

## 1. Healthcare

Priority

Highest

Example applications

- Telemedicine
- Remote Consultation
- Remote Diagnostics
- ECG Monitoring
- Patient IoT
- Ambulance Video Feed
- Medical Image Upload

Characteristics

- extremely low latency
- high reliability
- moderate bandwidth
- delay sensitive

---

## 2. Education

Priority

Medium

Applications

- Online Classes
- Lecture Streaming
- LMS
- PDF Downloads
- Screen Sharing
- Virtual Labs

Characteristics

- moderate latency
- burst downloads
- continuous video

---

## 3. Agriculture

Priority

High

Applications

- Soil Sensors
- Weather Stations
- Crop Monitoring
- Drone Telemetry
- Drone Image Upload
- Livestock Monitoring
- Smart Irrigation

Characteristics

- periodic traffic
- image uploads
- telemetry
- IoT traffic

---

## 4. General Internet

Priority

Best Effort

Applications

- YouTube
- Social Media
- Browsing
- Email
- Gaming
- Messaging
- Cloud Backup

Characteristics

- highly variable
- delay tolerant
- elastic bandwidth

---

# Future Classes

Planned extensions include

- Emergency Services
- Government Services
- Industrial IoT
- Smart Transportation
- Public Safety
- Smart Village Infrastructure

---

# Dataset Size

Target

```
40,000 Flows
```

Balanced

```
Healthcare      10,000

Education       10,000

Agriculture     10,000

General         10,000
```

Future versions

```
100k

250k

500k

1 Million Flows
```

---

# Traffic Generation Strategy

Traffic generation follows a hybrid approach.

## Synthetic

Generate realistic flows using

- Scapy
- iperf3
- Python sockets

Advantages

- fully controllable
- reproducible

---

## Replay

Replay realistic captures

using

- tcpreplay
- pcap

Advantages

- real timing behavior

---

## Live Capture

Capture traffic from

- Mininet
- Open vSwitch
- Linux Network Namespaces

Advantages

- realistic interaction

---

## Hybrid

Combine all approaches.

This becomes the default strategy.

---

# Traffic Sources

## Healthcare

Examples

- telemedicine video
- patient monitoring
- ECG
- CT upload
- MRI upload
- ambulance camera

---

## Education

Examples

- Zoom
- Google Meet
- Moodle
- Classroom
- FTP downloads
- PDF transfer

---

## Agriculture

Examples

- MQTT sensors
- CoAP devices
- drone streams
- weather stations
- irrigation controllers

---

## General Internet

Examples

- HTTP
- HTTPS
- DNS
- FTP
- SSH
- YouTube
- Netflix
- Instagram

---

# Feature Engineering

The dataset will contain approximately

```
60–70 Features
```

organized into logical groups.

---

## Layer 2 Features

Examples

- Ethernet Type
- VLAN
- MAC Prefix
- Broadcast Flag

---

## Layer 3 Features

Examples

- IP Version
- TTL
- DSCP
- ECN
- Fragmentation

---

## Layer 4 Features

Examples

- Protocol
- Source Port
- Destination Port
- TCP Flags
- Window Size
- Retransmissions

---

## Flow Features

Examples

- Duration
- Packets
- Bytes
- Packet Rate
- Byte Rate

---

## Statistical Features

Examples

- Mean Packet Size
- Variance
- Std Dev
- Maximum
- Minimum

---

## Temporal Features

Examples

- Mean IAT
- Max IAT
- Min IAT
- Active Time
- Idle Time

---

## QoS Features

Examples

- Throughput
- Delay
- Jitter
- Packet Loss
- Queue Delay

---

## Context Features

This is one of the primary research contributions.

Examples

- Cell Load
- Network Congestion
- Time of Day
- Device Type
- User Mobility
- Village ID
- Service Type
- Required Latency
- Required Reliability
- Required Bandwidth
- Slice ID

---

# Labeling Strategy

Labels are generated automatically.

Example

```
Telemedicine

↓

Healthcare
```

```
Soil Sensor

↓

Agriculture
```

Automatic labeling eliminates manual annotation errors while ensuring reproducibility.

---

# Dataset Schema

Each row contains

```
Flow ID

↓

Flow Statistics

↓

QoS Features

↓

Context Features

↓

Service Label
```

The final schema will define

- feature name
- datatype
- units
- valid range
- description

for every feature.

---

# Validation Pipeline

The dataset must pass

## Class Balance

Equal representation of all classes.

---

## Missing Values

No missing entries.

---

## Duplicate Detection

Duplicate flow removal.

---

## Correlation Analysis

Remove redundant features.

---

## Statistical Verification

Ensure realistic distributions.

---

## Visual Inspection

Distribution plots

Correlation heatmaps

Feature histograms

---

# Data Collection Pipeline

```
Applications
        │
        ▼
Mininet
        │
        ▼
Open vSwitch
        │
        ▼
Traffic Generator
        │
        ▼
tcpdump
        │
        ▼
Wireshark
        │
        ▼
Flow Extractor
        │
        ▼
Feature Extractor
        │
        ▼
CSV Generator
```

---

# Machine Learning Compatibility

The dataset is designed for

## Classical ML

- Decision Tree
- Random Forest
- XGBoost
- LightGBM
- CatBoost

---

## Deep Learning

- MLP
- CNN
- LSTM
- CNN-LSTM
- Transformer

---

## Reinforcement Learning

Future versions will integrate directly with the SliceNet RL scheduler.

The classifier output becomes part of the RL environment state.

---

# Deliverables

The completed submodule will provide

```
RSNSD/
│
├── dataset/
│      ├── raw/
│      ├── processed/
│      ├── metadata/
│      └── statistics/
│
├── traffic_generator/
│
├── feature_extractor/
│
├── labeling/
│
├── validator/
│
├── documentation/
│
└── examples/
```

---

# Future Roadmap

## Version 1

- Synthetic traffic
- Four service classes
- Balanced dataset

---

## Version 2

- Real ISP traces
- Additional service categories
- More contextual features

---

## Version 3

- Integration with institute 5G testbed
- Real SDR traffic
- Live Open5GS deployment

---

## Version 4

- Industry-scale deployment
- Multi-cell scenarios
- Dynamic slice adaptation
- Public benchmark release

---

# Expected Research Contributions

The RSNSD submodule contributes:

1. A novel rural service-aware network traffic dataset tailored for AI-driven network slicing.
2. Flow-level features enriched with QoS and contextual information, extending beyond traditional protocol-centric datasets.
3. A reproducible traffic generation and labeling pipeline for future research.
4. Support for supervised, deep learning, and reinforcement learning approaches to intelligent network resource allocation.
5. A publicly shareable benchmark enabling fair comparison of service-aware traffic classification and network slicing algorithms.

By positioning the dataset as a standalone research artifact, RSNSD strengthens the overall SliceNet project and serves as a reusable foundation for future work in 5G/6G intelligent networking.