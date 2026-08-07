"""
Traffic Behaviour Types

Defines the canonical traffic behaviour patterns supported
by the RSNSD Traffic Behaviour Engine.

Every application profile is mapped to exactly one
behaviour type.

Author: RSNSD
"""

from __future__ import annotations

from enum import Enum


class BehaviourType(str, Enum):
    """
    Canonical traffic behaviour categories.

    These describe HOW an application generates traffic,
    independent of its domain.
    """

    PERIODIC = "periodic"
    BURSTY = "bursty"
    STREAMING = "streaming"
    CONVERSATIONAL = "conversational"
    TRANSACTIONAL = "transactional"
    BULK_TRANSFER = "bulk_transfer"
    EMERGENCY = "emergency"

    @property
    def description(self) -> str:
        """
        Human-readable description.
        """

        return {
            BehaviourType.PERIODIC:
                "Regular periodic transmissions with nearly constant intervals.",

            BehaviourType.BURSTY:
                "Short bursts of packets followed by idle periods.",

            BehaviourType.STREAMING:
                "Continuous high-throughput media traffic.",

            BehaviourType.CONVERSATIONAL:
                "Interactive bidirectional low-latency traffic.",

            BehaviourType.TRANSACTIONAL:
                "Short request-response exchanges.",

            BehaviourType.BULK_TRANSFER:
                "Large continuous data transfers emphasizing throughput.",

            BehaviourType.EMERGENCY:
                "Highest-priority emergency traffic with stringent latency requirements.",
        }[self]