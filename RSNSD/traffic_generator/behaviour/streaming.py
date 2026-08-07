"""
Streaming Traffic Behaviour

Models continuous multimedia traffic such as:

- Video Streaming
- CCTV
- ECG Streaming
- Live Classroom
- Drone Video

Author: RSNSD
"""

from __future__ import annotations

import random

from RSNSD.traffic_generator.behaviour.base_behaviour import BaseBehaviour


class StreamingBehaviour(BaseBehaviour):
    """
    Continuous high-throughput streaming traffic.
    """

    @property
    def name(self) -> str:
        return "streaming"

    def generate_idle_time(self) -> float:
        """
        Streaming traffic is nearly continuous.
        """

        return 0.0

    def generate_burst_size(self) -> int:
        """
        Streaming is continuous rather than bursty.
        """

        return 1

    def generate_connection_probability(self) -> float:
        """
        Streaming applications are relatively likely
        to establish long-lived sessions.
        """

        return 0.85