"""
Emergency Traffic Behaviour

Models mission-critical emergency communications.

Typical applications:
- Ambulance
- Emergency Alert
- Disaster Response
- Emergency Voice
- First Responder Communications

Author: RSNSD
"""

from __future__ import annotations

import random

from RSNSD.traffic_generator.behaviour.base_behaviour import BaseBehaviour


class EmergencyBehaviour(BaseBehaviour):
    """
    Mission-critical emergency traffic.

    Characteristics
    ---------------
    - Highest priority
    - Extremely low latency
    - Immediate session establishment
    - Small to medium packets
    - Continuous communication while active
    """

    @property
    def name(self) -> str:
        return "emergency"

    def generate_idle_time(self) -> float:
        """
        Emergency sessions remain active.
        """

        return 0.0

    def generate_burst_size(self) -> int:
        """
        Small bursts of control and status packets.
        """

        return random.randint(
            5,
            30,
        )

    def generate_connection_probability(self) -> float:
        """
        Emergency sessions should establish almost
        immediately when triggered.
        """

        return 0.99