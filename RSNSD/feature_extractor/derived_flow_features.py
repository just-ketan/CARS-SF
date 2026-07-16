"""
Derived Flow Feature Extractor

Computes additional flow-level features from the simulated
traffic record. These features approximate what tools such as
CICFlowMeter would derive from captured traffic while keeping
the simulation lightweight.

Author: RSNSD
"""

from __future__ import annotations

from RSNSD.domain.dataset import DatasetRecord


class DerivedFlowFeatureExtractor:
    """
    Computes deterministic flow statistics from the generated
    FlowRecord.
    """

    LINK_CAPACITY_MBPS = 100.0

    def extract(self, record: DatasetRecord) -> dict:

        flow = record.flow
        qos = record.qos

        duration_s = max(flow.session_duration_s, 0.001)

        packet_size_bytes = max(flow.packet_size, 1)

        bitrate_bps = flow.bitrate_mbps * 1_000_000

        packet_count = max(
            1,
            int(
                (bitrate_bps * duration_s)
                / (packet_size_bytes * 8)
            ),
        )

        byte_count = packet_count * packet_size_bytes

        packet_rate = packet_count / duration_s

        byte_rate = byte_count / duration_s

        goodput = qos.throughput_mbps

        bandwidth_utilization = (
            goodput
            / self.LINK_CAPACITY_MBPS
        ) * 100

        link_utilization = bandwidth_utilization

        return {

            "flow_duration_ms":
                duration_s * 1000,

            "packet_count":
                packet_count,

            "byte_count":
                int(byte_count),

            "packet_rate_pps":
                packet_rate,

            "byte_rate_bps":
                byte_rate,

            "goodput_mbps":
                goodput,

            "bandwidth_utilization_pct":
                min(100.0, bandwidth_utilization),

            "link_utilization_pct":
                min(100.0, link_utilization),

        }