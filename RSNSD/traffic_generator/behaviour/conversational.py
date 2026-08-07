"""
Conversational Traffic Behaviour

Models real-time interactive communication such as:

- Voice over IP (VoIP)
- Emergency Voice
- Telemedicine Consultation
- Video Conferencing
- Interactive Classroom

Author: RSNSD
"""

from __future__ import annotations

import random

from RSNSD.traffic_generator.behaviour.base_behaviour import BaseBehaviour


class ConversationalBehaviour(BaseBehaviour):
    """
    Interactive bidirectional traffic.

    Characterized by:
    - Small packets
    - Very low latency
    - Continuous but variable packet generation
    - Human ON/OFF speaking behaviour
    """

    @property
    def name(self) -> str:
        return "conversational"

    def generate_idle_time(self) -> float:
        """
        Human conversations naturally alternate between
        speaking and silence.
        """

        return round(
            random.uniform(
                0.2,
                2.0,
            ),
            3,
        )

    def generate_burst_size(self) -> int:
        """
        A speaking period generates a small sequence of packets.
        """

        return random.randint(5, 20)

    def generate_connection_probability(self) -> float:
        """
        Users initiate conversational sessions fairly often,
        but less frequently than continuous streaming.
        """

        return 0.70