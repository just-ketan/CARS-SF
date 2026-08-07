"""
Bulk Transfer Traffic Behaviour

Models high-volume data transfer applications.

Typical applications:
- Medical Imaging
- Digital Library Downloads
- Software Updates
- File Synchronization
- Cloud Backup
- Dataset Replication

Author: RSNSD
"""

from __future__ import annotations

import random

from RSNSD.traffic_generator.behaviour.base_behaviour import BaseBehaviour


class BulkTransferBehaviour(BaseBehaviour):
    """
    Large continuous data transfers.

    Characteristics
    ---------------
    - Large packets
    - High throughput
    - Long sessions
    - Throughput-oriented
    - Latency tolerant
    """

    @property
    def name(self) -> str:
        return "bulk_transfer"

    def generate_idle_time(self) -> float:
        """
        Little idle time while a transfer
        is active.
        """

        return round(
            random.uniform(
                0.0,
                0.5,
            ),
            3,
        )

    def generate_burst_size(self) -> int:
        """
        Large packet bursts are common
        during sustained transfers.
        """

        return random.randint(
            100,
            1000,
        )

    def generate_connection_probability(self) -> float:
        """
        Large transfers are relatively
        infrequent.
        """

        return 0.35